#!/usr/bin/env python3
"""Check if Google Drive folders are in Shared Drives or My Drive."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import Config
from src.core.logger import logger
from src.storage import GoogleDriveManager


def check_drive_types():
    """Check the type of drives for configured folders."""
    try:
        # Load configuration
        config = Config()
        
        # Initialize Google Drive manager
        gdrive = GoogleDriveManager(
            config.gdrive_service_account_json,
            config.google_scopes
        )
        
        folders_to_check = [
            ("TO_BE_TRANSCRIBED_FOLDER", config.to_be_transcribed_folder_id),
            ("TRANSCRIBED_FOLDER", config.transcribed_folder_id),
            ("PROCESSED_FOLDER", config.processed_folder_id)
        ]
        
        logger.info("Checking Google Drive folder types...")
        logger.info("=" * 60)
        
        for folder_name, folder_id in folders_to_check:
            if not folder_id:
                logger.warning(f"{folder_name}: Not configured")
                continue
                
            try:
                # Get folder metadata
                result = gdrive.service.files().get(
                    fileId=folder_id,
                    fields="id,name,driveId,parents",
                    supportsAllDrives=True
                ).execute()
                
                folder_name_actual = result.get('name', 'Unknown')
                drive_id = result.get('driveId')
                
                if drive_id:
                    # It's in a shared drive
                    drive_info = gdrive.service.drives().get(driveId=drive_id).execute()
                    drive_name = drive_info.get('name', 'Unknown')
                    logger.success(f"{folder_name}: '{folder_name_actual}' is in Shared Drive '{drive_name}'")
                else:
                    # It's in My Drive
                    logger.warning(f"{folder_name}: '{folder_name_actual}' is in My Drive (may have quota issues)")
                    
            except Exception as e:
                logger.error(f"{folder_name}: Failed to check - {e}")
        
        logger.info("=" * 60)
        logger.info("\nNote: Service accounts work best with Shared Drives.")
        logger.info("If your folders are in My Drive, see docs/SERVICE_ACCOUNT_QUOTA.md")
        
    except Exception as e:
        logger.error(f"Failed to check drive types: {e}")
        return False
    
    return True


def main():
    """Main entry point."""
    success = check_drive_types()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()