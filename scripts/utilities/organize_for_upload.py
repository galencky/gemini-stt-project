#!/usr/bin/env python3
"""
Organize processed files into folders for manual upload
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')
from src.utils import config

def organize_files():
    """Organize processed files into folders matching Google Drive structure."""
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output_for_upload") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🗂️  Organizing files for manual upload...")
    print(f"📁 Output directory: {output_dir.absolute()}\n")
    
    # Find all processed files
    transcript_files = list(config.TRANSCRIPTS_DIR.glob("*.txt"))
    
    if not transcript_files:
        print("❌ No processed files found!")
        return
    
    organized_count = 0
    
    for transcript_file in transcript_files:
        # Get base name (without .txt)
        base_name = transcript_file.stem
        
        # Expected files
        parsed_file = config.PARSED_DIR / f"{base_name}_parsed.txt"
        summary_file = config.MARKDOWN_DIR / f"{base_name}.md"
        
        # Check if all files exist
        files_exist = {
            "transcript": transcript_file.exists(),
            "parsed": parsed_file.exists(),
            "summary": summary_file.exists()
        }
        
        print(f"📄 {base_name}:")
        for file_type, exists in files_exist.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {file_type}")
        
        # Create folder for this audio file
        file_folder = output_dir / base_name
        file_folder.mkdir(exist_ok=True)
        
        # Copy files
        copied = False
        if transcript_file.exists():
            shutil.copy2(transcript_file, file_folder / f"{base_name}.txt")
            copied = True
        
        if parsed_file.exists():
            shutil.copy2(parsed_file, file_folder / f"{base_name}_parsed.txt")
            copied = True
            
        if summary_file.exists():
            shutil.copy2(summary_file, file_folder / f"{base_name}.md")
            copied = True
        
        if copied:
            print(f"   📁 Organized in: {file_folder.relative_to(output_dir.parent)}")
            organized_count += 1
        
        print()
    
    # Create upload instructions
    instructions_file = output_dir / "UPLOAD_INSTRUCTIONS.txt"
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write("Google Drive Upload Instructions\n")
        f.write("================================\n\n")
        f.write("1. Go to your Google Drive PROCESSED folder\n")
        f.write("2. For each folder in this directory:\n")
        f.write("   - Create a new folder with the same name\n")
        f.write("   - Upload all files from that folder\n\n")
        f.write("3. After uploading, move the original audio files from:\n")
        f.write("   TO_BE_TRANSCRIBED folder -> TRANSCRIBED folder\n\n")
        f.write("Folders to upload:\n")
        f.write("-----------------\n")
        
        for folder in sorted(output_dir.iterdir()):
            if folder.is_dir():
                file_count = len(list(folder.glob("*")))
                f.write(f"- {folder.name} ({file_count} files)\n")
    
    print(f"\n{'='*60}")
    print(f"✅ Organized {organized_count} file sets")
    print(f"📁 Output location: {output_dir.absolute()}")
    print(f"📋 See UPLOAD_INSTRUCTIONS.txt for next steps")
    print(f"{'='*60}")
    
    # Also check for HackMD uploaded files
    uploaded_md_files = list(config.UPLOADED_DIR.glob("*.md"))
    if uploaded_md_files:
        print(f"\n📝 HackMD uploaded files ({len(uploaded_md_files)}):")
        for md_file in uploaded_md_files[:5]:  # Show first 5
            print(f"   - {md_file.name}")
        if len(uploaded_md_files) > 5:
            print(f"   ... and {len(uploaded_md_files) - 5} more")

if __name__ == "__main__":
    organize_files()