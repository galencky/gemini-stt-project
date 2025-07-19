"""Gemini API transcription module."""

import time
from pathlib import Path
from typing import List, Optional

import google.generativeai as genai

from ..core.logger import logger
from ..core.exceptions import TranscriptionError
from ..audio.processor import AudioProcessor


class GeminiTranscriber:
    """Handles audio transcription using Gemini API."""
    
    def __init__(self, api_key: str, chunk_duration_seconds: int = 300, model: str = 'gemini-2.0-flash'):
        """Initialize Gemini transcriber.
        
        Args:
            api_key: Gemini API key
            chunk_duration_seconds: Duration of audio chunks
            model: Gemini model to use
        """
        self.api_key = api_key
        self.chunk_duration_seconds = chunk_duration_seconds
        self.model_name = model
        self.audio_processor = AudioProcessor(chunk_duration_seconds)
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    def transcribe_audio_chunk(self, chunk_path: Path, chunk_number: int, total_chunks: int) -> Optional[str]:
        """Transcribe a single audio chunk using Gemini API.
        
        Args:
            chunk_path: Path to audio chunk
            chunk_number: Current chunk number
            total_chunks: Total number of chunks
            
        Returns:
            Transcribed text or None if error
        """
        try:
            logger.info(f"Transcribing chunk {chunk_number}/{total_chunks}...")
            
            # Upload audio file to Gemini
            audio_file = genai.upload_file(path=str(chunk_path), display_name=f"chunk_{chunk_number}")
            
            # Wait for file to be processed
            while audio_file.state.name == "PROCESSING":
                time.sleep(1)
                audio_file = genai.get_file(audio_file.name)
            
            # Check if file was processed successfully
            if audio_file.state.name != "ACTIVE":
                raise TranscriptionError(f"File processing failed: {audio_file.state.name}")
            
            # Prepare the prompt
            prompt = self._create_transcription_prompt(chunk_number, total_chunks)
            
            # Generate transcription
            response = self.model.generate_content([prompt, audio_file])
            
            # Delete uploaded file
            try:
                genai.delete_file(audio_file.name)
            except Exception as e:
                logger.warning(f"Failed to delete uploaded file: {e}")
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error transcribing chunk {chunk_number}: {e}")
            return None
    
    def transcribe_audio_file(self, audio_path: Path) -> Optional[str]:
        """Transcribe an audio file by splitting it into chunks.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Complete transcription or None if error
            
        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            # Split audio into chunks
            chunks = self.audio_processor.split_audio_into_chunks(audio_path)
            
            if not chunks:
                raise TranscriptionError("No chunks created from audio file")
            
            # Transcribe each chunk
            transcriptions = []
            total_chunks = len(chunks)
            
            for i, chunk_path in enumerate(chunks, 1):
                logger.info(f"\n--- Processing chunk {i}/{total_chunks} ---")
                chunk_transcript = self.transcribe_audio_chunk(chunk_path, i, total_chunks)
                
                if chunk_transcript:
                    transcriptions.append(chunk_transcript)
                    logger.success(f"Successfully transcribed chunk {i}/{total_chunks}")
                else:
                    logger.warning(f"Failed to transcribe chunk {i}/{total_chunks}")
            
            # Clean up chunk files
            self.audio_processor.cleanup_chunks(chunks, audio_path)
            
            # Merge all transcriptions
            if transcriptions:
                logger.info(f"\nMerging {len(transcriptions)} chunk transcriptions...")
                merged_transcript = self._merge_transcriptions(transcriptions)
                return merged_transcript
            else:
                raise TranscriptionError("No chunks were successfully transcribed")
                
        except Exception as e:
            error_msg = f"Error in chunked transcription: {e}"
            logger.failure(error_msg)
            raise TranscriptionError(error_msg) from e
    
    def _create_transcription_prompt(self, chunk_number: int, total_chunks: int) -> str:
        """Create the transcription prompt for Gemini.
        
        Args:
            chunk_number: Current chunk number
            total_chunks: Total number of chunks
            
        Returns:
            Formatted prompt string
        """
        return f"""You are transcribing chunk {chunk_number} of {total_chunks} from a medical audio recording that contains both Mandarin Chinese and Medical English terminology.

CRITICAL INSTRUCTIONS:
1. Transcribe the ENTIRE audio chunk from start to finish without stopping
2. Include ALL content, even if there are pauses or quiet sections
3. Do NOT summarize or skip any portions of the audio
4. Continue transcribing until you reach the absolute end of this audio chunk
5. This is chunk {chunk_number} of {total_chunks} - transcribe ONLY what you hear in this specific chunk

LANGUAGE AND CONTENT:
- The audio contains mixed Mandarin Chinese (Traditional Chinese zh-tw) and English medical terminology
- Speakers may switch between languages mid-sentence
- Medical terms may be spoken in English even within Chinese sentences
- Include all medical terminology, abbreviations, and technical language exactly as spoken

FORMAT:
- Transcribe verbatim what is said
- When speakers switch languages, transcribe in the language being spoken
- Preserve medical terms in their original language (usually English)
- Include speaker changes if distinguishable
- Do NOT add any chunk markers or headers - just transcribe the content

IMPORTANT: This is a complete transcription of chunk {chunk_number}. Transcribe every single word from the beginning to the end of this audio chunk."""
    
    def _merge_transcriptions(self, transcriptions: List[str]) -> str:
        """Merge chunk transcriptions with timestamps.
        
        Args:
            transcriptions: List of transcribed chunks
            
        Returns:
            Merged transcription with timestamps
        """
        merged_transcript = ""
        
        for i, transcript in enumerate(transcriptions, 1):
            # Calculate timestamp for this chunk
            chunk_start_seconds = (i - 1) * self.chunk_duration_seconds
            minutes = chunk_start_seconds // 60
            seconds = chunk_start_seconds % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}:00.000]"
            
            # Add timestamp and transcript
            merged_transcript += f"{timestamp}\n{transcript.strip()}\n\n"
        
        return merged_transcript.strip()