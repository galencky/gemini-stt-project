"""Google Drive folder organization for processed files."""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from ..core.logger import logger
from ..core.exceptions import StorageError
from .google_drive import GoogleDriveManager
from .local_storage import LocalStorageManager


class FolderOrganizer:
    """Organizes processed files into structured Google Drive folders."""
    
    def __init__(self, gdrive_manager: GoogleDriveManager, local_storage: LocalStorageManager, upload_audio: bool = False, state=None):
        """Initialize folder organizer.
        
        Args:
            gdrive_manager: Google Drive manager instance
            local_storage: Local storage manager instance
            upload_audio: Whether to upload audio files (default: False)
            state: Pipeline state manager (optional)
        """
        self.gdrive = gdrive_manager
        self.local_storage = local_storage
        self.upload_audio = upload_audio
        self.state = state
    
    def organize_to_drive(self, 
                         processed_folder_id: str,
                         transcripts_dir: Path,
                         parsed_dir: Path,
                         summaries_dir: Path,
                         audio_files: Optional[List[Path]] = None,
                         local_backup_dir: Optional[Path] = None) -> Dict[str, str]:
        """Organize and upload all processed files to Google Drive.
        
        Creates a folder structure like:
        Processed/
        ├── audio_file_1/
        │   ├── audio_file_1.m4a (original audio)
        │   ├── audio_file_1.txt (raw transcript)
        │   ├── audio_file_1_parsed.txt (parsed transcript)
        │   └── audio_file_1.md (summary)
        └── audio_file_2/
            ├── ...
        
        Args:
            processed_folder_id: Google Drive folder ID for processed files
            transcripts_dir: Directory containing raw transcripts
            parsed_dir: Directory containing parsed transcripts
            summaries_dir: Directory containing summaries
            audio_files: Optional list of audio files to include
            local_backup_dir: Optional directory to create local organized folders
            
        Returns:
            Dictionary mapping file stems to folder IDs
        """
        folder_map = {}
        upload_summary = {
            "successful": [],
            "failed": [],
            "total_files": 0,
            "local_folders_created": []
        }
        
        try:
            # Get all transcript files to determine what to process
            transcript_files = list(transcripts_dir.glob("*.txt"))
            
            if not transcript_files:
                logger.warning("No transcript files found to organize")
                return folder_map
            
            logger.info(f"Organizing {len(transcript_files)} audio file(s) to Google Drive")
            
            for transcript_file in transcript_files:
                stem = transcript_file.stem
                
                # Check if already organized (via state)
                if self.state and self.state.is_folder_organized(stem):
                    logger.info(f"Skipping {stem} - already organized (tracked in state)")
                    continue
                
                # Check if already organized locally
                if local_backup_dir:
                    local_folder = local_backup_dir / stem
                    if local_folder.exists() and any(local_folder.iterdir()):
                        logger.info(f"Skipping {stem} - already organized locally in {local_folder}")
                        upload_summary["local_folders_created"].append(stem)
                        if self.state:
                            self.state.add_folder_organized(stem, "local")
                        continue
                
                try:
                    # Create folder for this audio file
                    logger.info(f"Creating folder for {stem}")
                    try:
                        folder_id = self.gdrive.ensure_folder(processed_folder_id, stem)
                        folder_map[stem] = folder_id
                        
                        # Check if files already exist in Drive folder
                        try:
                            existing_files = self.gdrive.list_files_in_folder(folder_id)
                            if existing_files and len(existing_files) >= 2:  # At least transcript and summary
                                logger.info(f"Folder {stem} already has files in Google Drive, skipping upload")
                                upload_summary["successful"].append(stem)
                                continue
                        except:
                            pass  # Continue with upload if check fails
                            
                    except Exception as e:
                        logger.error(f"Failed to create Drive folder for {stem}: {e}")
                        folder_id = None  # Will trigger local folder creation
                    
                    files_to_upload = []
                    
                    # Collect files to upload
                    # 1. Original audio (only if enabled)
                    if self.upload_audio and audio_files:
                        for audio_file in audio_files:
                            if audio_file.stem == stem:
                                files_to_upload.append(("audio", audio_file))
                                break
                    
                    # 2. Raw transcript
                    if transcript_file.exists():
                        files_to_upload.append(("transcript", transcript_file))
                    
                    # 3. Parsed transcript
                    parsed_file = parsed_dir / f"{stem}_parsed.txt"
                    if parsed_file.exists():
                        files_to_upload.append(("parsed", parsed_file))
                    
                    # 4. Summary
                    summary_file = summaries_dir / f"{stem}.md"
                    if summary_file.exists():
                        files_to_upload.append(("summary", summary_file))
                    
                    # Try to upload files, fall back to local if fails
                    upload_failed = False
                    
                    # If folder creation failed, skip uploads and go straight to local
                    if folder_id is None:
                        upload_failed = True
                        logger.info(f"  Skipping uploads for {stem}, will create local folder")
                    else:
                        # Upload all files to the folder
                        for file_type, file_path in files_to_upload:
                            try:
                                logger.info(f"  Uploading {file_type}: {file_path.name}")
                                self.gdrive.upload_file(file_path, folder_id)
                                upload_summary["total_files"] += 1
                            except Exception as e:
                                upload_failed = True
                                error_str = str(e)
                                if "storageQuotaExceeded" in error_str:
                                    logger.error(f"  Quota exceeded for {file_path.name} - Will create local folder instead")
                                    upload_summary["failed"].append(f"{stem}/{file_path.name} (quota)")
                                else:
                                    logger.error(f"  Failed to upload {file_path.name}: {e}")
                                    upload_summary["failed"].append(f"{stem}/{file_path.name}")
                    
                    # If any upload failed and local backup dir is specified, create local folder
                    if upload_failed and local_backup_dir:
                        self._create_local_folder(stem, files_to_upload, local_backup_dir)
                        upload_summary["local_folders_created"].append(stem)
                    
                    # Only mark as successful if we actually uploaded to Drive
                    if not upload_failed:
                        upload_summary["successful"].append(stem)
                        logger.success(f"Completed organizing {stem} to Google Drive")
                        if self.state:
                            self.state.add_folder_organized(stem, "gdrive")
                    else:
                        logger.info(f"Completed organizing {stem} locally")
                        if self.state:
                            self.state.add_folder_organized(stem, "local")
                    
                except Exception as e:
                    logger.error(f"Failed to organize {stem}: {e}")
                    upload_summary["failed"].append(stem)
            
            # Print summary
            logger.info("\n" + "="*60)
            logger.info("Google Drive Organization Summary:")
            logger.success(f"Successfully organized: {len(upload_summary['successful'])} folders")
            logger.info(f"Total files uploaded: {upload_summary['total_files']}")
            
            if upload_summary["failed"]:
                logger.error(f"Failed: {len(upload_summary['failed'])} items")
                for failed_item in upload_summary["failed"]:
                    logger.error(f"  - {failed_item}")
            
            if upload_summary["local_folders_created"]:
                logger.info(f"\nCreated local folders for manual upload: {len(upload_summary['local_folders_created'])}")
                if local_backup_dir:
                    logger.info(f"Local folder location: {local_backup_dir}")
                for local_folder in upload_summary["local_folders_created"]:
                    logger.info(f"  - {local_folder}")
            
            logger.info("="*60)
            
            return folder_map
            
        except Exception as e:
            raise StorageError(f"Failed to organize files to Google Drive: {e}") from e
    
    def _create_local_folder(self, stem: str, files_to_copy: List[tuple], base_dir: Path):
        """Create a local folder with organized files.
        
        Args:
            stem: The file stem (base name)
            files_to_copy: List of (file_type, file_path) tuples
            base_dir: Base directory to create the folder in
        """
        try:
            # Create folder for this stem
            folder_path = base_dir / stem
            folder_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Creating local folder: {folder_path}")
            
            # Copy files to the folder
            for file_type, file_path in files_to_copy:
                if file_path.exists():
                    dest_path = folder_path / file_path.name
                    try:
                        import shutil
                        shutil.copy2(file_path, dest_path)
                        logger.info(f"  Copied {file_type}: {file_path.name}")
                    except Exception as e:
                        logger.error(f"  Failed to copy {file_path.name}: {e}")
            
            logger.success(f"Created local folder for {stem}")
            
        except Exception as e:
            logger.error(f"Failed to create local folder for {stem}: {e}")
    
    def create_date_organized_structure(self, 
                                      processed_folder_id: str,
                                      files_to_organize: Dict[str, List[Path]]) -> Dict[str, str]:
        """Create a date-organized folder structure.
        
        Creates structure like:
        Processed/
        ├── 2024-01/
        │   ├── audio_file_1/
        │   └── audio_file_2/
        └── 2024-02/
            └── audio_file_3/
        
        Args:
            processed_folder_id: Root folder ID
            files_to_organize: Dictionary mapping stems to file paths
            
        Returns:
            Dictionary mapping file stems to folder IDs
        """
        folder_map = {}
        
        try:
            # Group files by month
            files_by_month = {}
            
            for stem, file_paths in files_to_organize.items():
                # Get file creation date (use first file)
                if file_paths:
                    file_date = datetime.fromtimestamp(file_paths[0].stat().st_mtime)
                    month_key = file_date.strftime("%Y-%m")
                    
                    if month_key not in files_by_month:
                        files_by_month[month_key] = {}
                    
                    files_by_month[month_key][stem] = file_paths
            
            # Create month folders and organize files
            for month_key, month_files in files_by_month.items():
                logger.info(f"Processing month: {month_key}")
                
                # Create month folder
                month_folder_id = self.gdrive.ensure_folder(processed_folder_id, month_key)
                
                # Organize files within month
                for stem, file_paths in month_files.items():
                    # Create audio folder within month
                    audio_folder_id = self.gdrive.ensure_folder(month_folder_id, stem)
                    folder_map[stem] = audio_folder_id
                    
                    # Upload files
                    for file_path in file_paths:
                        try:
                            self.gdrive.upload_file(file_path, audio_folder_id)
                            logger.info(f"  Uploaded {file_path.name} to {month_key}/{stem}")
                        except Exception as e:
                            logger.error(f"  Failed to upload {file_path.name}: {e}")
            
            return folder_map
            
        except Exception as e:
            raise StorageError(f"Failed to create date-organized structure: {e}") from e
    
    def sync_audio_files(self, 
                        from_folder_id: str,
                        to_folder_id: str,
                        processed_stems: List[str]):
        """Move processed audio files from source to destination folder.
        
        Args:
            from_folder_id: Source folder ID (to_be_transcribed)
            to_folder_id: Destination folder ID (transcribed)
            processed_stems: List of file stems that were processed
        """
        try:
            logger.info("Moving processed audio files in Google Drive")
            
            moved_count = 0
            for stem in processed_stems:
                # Find matching audio files
                files = self.gdrive.list_files_in_folder(from_folder_id)
                
                for file_info in files:
                    file_name = file_info.get("name", "")
                    file_stem = Path(file_name).stem
                    
                    # Check if this file matches (handle _audio suffix)
                    if file_stem == stem or file_stem == f"{stem}_audio":
                        try:
                            self.gdrive.move_file(
                                file_info["id"],
                                from_folder_id,
                                to_folder_id
                            )
                            logger.info(f"Moved {file_name} to transcribed folder")
                            moved_count += 1
                            break
                        except Exception as e:
                            logger.error(f"Failed to move {file_name}: {e}")
            
            if moved_count > 0:
                logger.success(f"Moved {moved_count} audio file(s) to transcribed folder")
            
        except Exception as e:
            logger.error(f"Failed to sync audio files: {e}")