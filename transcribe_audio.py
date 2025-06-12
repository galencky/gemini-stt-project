import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from google import genai
from dotenv import load_dotenv
import math

# Import configuration
try:
    from config import *
except ImportError:
    # Default values if config.py doesn't exist
    CHUNK_DURATION_SECONDS = 300
    MAX_FILE_SIZE_MB = 20
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_CHANNELS = 1

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Please set GOOGLE_API_KEY in your .env file")

client = genai.Client(api_key=GOOGLE_API_KEY)

INBOX_DIR = Path('inbox')
TRANSCRIBED_DIR = Path('transcribed')
TRANSCRIPTION_DIR = Path('transcripts')

SUPPORTED_FORMATS = {'.wav', '.mp3', '.aiff', '.aac', '.ogg', '.flac', '.m4a'}

def get_file_size_mb(file_path):
    """Get file size in MB."""
    return file_path.stat().st_size / (1024 * 1024)

def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe."""
    try:
        cmd = [
            'ffprobe',
            '-i', str(audio_path),
            '-show_entries', 'format=duration',
            '-v', 'quiet',
            '-of', 'csv=p=0'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting audio duration: {e}")
    return None

def split_audio_into_chunks(audio_path, chunk_duration=CHUNK_DURATION_SECONDS):
    """Split audio file into chunks of specified duration."""
    chunks = []
    try:
        # Get total duration
        total_duration = get_audio_duration(audio_path)
        if not total_duration:
            print("Could not determine audio duration, processing as single file")
            return [audio_path]
        
        print(f"Total audio duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        
        # Calculate number of chunks
        num_chunks = math.ceil(total_duration / chunk_duration)
        
        if num_chunks == 1:
            print("Audio is shorter than chunk duration, processing as single file")
            return [audio_path]
        
        print(f"Splitting audio into {num_chunks} chunks of {chunk_duration} seconds each...")
        
        # Create temporary directory for chunks
        temp_dir = Path(tempfile.mkdtemp())
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = temp_dir / f"chunk_{i+1:03d}.wav"
            
            # FFmpeg command to extract chunk
            cmd = [
                'ffmpeg',
                '-i', str(audio_path),
                '-ss', str(start_time),  # Start time
                '-t', str(chunk_duration),  # Duration
                '-acodec', 'pcm_s16le',  # Uncompressed audio
                '-ar', str(AUDIO_SAMPLE_RATE),  # Sample rate from config
                '-ac', str(AUDIO_CHANNELS),  # Channels from config
                '-y',  # Overwrite
                str(chunk_path)
            ]
            
            print(f"Creating chunk {i+1}/{num_chunks} (start: {start_time}s)...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and chunk_path.exists():
                chunks.append(chunk_path)
            else:
                print(f"Error creating chunk {i+1}: {result.stderr}")
        
        print(f"Successfully created {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        print(f"Error splitting audio: {e}")
        return [audio_path]

def transcribe_audio_chunk(chunk_path, chunk_number, total_chunks):
    """Transcribe a single audio chunk using Gemini API."""
    try:
        file_size_mb = get_file_size_mb(chunk_path)
        print(f"Chunk {chunk_number}/{total_chunks} - Size: {file_size_mb:.2f} MB")
        
        print(f"Uploading chunk {chunk_number}...")
        uploaded_file = client.files.upload(file=str(chunk_path))
        
        print(f"Transcribing chunk {chunk_number}/{total_chunks}...")
        
        # Modified prompt to indicate this is a chunk
        prompt = f'''You are transcribing chunk {chunk_number} of {total_chunks} from a medical audio recording that contains both Mandarin Chinese and Medical English terminology.

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

IMPORTANT: This is a complete transcription of chunk {chunk_number}. Transcribe every single word from the beginning to the end of this audio chunk.'''
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt, uploaded_file]
        )
        
        return response.text
    except Exception as e:
        print(f"Error transcribing chunk {chunk_number}: {e}")
        return None

def transcribe_audio_file(audio_path):
    """Transcribe an audio file by splitting it into chunks."""
    try:
        # Split audio into chunks
        chunks = split_audio_into_chunks(audio_path)
        
        if not chunks:
            print("No chunks created, cannot proceed with transcription")
            return None
        
        # Transcribe each chunk
        transcriptions = []
        total_chunks = len(chunks)
        
        for i, chunk_path in enumerate(chunks, 1):
            print(f"\n--- Processing chunk {i}/{total_chunks} ---")
            chunk_transcript = transcribe_audio_chunk(chunk_path, i, total_chunks)
            
            if chunk_transcript:
                transcriptions.append(chunk_transcript)
                print(f"Successfully transcribed chunk {i}/{total_chunks}")
            else:
                print(f"Failed to transcribe chunk {i}/{total_chunks}")
                # Continue with other chunks even if one fails
        
        # Clean up chunk files if they were created
        if len(chunks) > 1:  # Only clean up if we created temporary chunks
            temp_dir = chunks[0].parent
            for chunk in chunks:
                if chunk.exists():
                    chunk.unlink()
            if temp_dir.exists() and temp_dir != audio_path.parent:
                temp_dir.rmdir()
        
        # Merge all transcriptions
        if transcriptions:
            print(f"\nMerging {len(transcriptions)} chunk transcriptions...")
            
            # Add a header indicating this was processed in chunks
            header = f"[Audio transcribed in {len(transcriptions)} chunks of {CHUNK_DURATION_SECONDS} seconds each]\n\n"
            
            # Join chunks with clear separators
            merged_transcript = header
            for i, transcript in enumerate(transcriptions, 1):
                if i > 1:
                    merged_transcript += f"\n\n--- Chunk {i}/{len(transcriptions)} ---\n\n"
                merged_transcript += transcript.strip()
            
            return merged_transcript
        else:
            print("No chunks were successfully transcribed")
            return None
            
    except Exception as e:
        print(f"Error in chunked transcription: {e}")
        return None

def process_audio_files():
    """Process all audio files in the inbox directory."""
    if not INBOX_DIR.exists():
        print(f"Error: {INBOX_DIR} directory does not exist")
        return
    
    audio_files = []
    for ext in SUPPORTED_FORMATS:
        audio_files.extend(INBOX_DIR.glob(f'*{ext}'))
    
    if not audio_files:
        print("No audio files found in the inbox directory")
        return
    
    print(f"Found {len(audio_files)} audio file(s) to process")
    
    for audio_file in audio_files:
        print(f"\n{'='*60}")
        print(f"Processing: {audio_file.name}")
        print(f"{'='*60}")
        
        transcript = transcribe_audio_file(audio_file)
        
        if transcript:
            transcript_filename = audio_file.stem + '.txt'
            transcript_path = TRANSCRIPTION_DIR / transcript_filename
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
            print(f"\nSaved transcript to: {transcript_path}")
            
            destination = TRANSCRIBED_DIR / audio_file.name
            shutil.move(str(audio_file), str(destination))
            print(f"Moved audio file to: {destination}")
        else:
            print(f"\nFailed to transcribe {audio_file.name}, leaving in inbox")

if __name__ == "__main__":
    INBOX_DIR.mkdir(exist_ok=True)
    TRANSCRIBED_DIR.mkdir(exist_ok=True)
    TRANSCRIPTION_DIR.mkdir(exist_ok=True)
    
    # Check if ffmpeg and ffprobe are available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg and ffprobe must be installed to use this script")
        print("Please install ffmpeg: https://ffmpeg.org/download.html")
        exit(1)
    
    process_audio_files()