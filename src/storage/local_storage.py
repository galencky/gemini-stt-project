"""Local storage operations."""

import shutil
from pathlib import Path
from typing import List, Optional

from ..core.logger import logger
from ..core.exceptions import StorageError


class LocalStorageManager:
    """Manages local file storage operations."""
    
    @staticmethod
    def find_files(directory: Path, extensions: set, recursive: bool = True) -> List[Path]:
        """Find files with specific extensions in a directory.
        
        Args:
            directory: Directory to search
            extensions: Set of file extensions (e.g., {'.mp3', '.wav'})
            recursive: Whether to search recursively
            
        Returns:
            List of file paths
        """
        files = []
        
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return files
        
        for ext in extensions:
            if recursive:
                files.extend(directory.rglob(f"*{ext}"))
                files.extend(directory.rglob(f"*{ext.upper()}"))
            else:
                files.extend(directory.glob(f"*{ext}"))
                files.extend(directory.glob(f"*{ext.upper()}"))
        
        # Remove duplicates and sort
        files = sorted(set(files))
        
        logger.info(f"Found {len(files)} files with extensions {extensions} in {directory}")
        return files
    
    @staticmethod
    def copy_files(files: List[Path], dest_dir: Path, preserve_structure: bool = False) -> List[Path]:
        """Copy files to destination directory.
        
        Args:
            files: List of files to copy
            dest_dir: Destination directory
            preserve_structure: Whether to preserve directory structure
            
        Returns:
            List of destination paths
        """
        copied_files = []
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for file in files:
            try:
                if preserve_structure and file.parent != file.parent.parent:
                    # Preserve relative directory structure
                    rel_path = file.relative_to(file.parent.parent)
                    dest_path = dest_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    dest_path = dest_dir / file.name
                
                shutil.copy2(file, dest_path)
                copied_files.append(dest_path)
                logger.debug(f"Copied {file.name} to {dest_path}")
                
            except Exception as e:
                logger.error(f"Failed to copy {file}: {e}")
        
        logger.info(f"Copied {len(copied_files)} files to {dest_dir}")
        return copied_files
    
    @staticmethod
    def move_files(files: List[Path], dest_dir: Path) -> List[Path]:
        """Move files to destination directory.
        
        Args:
            files: List of files to move
            dest_dir: Destination directory
            
        Returns:
            List of destination paths
        """
        moved_files = []
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for file in files:
            try:
                dest_path = dest_dir / file.name
                shutil.move(str(file), str(dest_path))
                moved_files.append(dest_path)
                logger.debug(f"Moved {file.name} to {dest_path}")
                
            except Exception as e:
                logger.error(f"Failed to move {file}: {e}")
        
        logger.info(f"Moved {len(moved_files)} files to {dest_dir}")
        return moved_files
    
    @staticmethod
    def ensure_directory(directory: Path) -> Path:
        """Ensure a directory exists, creating if necessary.
        
        Args:
            directory: Directory path
            
        Returns:
            Directory path
        """
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    
    @staticmethod
    def read_file(file_path: Path, encoding: str = 'utf-8') -> str:
        """Read text file contents.
        
        Args:
            file_path: Path to file
            encoding: File encoding
            
        Returns:
            File contents
            
        Raises:
            StorageError: If read fails
        """
        try:
            with file_path.open('r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            raise StorageError(f"Failed to read {file_path}: {e}") from e
    
    @staticmethod
    def write_file(file_path: Path, content: str, encoding: str = 'utf-8'):
        """Write content to text file.
        
        Args:
            file_path: Path to file
            content: Content to write
            encoding: File encoding
            
        Raises:
            StorageError: If write fails
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open('w', encoding=encoding) as f:
                f.write(content)
            logger.debug(f"Wrote {len(content)} characters to {file_path}")
        except Exception as e:
            raise StorageError(f"Failed to write {file_path}: {e}") from e
    
    @staticmethod
    def cleanup_directory(directory: Path, keep_empty: bool = False):
        """Clean up a directory by removing all contents.
        
        Args:
            directory: Directory to clean
            keep_empty: Whether to keep the empty directory
        """
        if not directory.exists():
            return
        
        try:
            if keep_empty:
                # Remove only contents
                for item in directory.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                logger.info(f"Cleaned contents of {directory}")
            else:
                # Remove entire directory
                shutil.rmtree(directory)
                logger.info(f"Removed directory {directory}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup {directory}: {e}")