#!/usr/bin/env python3
"""
Standalone script to process video files and extract audio.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from video_processor import VideoProcessor

# Load environment variables
load_dotenv()

# Configuration from environment
VIDEO_INPUT_DIR = os.getenv("VIDEO_INPUT_DIR", "C:\\Users\\galen\\Videos\\audio_strip")
AUDIO_OUTPUT_DIR = os.getenv("AUDIO_INPUT_DIR", "C:\\Users\\galen\\Videos\\audio_strip\\audio_only")
VIDEO_AUDIO_FORMAT = os.getenv("VIDEO_AUDIO_FORMAT", "m4a")
VIDEO_AUDIO_BITRATE = os.getenv("VIDEO_AUDIO_BITRATE", "192k")
VIDEO_AUDIO_SAMPLERATE = int(os.getenv("VIDEO_AUDIO_SAMPLERATE", "44100"))


def main():
    """Main function to process videos."""
    video_dir = Path(VIDEO_INPUT_DIR)
    audio_dir = Path(AUDIO_OUTPUT_DIR)
    
    print(f"Video input directory: {video_dir}")
    print(f"Audio output directory: {audio_dir}")
    
    if not video_dir.exists():
        print(f"❌ Video directory not found: {video_dir}")
        return
    
    # Initialize video processor
    processor = VideoProcessor(
        audio_format=VIDEO_AUDIO_FORMAT,
        audio_bitrate=VIDEO_AUDIO_BITRATE,
        audio_samplerate=VIDEO_AUDIO_SAMPLERATE
    )
    
    # Process videos
    results = processor.process_videos(
        input_dir=video_dir,
        output_dir=audio_dir,
        move_to_processed=True
    )
    
    if results["successful"]:
        print(f"\n✅ Successfully extracted audio from {len(results['successful'])} video(s)")
        print(f"Audio files saved to: {audio_dir}")
    else:
        print("\n❌ No videos were processed successfully")


if __name__ == "__main__":
    main()