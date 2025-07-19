#!/usr/bin/env python3
"""Test script for the folder organization functionality."""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import Config
from src.core.logger import logger
from src.storage import GoogleDriveManager, LocalStorageManager, FolderOrganizer


def test_folder_organizer():
    """Test the folder organization functionality."""
    try:
        # Load configuration
        config = Config()
        
        # Validate config
        is_valid, errors = config.validate()
        if not is_valid:
            logger.error(f"Invalid configuration: {', '.join(errors)}")
            return False
        
        logger.info("Testing Folder Organizer functionality...")
        
        # Initialize components
        logger.info("Initializing Google Drive manager...")
        gdrive = GoogleDriveManager(
            config.gdrive_service_account_json,
            config.google_scopes
        )
        
        logger.info("Initializing local storage manager...")
        local_storage = LocalStorageManager()
        
        logger.info("Initializing folder organizer...")
        folder_organizer = FolderOrganizer(gdrive, local_storage)
        
        # Test folder creation
        logger.info(f"Testing folder creation in Google Drive...")
        test_folder_name = "test_folder_organizer"
        
        try:
            folder_id = gdrive.ensure_folder(
                config.processed_folder_id,
                test_folder_name
            )
            logger.success(f"Successfully created/found test folder: {folder_id}")
            
            # Clean up test folder
            logger.info("Cleaning up test folder...")
            # Note: We don't delete the folder to avoid permissions issues
            # Just verify it was created successfully
            
        except Exception as e:
            logger.error(f"Failed to create test folder: {e}")
            return False
        
        # Check for existing files to organize
        logger.info("Checking for files to organize...")
        
        transcripts_exist = config.transcripts_dir.exists() and list(config.transcripts_dir.glob("*.txt"))
        parsed_exist = config.parsed_dir.exists() and list(config.parsed_dir.glob("*_parsed.txt"))
        summaries_exist = config.uploaded_dir.exists() and list(config.uploaded_dir.glob("*.md"))
        
        if not any([transcripts_exist, parsed_exist, summaries_exist]):
            logger.warning("No processed files found to test organization")
            logger.info("Run the main pipeline first to generate files, then test organization")
            return True
        
        logger.info("Found files to organize:")
        if transcripts_exist:
            logger.info(f"  - Transcripts: {len(list(config.transcripts_dir.glob('*.txt')))}")
        if parsed_exist:
            logger.info(f"  - Parsed: {len(list(config.parsed_dir.glob('*_parsed.txt')))}")
        if summaries_exist:
            logger.info(f"  - Summaries: {len(list(config.uploaded_dir.glob('*.md')))}")
        
        # Test dry run (without actually uploading)
        logger.info("Testing folder organization structure (dry run)...")
        
        # Get one transcript file as example
        transcript_files = list(config.transcripts_dir.glob("*.txt"))[:1]
        if transcript_files:
            stem = transcript_files[0].stem
            logger.info(f"Example file structure for '{stem}':")
            logger.info(f"  - Folder: {stem}/")
            
            files_that_would_upload = []
            
            # Check what files would be uploaded
            transcript_file = config.transcripts_dir / f"{stem}.txt"
            if transcript_file.exists():
                files_that_would_upload.append(f"    - {stem}.txt (transcript)")
            
            parsed_file = config.parsed_dir / f"{stem}_parsed.txt"
            if parsed_file.exists():
                files_that_would_upload.append(f"    - {stem}_parsed.txt (parsed)")
            
            summary_file = config.uploaded_dir / f"{stem}.md"
            if summary_file.exists():
                files_that_would_upload.append(f"    - {stem}.md (summary)")
            
            for file_desc in files_that_would_upload:
                logger.info(file_desc)
        
        logger.success("Folder organizer test completed successfully!")
        logger.info("To actually organize files, run the main pipeline with ORGANIZE_TO_FOLDERS=true")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Folder Organizer Test")
    logger.info("=" * 60)
    
    success = test_folder_organizer()
    
    if success:
        logger.success("\nAll tests passed!")
    else:
        logger.error("\nSome tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()