import subprocess
import os
from pathlib import Path

# Directory containing videos to process
input_dir = Path(r"C:\Users\galen\Videos\audio_strip")
output_dir = input_dir / "audio_only"

# Create output directory if it doesn't exist
output_dir.mkdir(exist_ok=True)

# Video extensions to process
video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}

# Find all video files (case-insensitive)
video_files = [f for f in input_dir.iterdir() 
               if f.suffix.lower() in video_extensions and f.is_file()]

# Remove duplicates by converting to set of resolved paths
video_files = list(set(video_files))

print(f"Found {len(video_files)} video files to process\n")

# Debug: Print all found files
print("Files found:")
for f in video_files:
    print(f"  - {f.name}")
print()

# Process each video
success_count = 0
for video_file in video_files:
    output_file = output_dir / f"{video_file.stem}_audio.m4a"
    
    # FFmpeg command to extract audio
    cmd = [
        "ffmpeg",
        "-y",                    # overwrite existing
        "-i", str(video_file),   # input file
        "-vn",                   # no video
        "-c:a", "aac",           # AAC audio codec
        "-ac", "2",              # stereo
        "-ar", "44100",          # 44.1kHz sample rate
        "-b:a", "192k",          # 192kbps bitrate
        str(output_file)
    ]
    
    print(f"Processing: {video_file.name}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Extracted audio: {output_file.name}")
        success_count += 1
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e.stderr}")
    print()

print(f"\nProcessing complete!")
print(f"✅ Successfully extracted audio from: {success_count}/{len(video_files)} files")
print(f"📁 Output directory: {output_dir}")