#!/usr/bin/env python3
"""
Standalone video processing script.
Extracts audio from video files without running the full transcription pipeline.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import audio compatibility first for Python 3.13+
from src.core.audio_compat import setup_audio_compatibility

from src.core import Config
from src.core.logger import logger
from src.audio import VideoProcessor


def main():
    """Process videos and extract audio."""
    try:
        # Load configuration
        config = Config()
        
        # Check video processing configuration
        if not config.process_videos:
            logger.error("Video processing is disabled in configuration")
            logger.info("Set PROCESS_VIDEOS=true in .env file")
            return
        
        if not config.video_input_dir:
            logger.error("VIDEO_INPUT_DIR is not set in configuration")
            return
        
        video_dir = Path(config.video_input_dir)
        if not video_dir.exists():
            logger.error(f"Video directory not found: {video_dir}")
            return
        
        # Determine output directory
        audio_output_dir = Path(config.audio_input_dir) if config.audio_input_dir else video_dir / "audio_only"
        
        logger.info(f"Video input directory: {video_dir}")
        logger.info(f"Audio output directory: {audio_output_dir}")
        
        # Initialize video processor
        processor = VideoProcessor(
            video_extensions=config.video_extensions,
            audio_format=config.video_audio_format,
            audio_bitrate=config.video_audio_bitrate,
            audio_samplerate=config.video_audio_samplerate
        )
        
        # Process videos
        results = processor.process_videos(
            input_dir=video_dir,
            output_dir=audio_output_dir,
            move_to_processed=True
        )
        
        if results["successful"]:
            logger.success(f"Successfully extracted audio from {len(results['successful'])} video(s)")
            logger.info(f"Audio files saved to: {audio_output_dir}")
        else:
            logger.warning("No videos were processed successfully")
            
    except Exception as e:
        logger.failure(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()