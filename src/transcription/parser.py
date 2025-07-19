"""Transcript parsing utilities."""

import re
from typing import List, Tuple


class TranscriptParser:
    """Handles parsing and formatting of transcripts."""
    
    @staticmethod
    def parse_transcript_simple(text: str) -> str:
        """Parse transcript into time blocks with preserved formatting.
        
        Args:
            text: Raw transcript text
            
        Returns:
            Formatted transcript with time blocks
        """
        lines = text.strip().split('\n')
        
        result = []
        current_block = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('[') and line.endswith(']') and re.match(r'\[\d{2}:\d{2}:\d{2}\.\d{3}\]', line):
                # This is a timestamp line
                if current_block:
                    result.append('\n'.join(current_block))
                    result.append('')  # blank line
                    current_block = []
                result.append(line)
            elif line:
                current_block.append(line)
        
        if current_block:
            result.append('\n'.join(current_block))
        
        return '\n'.join(result)
    
    @staticmethod
    def extract_timestamps(text: str) -> List[Tuple[str, str]]:
        """Extract timestamps and their associated text blocks.
        
        Args:
            text: Transcript text with timestamps
            
        Returns:
            List of (timestamp, text) tuples
        """
        timestamp_pattern = r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]'
        blocks = []
        
        # Split by timestamps
        parts = re.split(timestamp_pattern, text.strip())
        
        # Parts will be: ['', timestamp1, text1, timestamp2, text2, ...]
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                timestamp = parts[i]
                text_block = parts[i + 1].strip()
                if text_block:
                    blocks.append((timestamp, text_block))
        
        return blocks
    
    @staticmethod
    def format_for_display(text: str, include_timestamps: bool = True) -> str:
        """Format transcript for display.
        
        Args:
            text: Raw transcript text
            include_timestamps: Whether to include timestamps
            
        Returns:
            Formatted text for display
        """
        if not include_timestamps:
            # Remove timestamps
            return re.sub(r'\[\d{2}:\d{2}:\d{2}\.\d{3}\]\n?', '', text).strip()
        
        # Ensure proper formatting with timestamps
        return TranscriptParser.parse_transcript_simple(text)