#!/usr/bin/env python3
"""Update all batch files to work from bin directory."""

from pathlib import Path

# Add the cd command after @echo off
CD_COMMAND = '\nREM Move to project root\ncd /d "%~dp0\\.."\n'

# Files to update
batch_files = [
    "bin/run_video_only.bat",
    "bin/setup_windows.bat",
    "bin/manage_state.bat",
    "bin/diagnose.bat"
]

for batch_file in batch_files:
    file_path = Path(batch_file)
    if file_path.exists():
        # Read content
        content = file_path.read_text()
        
        # Check if already updated
        if "cd /d" in content:
            print(f"✓ {batch_file} already updated")
            continue
        
        # Find @echo off and add cd command after it
        lines = content.splitlines()
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            if line.strip() == "@echo off" and i < len(lines) - 1:
                # Add cd command after @echo off
                new_lines.append("REM Move to project root")
                new_lines.append('cd /d "%~dp0\\.."')
                if i + 1 < len(lines) and lines[i + 1].strip():
                    new_lines.append("")  # Add blank line
        
        # Also update references to other batch files
        new_content = '\n'.join(new_lines)
        new_content = new_content.replace("setup_windows.bat", "bin\\setup_windows.bat")
        
        # Write back
        file_path.write_text(new_content)
        print(f"✅ Updated {batch_file}")

print("\nBatch files updated!")