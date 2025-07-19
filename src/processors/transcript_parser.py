import re
from pathlib import Path
from typing import List, Optional
from datetime import timedelta

class TranscriptParser:
    def __init__(self):
        """Initialize transcript parser."""
        pass
    
    def parse_transcript_simple(self, text: str) -> str:
        """Parse transcript into 5-minute blocks with preserved formatting."""
        lines = text.strip().split('\n')
        
        result = []
        current_block = []
        
        for line in lines:
            line = line.strip()
            
            # Check if this is a timestamp line
            if self._is_timestamp_line(line):
                # If we have accumulated content, add it to result
                if current_block:
                    result.append('\n'.join(current_block))
                    result.append('')  # blank line between blocks
                    current_block = []
                
                # Add the timestamp line
                result.append(line)
            elif line:  # Non-empty, non-timestamp line
                current_block.append(line)
        
        # Add any remaining content
        if current_block:
            result.append('\n'.join(current_block))
        
        return '\n'.join(result)
    
    def _is_timestamp_line(self, line: str) -> bool:
        """Check if a line is a timestamp line."""
        # Pattern matches [HH:MM:SS.mmm] format
        timestamp_pattern = r'^\[\d{2}:\d{2}:\d{2}\.\d{3}\]$'
        return bool(re.match(timestamp_pattern, line.strip()))
    
    def parse_transcript_file(self, input_path: Path, output_path: Path) -> bool:
        """Parse a transcript file and save the result."""
        try:
            # Read the transcript
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Parse it
            parsed_text = self.parse_transcript_simple(text)
            
            # Save the parsed version
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(parsed_text)
            
            print(f"✅ Parsed transcript saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error parsing transcript {input_path}: {e}")
            return False
    
    def batch_parse_transcripts(self, input_dir: Path, output_dir: Path) -> dict:
        """Parse all transcript files in a directory."""
        results = {
            "successful": [],
            "failed": []
        }
        
        # Find all .txt files in input directory
        txt_files = list(input_dir.glob("*.txt"))
        
        if not txt_files:
            print(f"⚠️  No .txt files found in {input_dir}")
            return results
        
        print(f"\n📄 Found {len(txt_files)} transcript files to parse")
        
        for txt_file in txt_files:
            print(f"\nParsing: {txt_file.name}")
            
            # Create output filename
            output_filename = txt_file.name.replace('.txt', '_parsed.txt')
            output_path = output_dir / output_filename
            
            # Parse the file
            if self.parse_transcript_file(txt_file, output_path):
                results["successful"].append({
                    "input": txt_file,
                    "output": output_path
                })
            else:
                results["failed"].append({
                    "input": txt_file,
                    "error": "Parsing failed"
                })
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"Parsing complete!")
        print(f"✅ Successful: {len(results['successful'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        
        return results
    
    def extract_timestamps_and_text(self, text: str) -> List[dict]:
        """Extract timestamps and their associated text blocks."""
        blocks = []
        lines = text.strip().split('\n')
        
        current_timestamp = None
        current_text = []
        
        for line in lines:
            line = line.strip()
            
            if self._is_timestamp_line(line):
                # Save previous block if exists
                if current_timestamp and current_text:
                    blocks.append({
                        "timestamp": current_timestamp,
                        "text": '\n'.join(current_text).strip()
                    })
                
                # Start new block
                current_timestamp = line.strip('[]')
                current_text = []
            elif line:  # Non-empty line
                current_text.append(line)
        
        # Add last block
        if current_timestamp and current_text:
            blocks.append({
                "timestamp": current_timestamp,
                "text": '\n'.join(current_text).strip()
            })
        
        return blocks
    
    def format_with_speaker_detection(self, text: str) -> str:
        """Format transcript with basic speaker detection."""
        # This is a simple implementation - can be enhanced with more sophisticated speaker detection
        lines = text.strip().split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Simple speaker detection based on common patterns
            # Can be enhanced based on actual transcript patterns
            if line.startswith(('Speaker', 'Doctor', 'Patient', 'Nurse')):
                formatted_lines.append(f"\n**{line}**")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)