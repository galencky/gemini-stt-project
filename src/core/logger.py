"""Logging utilities for Gemini STT."""

import datetime
import logging
from pathlib import Path
from typing import Optional


class Logger:
    """Custom logger with timestamp formatting."""
    
    def __init__(self, name: str = "GeminiSTT", log_file: Optional[str] = None):
        """Initialize logger with optional file output."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Console handler with custom format
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_format = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
    
    def success(self, message: str):
        """Log success message with checkmark."""
        self.logger.info(f"✅ {message}")
    
    def failure(self, message: str):
        """Log failure message with X mark."""
        self.logger.error(f"❌ {message}")
    
    def progress(self, message: str):
        """Log progress message with arrow."""
        self.logger.info(f"→ {message}")


# Global logger instance
logger = Logger()