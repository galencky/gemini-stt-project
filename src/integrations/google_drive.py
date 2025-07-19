import io
import json
import datetime
from pathlib import Path
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

class GoogleDriveClient:
    def __init__(self, service_account_json_path_or_dict):
        """Initialize Google Drive client with service account credentials.
        
        Args:
            service_account_json_path_or_dict: Either a path to JSON file or a dict/JSON string
        """
        self.scopes = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/documents.readonly"]
        
        try:
            # Check if it's a file path or JSON data
            if isinstance(service_account_json_path_or_dict, str):
                # Try to parse as JSON first
                try:
                    import json as json_module
                    service_account_info = json_module.loads(service_account_json_path_or_dict)
                    self.creds = service_account.Credentials.from_service_account_info(
                        service_account_info, 
                        scopes=self.scopes
                    )
                except (json_module.JSONDecodeError, ValueError):
                    # Not JSON, treat as file path
                    self.creds = service_account.Credentials.from_service_account_file(
                        service_account_json_path_or_dict, 
                        scopes=self.scopes
                    )
            elif isinstance(service_account_json_path_or_dict, dict):
                # Direct dictionary
                self.creds = service_account.Credentials.from_service_account_info(
                    service_account_json_path_or_dict, 
                    scopes=self.scopes
                )
            else:
                raise ValueError("Service account must be a file path, JSON string, or dictionary")
            
            self.drive_service = build("drive", "v3", credentials=self.creds)
            self.docs_service = build("docs", "v1", credentials=self.creds)
        except Exception as e:
            raise ValueError(f"Failed to initialize Google Drive client: {e}")
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """List all files in a Google Drive folder."""
        query = f"'{folder_id}' in parents and trashed=false"
        files = []
        page_token = None
        
        try:
            while True:
                response = self.drive_service.files().list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                    supportsAllDrives=True
                ).execute()
                
                files.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                
                if not page_token:
                    break
                    
        except HttpError as error:
            print(f"An error occurred: {error}")
            
        return files
    
    def download_file(self, file_id: str, file_name: str, destination_path: Path) -> bool:
        """Download a file from Google Drive."""
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            destination_file = destination_path / file_name
            
            with io.FileIO(str(destination_file), mode="wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        print(f"Download progress: {int(status.progress() * 100)}%")
            
            print(f"✅ Downloaded: {file_name} to {destination_file}")
            return True
            
        except HttpError as error:
            print(f"❌ Error downloading {file_name}: {error}")
            return False
    
    def download_folder_contents(self, folder_id: str, destination_path: Path, 
                               file_types: Optional[List[str]] = None) -> List[Path]:
        """Download all files from a folder, optionally filtering by file type."""
        downloaded_files = []
        files = self.list_files_in_folder(folder_id)
        
        if not files:
            print(f"No files found in folder {folder_id}")
            return downloaded_files
        
        # Filter out folders
        files = [f for f in files if f["mimeType"] != "application/vnd.google-apps.folder"]
        
        # Filter by file types if specified
        if file_types:
            files = [f for f in files if any(f["name"].endswith(ext) for ext in file_types)]
        
        print(f"Found {len(files)} files to download")
        
        for file in files:
            if self.download_file(file["id"], file["name"], destination_path):
                downloaded_files.append(destination_path / file["name"])
        
        return downloaded_files
    
    def upload_file(self, local_file_path: Path, parent_folder_id: str) -> Optional[str]:
        """Upload a file to Google Drive."""
        try:
            file_metadata = {
                "name": local_file_path.name,
                "parents": [parent_folder_id]
            }
            
            media = MediaFileUpload(str(local_file_path), resumable=True)
            
            # Check if parent folder is in a shared drive
            parent_info = self.drive_service.files().get(
                fileId=parent_folder_id,
                fields="id,driveId",
                supportsAllDrives=True
            ).execute()
            
            if 'driveId' in parent_info:
                # It's a shared drive folder
                file_metadata['driveId'] = parent_info['driveId']
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True
            ).execute()
            
            print(f"✅ Uploaded: {local_file_path.name} (ID: {file.get('id')})")
            return file.get("id")
            
        except HttpError as error:
            print(f"❌ Error uploading {local_file_path.name}: {error}")
            return None
    
    def move_file(self, file_id: str, new_parent_id: str, old_parent_id: str) -> bool:
        """Move a file from one folder to another in Google Drive."""
        try:
            self.drive_service.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=old_parent_id,
                fields="id, parents",
                supportsAllDrives=True
            ).execute()
            
            print(f"✅ Moved file {file_id} to folder {new_parent_id}")
            return True
            
        except HttpError as error:
            print(f"❌ Error moving file: {error}")
            return False
    
    def create_folder(self, folder_name: str, parent_folder_id: str) -> Optional[str]:
        """Create a new folder in Google Drive."""
        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id]
            }
            
            folder = self.drive_service.files().create(
                body=file_metadata,
                fields="id",
                supportsAllDrives=True
            ).execute()
            
            print(f"✅ Created folder: {folder_name} (ID: {folder.get('id')})")
            return folder.get("id")
            
        except HttpError as error:
            print(f"❌ Error creating folder: {error}")
            return None
    
    def ensure_subfolder(self, parent_id: str, folder_name: str) -> str:
        """Get or create a subfolder in the specified parent folder."""
        # Check if folder already exists
        query = (f"'{parent_id}' in parents and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"name='{folder_name}' and trashed=false")
        
        try:
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
                # Create the folder
                return self.create_folder(folder_name, parent_id)
                
        except HttpError as error:
            print(f"❌ Error ensuring subfolder: {error}")
            return None
    
    def get_document_text(self, doc_id: str) -> str:
        """Get the text content from a Google Doc."""
        try:
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            
            text_parts = []
            for element in doc.get("body", {}).get("content", []):
                if "paragraph" in element:
                    for run in element["paragraph"].get("elements", []):
                        text = run.get("textRun", {}).get("content")
                        if text:
                            text_parts.append(text)
            
            return "".join(text_parts).strip()
            
        except HttpError as error:
            print(f"❌ Error retrieving document: {error}")
            return ""
    
    def find_file_by_name(self, file_name: str, parent_folder_id: str) -> Optional[Dict]:
        """Find a file by name in a specific folder."""
        query = f"'{parent_folder_id}' in parents and name='{file_name}' and trashed=false"
        
        try:
            response = self.drive_service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True
            ).execute()
            
            files = response.get("files", [])
            return files[0] if files else None
            
        except HttpError as error:
            print(f"❌ Error finding file: {error}")
            return None