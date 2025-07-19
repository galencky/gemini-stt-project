import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional

class VideoProcessor:
    def __init__(self, video_extensions: set = None, audio_format: str = 'm4a', 
                 audio_bitrate: str = '192k', audio_samplerate: int = 44100):
        """Initialize video processor with configuration."""
        self.video_extensions = video_extensions or {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}
        self.audio_format = audio_format
        self.audio_bitrate = audio_bitrate
        self.audio_samplerate = audio_samplerate
        
        # Check if ffmpeg is available
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available in the system PATH."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  FFmpeg not found. Please install FFmpeg to process videos.")
            return False
    
    def find_video_files(self, directory: Path) -> List[Path]:
        """Find all video files in the specified directory."""
        video_files = []
        
        if not directory.exists():
            print(f"❌ Directory not found: {directory}")
            return video_files
        
        # Find all video files
        for ext in self.video_extensions:
            video_files.extend(directory.glob(f"*{ext}"))
            video_files.extend(directory.glob(f"*{ext.upper()}"))
        
        # Remove duplicates and sort
        video_files = sorted(set(video_files))
        
        return video_files
    
    def extract_audio_from_video(self, video_path: Path, output_path: Path) -> bool:
        """Extract audio from a single video file."""
        if not self.ffmpeg_available:
            return False
        
        try:
            # Determine codec based on output format
            audio_codec = self._get_audio_codec(self.audio_format)
            
            # FFmpeg command to extract audio
            cmd = [
                "ffmpeg",
                "-y",                              # overwrite existing
                "-i", str(video_path),             # input file
                "-vn",                             # no video
                "-c:a", audio_codec,               # audio codec
                "-ac", "2",                        # stereo
                "-ar", str(self.audio_samplerate), # sample rate
                "-b:a", self.audio_bitrate,        # bitrate
                str(output_path)
            ]
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg error: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Error extracting audio: {e}")
            return False
    
    def _get_audio_codec(self, format: str) -> str:
        """Get the appropriate audio codec for the output format."""
        codec_map = {
            'm4a': 'aac',
            'mp3': 'libmp3lame',
            'wav': 'pcm_s16le',
            'flac': 'flac',
            'ogg': 'libvorbis',
            'wma': 'wmav2'
        }
        return codec_map.get(format, 'aac')
    
    def process_videos(self, input_dir: Path, output_dir: Path, 
                      move_to_processed: bool = True) -> Dict:
        """Process all videos in input directory and extract audio."""
        results = {
            "successful": [],
            "failed": [],
            "extracted_audio": []
        }
        
        if not self.ffmpeg_available:
            print("❌ Cannot process videos without FFmpeg")
            return results
        
        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find video files
        video_files = self.find_video_files(input_dir)
        
        if not video_files:
            print(f"ℹ️  No video files found in {input_dir}")
            return results
        
        print(f"\n🎥 Found {len(video_files)} video files to process")
        print("Files found:")
        for video in video_files:
            print(f"  - {video.name}")
        print()
        
        # Create processed directory if moving files
        if move_to_processed:
            processed_dir = input_dir / "processed_videos"
            processed_dir.mkdir(exist_ok=True)
        
        # Process each video
        for video_file in video_files:
            output_file = output_dir / f"{video_file.stem}_audio.{self.audio_format}"
            
            print(f"📹 Processing: {video_file.name}")
            
            if self.extract_audio_from_video(video_file, output_file):
                print(f"✅ Extracted audio: {output_file.name}")
                results["successful"].append(video_file)
                results["extracted_audio"].append(output_file)
                
                # Move processed video if requested
                if move_to_processed:
                    try:
                        dest = processed_dir / video_file.name
                        shutil.move(str(video_file), str(dest))
                        print(f"   Moved video to: {dest}")
                    except Exception as e:
                        print(f"   Warning: Could not move video: {e}")
            else:
                results["failed"].append(video_file)
            
            print()
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"Video processing complete!")
        print(f"✅ Successfully processed: {len(results['successful'])}/{len(video_files)} videos")
        print(f"🎵 Audio files created: {len(results['extracted_audio'])}")
        if results["failed"]:
            print(f"❌ Failed: {len(results['failed'])}")
        print(f"{'='*60}")
        
        return results
    
    def batch_extract_audio(self, video_files: List[Path], output_dir: Path) -> List[Path]:
        """Extract audio from a list of video files."""
        extracted_files = []
        
        for video_file in video_files:
            output_file = output_dir / f"{video_file.stem}_audio.{self.audio_format}"
            
            if self.extract_audio_from_video(video_file, output_file):
                extracted_files.append(output_file)
        
        return extracted_files
    
    def get_video_info(self, video_path: Path) -> Optional[Dict]:
        """Get information about a video file using ffprobe."""
        if not self.ffmpeg_available:
            return None
        
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            info = json.loads(result.stdout)
            
            # Extract relevant information
            video_info = {
                "filename": video_path.name,
                "duration": float(info.get("format", {}).get("duration", 0)),
                "size_mb": int(info.get("format", {}).get("size", 0)) / (1024 * 1024),
                "format": info.get("format", {}).get("format_name", "unknown")
            }
            
            # Find video and audio streams
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video" and "video_codec" not in video_info:
                    video_info["video_codec"] = stream.get("codec_name")
                    video_info["resolution"] = f"{stream.get('width')}x{stream.get('height')}"
                elif stream.get("codec_type") == "audio" and "audio_codec" not in video_info:
                    video_info["audio_codec"] = stream.get("codec_name")
                    video_info["audio_channels"] = stream.get("channels")
                    video_info["audio_samplerate"] = stream.get("sample_rate")
            
            return video_info
            
        except Exception as e:
            print(f"❌ Error getting video info: {e}")
            return None