"""Audio processing and chunking utilities."""

import math
import tempfile
from pathlib import Path
from typing import List, Optional

from pydub import AudioSegment

from ..core.logger import logger
from ..core.exceptions import AudioProcessingError


class AudioProcessor:
    """Handles audio file processing and chunking."""
    
    def __init__(self, chunk_duration_seconds: int = 300):
        """Initialize audio processor.
        
        Args:
            chunk_duration_seconds: Duration of each chunk in seconds
        """
        self.chunk_duration_seconds = chunk_duration_seconds
    
    def get_audio_duration(self, audio_path: Path) -> Optional[float]:
        """Get audio duration in seconds.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds or None if error
        """
        try:
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0  # Convert milliseconds to seconds
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return None
    
    def split_audio_into_chunks(self, audio_path: Path) -> List[Path]:
        """Split audio file into chunks of specified duration.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of paths to chunk files
            
        Raises:
            AudioProcessingError: If splitting fails
        """
        chunks = []
        
        try:
            # Load audio
            audio = AudioSegment.from_file(str(audio_path))
            total_duration = len(audio) / 1000.0  # Convert to seconds
            
            logger.info(f"Total audio duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
            
            # Calculate number of chunks
            num_chunks = math.ceil(total_duration / self.chunk_duration_seconds)
            
            if num_chunks == 1:
                logger.info("Audio is shorter than chunk duration, processing as single file")
                return [audio_path]
            
            logger.info(f"Splitting audio into {num_chunks} chunks of {self.chunk_duration_seconds} seconds each...")
            
            # Create temporary directory for chunks
            temp_dir = Path(tempfile.mkdtemp(prefix="gemini_stt_chunks_"))
            chunk_duration_ms = self.chunk_duration_seconds * 1000
            
            for i in range(num_chunks):
                start_ms = i * chunk_duration_ms
                end_ms = min((i + 1) * chunk_duration_ms, len(audio))
                
                # Extract chunk
                chunk = audio[start_ms:end_ms]
                
                # Save chunk
                chunk_path = temp_dir / f"chunk_{i+1:03d}.wav"
                chunk.export(chunk_path, format="wav")
                
                logger.info(f"Created chunk {i+1}/{num_chunks} (duration: {(end_ms-start_ms)/1000:.1f}s)")
                chunks.append(chunk_path)
            
            logger.success(f"Successfully created {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            error_msg = f"Error splitting audio: {e}"
            logger.failure(error_msg)
            raise AudioProcessingError(error_msg) from e
    
    def cleanup_chunks(self, chunks: List[Path], original_path: Path):
        """Clean up temporary chunk files.
        
        Args:
            chunks: List of chunk file paths
            original_path: Path to original audio file
        """
        if len(chunks) <= 1:  # No chunks were created
            return
        
        try:
            temp_dir = chunks[0].parent
            if temp_dir != original_path.parent:  # Ensure we're in temp directory
                for chunk in chunks:
                    if chunk.exists():
                        chunk.unlink()
                if temp_dir.exists() and temp_dir.name.startswith("gemini_stt_chunks_"):
                    temp_dir.rmdir()
                logger.debug("Cleaned up temporary chunk files")
        except Exception as e:
            logger.warning(f"Failed to clean up chunk files: {e}")