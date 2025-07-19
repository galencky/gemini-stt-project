import time
from pathlib import Path
from typing import List, Optional
import google.generativeai as genai
from .audio_processor import AudioProcessor

class GeminiTranscriber:
    def __init__(self, api_key: str, chunk_duration_seconds: int = 300):
        """Initialize Gemini transcriber with API key."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self.audio_processor = AudioProcessor(chunk_duration_seconds)
        self.chunk_duration_seconds = chunk_duration_seconds
    
    def transcribe_audio_chunk(self, chunk_path: Path, chunk_number: int, total_chunks: int) -> Optional[str]:
        """Transcribe a single audio chunk using Gemini API."""
        try:
            print(f"\n📝 Transcribing chunk {chunk_number}/{total_chunks}...")
            
            # Upload audio file to Gemini
            print(f"Uploading chunk to Gemini...")
            audio_file = genai.upload_file(path=str(chunk_path), display_name=f"chunk_{chunk_number}")
            
            # Wait for file to be processed
            while audio_file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(1)
                audio_file = genai.get_file(audio_file.name)
            print()  # New line after dots
            
            # Prepare the prompt
            prompt = self._create_transcription_prompt(chunk_number, total_chunks)
            
            # Generate transcription
            print(f"Generating transcription for chunk {chunk_number}...")
            response = self.model.generate_content([prompt, audio_file])
            
            # Delete uploaded file
            genai.delete_file(audio_file.name)
            
            if response.text:
                print(f"✅ Successfully transcribed chunk {chunk_number}/{total_chunks}")
                return response.text
            else:
                print(f"❌ No transcription generated for chunk {chunk_number}")
                return None
                
        except Exception as e:
            print(f"❌ Error transcribing chunk {chunk_number}: {e}")
            return None
    
    def transcribe_audio_file(self, audio_path: Path) -> Optional[str]:
        """Transcribe an audio file by splitting it into chunks if necessary."""
        try:
            audio_path = Path(audio_path)
            if not audio_path.exists():
                print(f"❌ Audio file not found: {audio_path}")
                return None
            
            print(f"\n🎵 Processing audio file: {audio_path.name}")
            
            # Get audio info
            audio_info = self.audio_processor.get_audio_info(audio_path)
            if "error" not in audio_info:
                print(f"   Duration: {audio_info['duration_formatted']}")
                print(f"   Format: {audio_info['format']}")
            
            # Split audio into chunks
            chunks = self.audio_processor.split_audio_into_chunks(audio_path)
            
            if not chunks:
                print("❌ No chunks created, cannot proceed with transcription")
                return None
            
            # Transcribe each chunk
            transcriptions = []
            total_chunks = len(chunks)
            
            for i, chunk_path in enumerate(chunks, 1):
                chunk_transcript = self.transcribe_audio_chunk(chunk_path, i, total_chunks)
                
                if chunk_transcript:
                    transcriptions.append(chunk_transcript)
                else:
                    print(f"⚠️  Failed to transcribe chunk {i}/{total_chunks}, continuing...")
            
            # Clean up chunk files
            self.audio_processor.cleanup_chunks(chunks, audio_path)
            
            # Merge all transcriptions
            if transcriptions:
                print(f"\n🔄 Merging {len(transcriptions)} chunk transcriptions...")
                merged_transcript = self._merge_transcriptions(transcriptions)
                print("✅ Transcription complete!")
                return merged_transcript
            else:
                print("❌ No chunks were successfully transcribed")
                return None
                
        except Exception as e:
            print(f"❌ Error in chunked transcription: {e}")
            return None
    
    def _create_transcription_prompt(self, chunk_number: int, total_chunks: int) -> str:
        """Create the transcription prompt for Gemini."""
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
        """Merge chunk transcriptions with timestamps."""
        merged_transcript = []
        
        for i, transcript in enumerate(transcriptions, 1):
            # Calculate timestamp for the start of this chunk
            start_seconds = (i - 1) * self.chunk_duration_seconds
            hours = start_seconds // 3600
            minutes = (start_seconds % 3600) // 60
            seconds = start_seconds % 60
            
            timestamp = f"[{hours:02d}:{minutes:02d}:{seconds:02d}.000]"
            
            # Add timestamp and transcript
            merged_transcript.append(timestamp)
            merged_transcript.append(transcript.strip())
            merged_transcript.append("")  # Empty line between chunks
        
        return "\n".join(merged_transcript).strip()
    
    def batch_transcribe(self, audio_files: List[Path], output_dir: Path) -> dict:
        """Transcribe multiple audio files and save results."""
        results = {
            "successful": [],
            "failed": []
        }
        
        total_files = len(audio_files)
        print(f"\n🎧 Starting batch transcription of {total_files} files...")
        
        for idx, audio_file in enumerate(audio_files, 1):
            print(f"\n{'='*60}")
            print(f"Processing file {idx}/{total_files}: {audio_file.name}")
            print(f"{'='*60}")
            
            # Transcribe the file
            transcript = self.transcribe_audio_file(audio_file)
            
            if transcript:
                # Save transcript
                output_path = output_dir / f"{audio_file.stem}.txt"
                try:
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(transcript)
                    print(f"✅ Saved transcript to: {output_path}")
                    results["successful"].append({
                        "audio_file": audio_file,
                        "transcript_file": output_path
                    })
                except Exception as e:
                    print(f"❌ Error saving transcript: {e}")
                    results["failed"].append({
                        "audio_file": audio_file,
                        "error": str(e)
                    })
            else:
                results["failed"].append({
                    "audio_file": audio_file,
                    "error": "Transcription failed"
                })
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"Batch transcription complete!")
        print(f"✅ Successful: {len(results['successful'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        print(f"{'='*60}")
        
        return results