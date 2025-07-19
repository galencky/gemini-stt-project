import math
import tempfile
from pathlib import Path
from typing import List, Optional
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

class AudioProcessor:
    def __init__(self, chunk_duration_seconds: int = 300):
        """Initialize audio processor with chunk duration in seconds."""
        self.chunk_duration_seconds = chunk_duration_seconds
        self.chunk_duration_ms = chunk_duration_seconds * 1000
    
    def get_audio_duration(self, audio_path: Path) -> Optional[float]:
        """Get audio duration in seconds."""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0  # Convert milliseconds to seconds
        except CouldntDecodeError as e:
            print(f"❌ Could not decode audio file {audio_path}: {e}")
            return None
        except Exception as e:
            print(f"❌ Error getting audio duration: {e}")
            return None
    
    def split_audio_into_chunks(self, audio_path: Path) -> List[Path]:
        """Split audio file into chunks of specified duration."""
        chunks = []
        
        try:
            # Load audio
            print(f"Loading audio file: {audio_path}")
            audio = AudioSegment.from_file(str(audio_path))
            total_duration = len(audio) / 1000.0  # Convert to seconds
            
            print(f"Total audio duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
            
            # Calculate number of chunks
            num_chunks = math.ceil(total_duration / self.chunk_duration_seconds)
            
            if num_chunks == 1:
                print("Audio is shorter than chunk duration, processing as single file")
                return [audio_path]
            
            print(f"Splitting audio into {num_chunks} chunks of {self.chunk_duration_seconds} seconds each...")
            
            # Create temporary directory for chunks
            temp_dir = Path(tempfile.mkdtemp())
            
            for i in range(num_chunks):
                start_ms = i * self.chunk_duration_ms
                end_ms = min((i + 1) * self.chunk_duration_ms, len(audio))
                
                # Extract chunk
                chunk = audio[start_ms:end_ms]
                
                # Save chunk as WAV for better compatibility
                chunk_path = temp_dir / f"chunk_{i+1:03d}.wav"
                chunk.export(chunk_path, format="wav")
                
                chunk_duration = (end_ms - start_ms) / 1000.0
                print(f"Created chunk {i+1}/{num_chunks} (duration: {chunk_duration:.1f}s)")
                chunks.append(chunk_path)
            
            print(f"✅ Successfully created {len(chunks)} chunks")
            return chunks
            
        except CouldntDecodeError as e:
            print(f"❌ Could not decode audio file: {e}")
            print("Attempting to process as single file...")
            return [audio_path]
        except Exception as e:
            print(f"❌ Error splitting audio: {e}")
            print("Attempting to process as single file...")
            return [audio_path]
    
    def cleanup_chunks(self, chunk_paths: List[Path], original_path: Path) -> None:
        """Clean up temporary chunk files."""
        if len(chunk_paths) <= 1:
            return  # No chunks to clean up
        
        # Only clean up if the chunks are in a different directory than the original
        if chunk_paths and chunk_paths[0].parent != original_path.parent:
            temp_dir = chunk_paths[0].parent
            
            # Remove chunk files
            for chunk in chunk_paths:
                if chunk.exists():
                    try:
                        chunk.unlink()
                    except Exception as e:
                        print(f"Warning: Could not remove chunk file {chunk}: {e}")
            
            # Remove temporary directory if empty
            if temp_dir.exists():
                try:
                    temp_dir.rmdir()
                    print(f"✅ Cleaned up temporary chunk directory: {temp_dir}")
                except Exception as e:
                    print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")
    
    def convert_to_wav(self, audio_path: Path, output_dir: Path) -> Optional[Path]:
        """Convert audio file to WAV format for better compatibility."""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            wav_path = output_dir / f"{audio_path.stem}.wav"
            audio.export(wav_path, format="wav")
            print(f"✅ Converted {audio_path.name} to WAV format")
            return wav_path
        except Exception as e:
            print(f"❌ Error converting to WAV: {e}")
            return None
    
    def get_audio_info(self, audio_path: Path) -> dict:
        """Get detailed information about an audio file."""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            
            info = {
                "filename": audio_path.name,
                "duration_seconds": len(audio) / 1000.0,
                "duration_formatted": self.format_duration(len(audio) / 1000.0),
                "channels": audio.channels,
                "sample_rate": audio.frame_rate,
                "sample_width": audio.sample_width,
                "format": audio_path.suffix[1:].upper()
            }
            
            return info
            
        except Exception as e:
            print(f"❌ Error getting audio info: {e}")
            return {
                "filename": audio_path.name,
                "error": str(e)
            }
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def is_audio_file(file_path: Path, audio_extensions: set = None) -> bool:
        """Check if a file is an audio file based on its extension."""
        if audio_extensions is None:
            audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm', '.aac', '.wma'}
        
        return file_path.suffix.lower() in audio_extensions