"""Google Drive storage operations."""

import io
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

from ..core.logger import logger
from ..core.exceptions import StorageError, AuthenticationError


class GoogleDriveManager:
    """Manages Google Drive operations."""
    
    def __init__(self, service_account_json: str, scopes: List[str] = None):
        """Initialize Google Drive manager.
        
        Args:
            service_account_json: JSON string with service account credentials
            scopes: Google API scopes
        """
        self.scopes = scopes or ["https://www.googleapis.com/auth/drive"]
        
        try:
            # Parse the JSON string
            sa_data = json.loads(service_account_json)
            
            # Create credentials
            self.creds = service_account.Credentials.from_service_account_info(
                sa_data, scopes=self.scopes
            )
            
            # Build services
            self.drive_service = build("drive", "v3", credentials=self.creds)
            self.docs_service = build("docs", "v1", credentials=self.creds)
            
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Google Drive: {e}") from e
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """List all files in a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            List of file dictionaries with 'id' and 'name' keys
            
        Raises:
            StorageError: If listing fails
        """
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            files = []
            page_token = None
            
            while True:
                response = self.drive_service.files().list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    pageToken=page_token,
                    supportsAllDrives=True
                ).execute()
                
                files.extend(response.get("files", []))
                page_token = response.get("nextPageToken", None)
                
                if not page_token:
                    break
            
            logger.info(f"Found {len(files)} files in folder {folder_id}")
            return files
            
        except HttpError as e:
            raise StorageError(f"Failed to list files in folder: {e}") from e
    
    def download_file(self, file_id: str, file_name: str, dest_dir: Path) -> Path:
        """Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            dest_dir: Destination directory
            
        Returns:
            Path to downloaded file
            
        Raises:
            StorageError: If download fails
        """
        try:
            dest_path = dest_dir / file_name
            
            request = self.drive_service.files().get_media(fileId=file_id)
            fh = io.FileIO(str(dest_path), mode="wb")
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            fh.close()
            logger.success(f"Downloaded {file_name} to {dest_path}")
            return dest_path
            
        except Exception as e:
            raise StorageError(f"Failed to download file {file_name}: {e}") from e
    
    def download_files_from_folder(self, folder_id: str, dest_dir: Path, 
                                 file_filter: Optional[List[str]] = None) -> List[Path]:
        """Download all files from a Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            dest_dir: Destination directory
            file_filter: Optional list of file extensions to download
            
        Returns:
            List of downloaded file paths
        """
        downloaded_files = []
        
        # List non-folder files
        query = (
            f"'{folder_id}' in parents and "
            "trashed = false and "
            "mimeType != 'application/vnd.google-apps.folder'"
        )
        
        try:
            response = self.drive_service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True
            ).execute()
            
            files = response.get("files", [])
            
            if not files:
                logger.info(f"No files found in folder {folder_id}")
                return downloaded_files
            
            logger.info(f"Found {len(files)} file(s) to download")
            
            for file_data in files:
                file_name = file_data["name"]
                
                # Apply filter if specified
                if file_filter:
                    if not any(file_name.lower().endswith(ext.lower()) for ext in file_filter):
                        logger.debug(f"Skipping {file_name} (not matching filter)")
                        continue
                
                try:
                    dest_path = self.download_file(file_data["id"], file_name, dest_dir)
                    downloaded_files.append(dest_path)
                except Exception as e:
                    logger.error(f"Failed to download {file_name}: {e}")
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error downloading files from folder: {e}")
            return downloaded_files
    
    def upload_file(self, local_path: Path, parent_id: str) -> str:
        """Upload a file to Google Drive.
        
        Args:
            local_path: Path to local file
            parent_id: Parent folder ID in Google Drive
            
        Returns:
            File ID of uploaded file
            
        Raises:
            StorageError: If upload fails
        """
        try:
            media = MediaFileUpload(str(local_path), resumable=False)
            meta = {
                "name": local_path.name,
                "parents": [parent_id]
            }
            
            file = self.drive_service.files().create(
                body=meta,
                media_body=media,
                fields="id",
                supportsAllDrives=True
            ).execute()
            
            logger.success(f"Uploaded {local_path.name} to Google Drive")
            return file["id"]
            
        except Exception as e:
            raise StorageError(f"Failed to upload {local_path.name}: {e}") from e
    
    def create_folder(self, name: str, parent_id: str) -> str:
        """Create a folder in Google Drive.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID
            
        Returns:
            Folder ID of created folder
        """
        try:
            meta = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id]
            }
            
            folder = self.drive_service.files().create(
                body=meta,
                fields="id",
                supportsAllDrives=True
            ).execute()
            
            logger.info(f"Created folder '{name}' in Google Drive")
            return folder["id"]
            
        except Exception as e:
            raise StorageError(f"Failed to create folder {name}: {e}") from e
    
    def ensure_folder(self, parent_id: str, name: str) -> str:
        """Ensure a folder exists, creating if necessary.
        
        Args:
            parent_id: Parent folder ID
            name: Folder name
            
        Returns:
            Folder ID
        """
        try:
            # Check if folder exists
            query = (
                f"'{parent_id}' in parents and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"name='{name}' and trashed=false"
            )
            
            response = self.drive_service.files().list(
                q=query,
                spaces="drive",
                fields="files(id)",
                supportsAllDrives=True
            ).execute()
            
            files = response.get("files", [])
            
            if files:
                return files[0]["id"]
            else:
                return self.create_folder(name, parent_id)
                
        except Exception as e:
            raise StorageError(f"Failed to ensure folder {name}: {e}") from e
    
    def move_file(self, file_id: str, from_folder_id: str, to_folder_id: str):
        """Move a file between folders in Google Drive.
        
        Args:
            file_id: File ID to move
            from_folder_id: Source folder ID
            to_folder_id: Destination folder ID
        """
        try:
            self.drive_service.files().update(
                fileId=file_id,
                addParents=to_folder_id,
                removeParents=from_folder_id,
                fields="id",
                supportsAllDrives=True
            ).execute()
            
            logger.info(f"Moved file {file_id} to folder {to_folder_id}")
            
        except Exception as e:
            raise StorageError(f"Failed to move file: {e}") from e
    
    def find_file_by_name(self, folder_id: str, file_name: str) -> Optional[str]:
        """Find a file by name in a folder.
        
        Args:
            folder_id: Folder ID to search in
            file_name: Name of the file
            
        Returns:
            File ID if found, None otherwise
        """
        try:
            query = f"'{folder_id}' in parents and name='{file_name}' and trashed=false"
            
            response = self.drive_service.files().list(
                q=query,
                spaces="drive",
                fields="files(id)",
                supportsAllDrives=True
            ).execute()
            
            files = response.get("files", [])
            return files[0]["id"] if files else None
            
        except Exception as e:
            logger.error(f"Error finding file {file_name}: {e}")
            return None
    
    def get_document_text(self, doc_id: str) -> str:
        """Retrieve text content from a Google Doc.
        
        Args:
            doc_id: Google Doc ID
            
        Returns:
            Document text content
        """
        try:
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            text = []
            
            for element in doc.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for run in element['paragraph'].get('elements', []):
                        txt = run.get('textRun', {}).get('content')
                        if txt:
                            text.append(txt)
            
            return ''.join(text).strip()
            
        except Exception as e:
            raise StorageError(f"Failed to get document text: {e}") from e