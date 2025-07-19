#!/usr/bin/env python3
"""Cleanup working directories after successful processing."""

import sys
from pathlib import Path
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import Config, PipelineState
from src.core.logger import logger


def cleanup_working_directories(dry_run=True):
    """Clean up working directories for files that have been successfully organized.
    
    Args:
        dry_run: If True, only show what would be deleted without actually deleting
    """
    try:
        # Load configuration and state
        config = Config()
        state = PipelineState()
        
        # Get organized files from state
        organized_files = state.state.get("folders_organized", {})
        
        if not organized_files:
            logger.info("No organized files found in state. Nothing to clean up.")
            return
        
        logger.info(f"Found {len(organized_files)} organized file(s) in state")
        
        if dry_run:
            logger.info("DRY RUN MODE - No files will be deleted")
        
        files_to_clean = []
        
        # Check each organized file
        for stem, info in organized_files.items():
            logger.info(f"\nChecking {stem} (organized to {info['location']})")
            
            # Files to check for cleanup
            file_paths = [
                (config.transcripts_dir / f"{stem}.txt", "transcript"),
                (config.parsed_dir / f"{stem}_parsed.txt", "parsed"),
                (config.markdown_dir / f"{stem}.md", "markdown"),
                (config.uploaded_dir / f"{stem}.md", "uploaded summary"),
                (config.inbox_dir / f"{stem}.m4a", "audio"),
                (config.inbox_dir / f"{stem}_audio.m4a", "audio"),
            ]
            
            for file_path, file_type in file_paths:
                if file_path.exists():
                    files_to_clean.append((file_path, file_type))
                    if dry_run:
                        logger.info(f"  Would delete {file_type}: {file_path.name}")
        
        if not files_to_clean:
            logger.info("\nNo files to clean up.")
            return
        
        if not dry_run:
            logger.warning(f"\nAbout to delete {len(files_to_clean)} file(s)")
            response = input("Are you sure you want to delete these files? (yes/no): ")
            
            if response.lower() != "yes":
                logger.info("Cleanup cancelled.")
                return
            
            # Delete files
            deleted_count = 0
            for file_path, file_type in files_to_clean:
                try:
                    file_path.unlink()
                    logger.info(f"Deleted {file_type}: {file_path.name}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file_path.name}: {e}")
            
            logger.success(f"\nDeleted {deleted_count} file(s)")
        else:
            logger.info(f"\nWould delete {len(files_to_clean)} file(s) total")
            logger.info("Run with --execute to actually delete files")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return False
    
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up working directories for organized files")
    parser.add_argument("--execute", action="store_true", 
                       help="Actually delete files (default is dry run)")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Working Directory Cleanup")
    logger.info("=" * 60)
    
    success = cleanup_working_directories(dry_run=not args.execute)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()