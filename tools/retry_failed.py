#!/usr/bin/env python3
"""
Retry failed operations in the Gemini STT pipeline.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import audio compatibility first
from src.core.audio_compat import setup_audio_compatibility

from src.core import Config, PipelineState
from src.core.logger import logger
from src.storage import GoogleDriveManager


def retry_failed_syncs():
    """Retry failed Google Drive syncs."""
    try:
        # Load configuration and state
        config = Config()
        state = PipelineState()
        
        # Check for failed syncs
        failed_syncs = state.get_failed_syncs()
        if not failed_syncs:
            logger.info("No failed syncs found")
            return
        
        logger.info(f"Found {len(failed_syncs)} failed sync(s): {', '.join(failed_syncs)}")
        
        # Initialize Google Drive
        gdrive = GoogleDriveManager(
            config.gdrive_service_account_json,
            config.google_scopes
        )
        
        # Get all summaries
        summaries = state.get_summaries()
        
        # Retry each failed sync
        retry_success = []
        retry_failed = []
        
        for stem in failed_syncs:
            if stem not in summaries:
                logger.warning(f"No summary found for {stem}, skipping")
                continue
            
            logger.info(f"Retrying sync for {stem}...")
            
            try:
                # Create folder
                folder_id = gdrive.ensure_folder(
                    config.processed_folder_id,
                    stem
                )
                
                # Upload files
                files_to_upload = [
                    config.transcripts_dir / f"{stem}.txt",
                    config.parsed_dir / f"{stem}_parsed.txt",
                    config.uploaded_dir / f"{stem}.md"
                ]
                
                for file_path in files_to_upload:
                    if file_path.exists():
                        gdrive.upload_file(file_path, folder_id)
                        logger.info(f"  Uploaded {file_path.name}")
                
                # Mark as synced
                state.add_gdrive_sync(stem, folder_id)
                retry_success.append(stem)
                logger.success(f"Successfully synced {stem}")
                
            except Exception as e:
                logger.error(f"Failed again: {e}")
                retry_failed.append(stem)
        
        # Summary
        logger.info("\nRetry Summary:")
        if retry_success:
            logger.success(f"Successfully synced: {len(retry_success)} files")
        if retry_failed:
            logger.error(f"Still failed: {len(retry_failed)} files")
    
    except Exception as e:
        logger.error(f"Error during retry: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Retry failed operations")
    parser.add_argument("--sync", action="store_true", 
                       help="Retry failed Google Drive syncs")
    parser.add_argument("--all", action="store_true",
                       help="Retry all failed operations")
    
    args = parser.parse_args()
    
    if not any([args.sync, args.all]):
        parser.print_help()
        return
    
    if args.sync or args.all:
        retry_failed_syncs()


if __name__ == "__main__":
    main()