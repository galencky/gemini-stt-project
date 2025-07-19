#!/usr/bin/env python3
"""
Manual fallback script to organize already processed files to Google Drive folders.
This is normally handled automatically by the main pipeline (run.cmd).
Only use this if you need to manually re-organize files.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import Config, PipelineState
from src.core.logger import logger
from src.storage import GoogleDriveManager, LocalStorageManager, FolderOrganizer


def organize_existing_files():
    """Organize already processed files into Google Drive folders."""
    try:
        # Load configuration
        config = Config()
        
        # Validate configuration
        is_valid, errors = config.validate()
        if not is_valid:
            logger.error(f"Invalid configuration: {', '.join(errors)}")
            return False
        
        logger.info("Organizing processed files to Google Drive folders...")
        
        # Initialize state
        state = PipelineState()
        
        # Initialize components
        gdrive = GoogleDriveManager(
            config.gdrive_service_account_json,
            config.google_scopes
        )
        local_storage = LocalStorageManager()
        folder_organizer = FolderOrganizer(
            gdrive, 
            local_storage,
            upload_audio=config.upload_audio_to_drive,
            state=state
        )
        
        # Check what files we have
        transcript_files = list(config.transcripts_dir.glob("*.txt")) if config.transcripts_dir.exists() else []
        parsed_files = list(config.parsed_dir.glob("*_parsed.txt")) if config.parsed_dir.exists() else []
        summary_files = list(config.uploaded_dir.glob("*.md")) if config.uploaded_dir.exists() else []
        
        if not any([transcript_files, parsed_files, summary_files]):
            logger.warning("No processed files found to organize")
            return False
        
        logger.info(f"Found files to organize:")
        logger.info(f"  - Transcripts: {len(transcript_files)}")
        logger.info(f"  - Parsed: {len(parsed_files)}")
        logger.info(f"  - Summaries: {len(summary_files)}")
        
        # Get audio files from inbox
        audio_files = local_storage.find_files(
            config.inbox_dir,
            config.audio_extensions
        )
        
        logger.info(f"  - Audio files: {len(audio_files)}")
        
        # Prepare local backup directory
        local_backup_dir = config.working_dir / "organized_for_upload"
        local_backup_dir.mkdir(exist_ok=True)
        
        # Organize files
        folder_map = folder_organizer.organize_to_drive(
            processed_folder_id=config.processed_folder_id,
            transcripts_dir=config.transcripts_dir,
            parsed_dir=config.parsed_dir,
            summaries_dir=config.uploaded_dir,
            audio_files=audio_files,
            local_backup_dir=local_backup_dir
        )
        
        if folder_map:
            logger.success(f"Successfully organized {len(folder_map)} file sets to Google Drive")
            
            # Optionally sync audio files between folders
            if hasattr(config, 'to_be_transcribed_folder_id') and hasattr(config, 'transcribed_folder_id'):
                logger.info("Syncing audio files between Google Drive folders...")
                folder_organizer.sync_audio_files(
                    from_folder_id=config.to_be_transcribed_folder_id,
                    to_folder_id=config.transcribed_folder_id,
                    processed_stems=list(folder_map.keys())
                )
        else:
            logger.warning("No files were organized")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to organize files: {e}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Organize processed files to Google Drive folders")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be organized without uploading")
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be uploaded")
        # TODO: Implement dry run mode
    
    success = organize_existing_files()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()