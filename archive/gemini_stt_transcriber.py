#!/usr/bin/env python3
"""
Gemini Speech-to-Text Transcriber
Transcribes audio files using Google's Gemini API with automatic chunking for long recordings.
Processes medical audio with mixed Mandarin Chinese and English content.
"""

import os
import json
import shutil
import datetime
import time
import math
import tempfile
import smtplib
import requests
import io
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Google API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import google.generativeai as genai

# Audio processing
from pydub import AudioSegment
from tqdm import tqdm

# Import video processor
from video_processor import VideoProcessor

# Load environment variables
load_dotenv()

# Configuration from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GDRIVE_SERVICE_ACCOUNT_JSON = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON")
TO_BE_TRANSCRIBED_FOLDER_ID = os.getenv("TO_BE_TRANSCRIBED_FOLDER_ID")
TRANSCRIBED_FOLDER_ID = os.getenv("TRANSCRIBED_FOLDER_ID")
PROCESSED_FOLDER_ID = os.getenv("PROCESSED_FOLDER_ID")
SYSTEM_PROMPT_DOC_ID = os.getenv("SYSTEM_PROMPT_DOC_ID", "1p44XUpBu7lPjyux4eANd_9FHT5F1UDbgUyx7q6Libvk")
HACKMD_TOKEN = os.getenv("HACKMD_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")
CHUNK_DURATION_SECONDS = int(os.getenv("CHUNK_DURATION_SECONDS", "300"))

# Local directory configuration
PROCESS_LOCAL_AUDIO = os.getenv("PROCESS_LOCAL_AUDIO", "false").lower() == "true"
AUDIO_INPUT_DIR = os.getenv("AUDIO_INPUT_DIR", "")
VIDEO_INPUT_DIR = os.getenv("VIDEO_INPUT_DIR", "")
PROCESS_VIDEOS = os.getenv("PROCESS_VIDEOS", "false").lower() == "true"
VIDEO_AUDIO_FORMAT = os.getenv("VIDEO_AUDIO_FORMAT", "m4a")
VIDEO_AUDIO_BITRATE = os.getenv("VIDEO_AUDIO_BITRATE", "192k")
VIDEO_AUDIO_SAMPLERATE = int(os.getenv("VIDEO_AUDIO_SAMPLERATE", "44100"))

# Working directories
WORKING_DIR = Path("./working")
INBOX_DIR = WORKING_DIR / "from_google_drive"
TRANSCRIPTS_DIR = WORKING_DIR / "transcription"
PARSED_DIR = WORKING_DIR / "parsed"
MARKDOWN_DIR = WORKING_DIR / "markdown"
UPLOADED_DIR = WORKING_DIR / "uploaded"

# Audio file extensions
AUDIO_EXT = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}

# Google Drive scopes
SCOPES = ["https://www.googleapis.com/auth/drive"]


def log(msg: str):
    """Print timestamped log message."""
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}")


def setup_directories():
    """Create all necessary working directories."""
    for dir_path in [WORKING_DIR, INBOX_DIR, TRANSCRIPTS_DIR, PARSED_DIR, MARKDOWN_DIR, UPLOADED_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def setup_google_services():
    """Set up Google Drive and Docs services."""
    if not GDRIVE_SERVICE_ACCOUNT_JSON:
        raise ValueError("GDRIVE_SERVICE_ACCOUNT_JSON not found in environment!")
    
    # Parse the JSON string from environment
    sa_data = json.loads(GDRIVE_SERVICE_ACCOUNT_JSON)
    
    # Create credentials from parsed data
    creds = service_account.Credentials.from_service_account_info(sa_data, scopes=SCOPES)
    
    drive_service = build("drive", "v3", credentials=creds)
    docs_service = build("docs", "v1", credentials=creds)
    
    return drive_service, docs_service, creds


def setup_gemini():
    """Configure Gemini API."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment!")
    
    genai.configure(api_key=GEMINI_API_KEY)


def list_files_in_folder(drive_service, folder_id: str) -> List[Dict]:
    """List all files in a Google Drive folder."""
    query = f"'{folder_id}' in parents and trashed=false"
    files = []
    page_token = None
    
    while True:
        resp = drive_service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name)",
            pageToken=page_token
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken", None)
        if not page_token:
            break
    
    return files


def download_files_from_drive(drive_service, folder_id: str, dest_dir: Path) -> List[Path]:
    """Download all files from a Google Drive folder."""
    downloaded_files = []
    
    # List non-folder files
    query = (
        f"'{folder_id}' in parents and "
        "trashed = false and "
        "mimeType != 'application/vnd.google-apps.folder'"
    )
    
    response = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)"
    ).execute()
    
    files = response.get("files", [])
    
    if not files:
        log(f"No files found in folder ID = {folder_id}")
        return downloaded_files
    
    log(f"Found {len(files)} file(s) to download")
    
    for file_data in files:
        file_id = file_data["id"]
        file_name = file_data["name"]
        dest_path = dest_dir / file_name
        
        try:
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.FileIO(str(dest_path), mode="wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            
            log(f"Downloading {file_name}...")
            while not done:
                status, done = downloader.next_chunk()
            
            fh.close()
            downloaded_files.append(dest_path)
            log(f"✅ Saved to {dest_path}")
            
        except Exception as e:
            log(f"❌ Error downloading {file_name}: {e}")
    
    return downloaded_files


def get_audio_duration(audio_path: Path) -> Optional[float]:
    """Get audio duration in seconds using pydub."""
    try:
        audio = AudioSegment.from_file(str(audio_path))
        return len(audio) / 1000.0  # Convert milliseconds to seconds
    except Exception as e:
        log(f"Error getting audio duration: {e}")
        return None


def split_audio_into_chunks(audio_path: Path, chunk_duration_seconds: int = 300) -> List[Path]:
    """Split audio file into chunks of specified duration."""
    chunks = []
    
    try:
        # Load audio
        audio = AudioSegment.from_file(str(audio_path))
        total_duration = len(audio) / 1000.0  # Convert to seconds
        
        log(f"Total audio duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        
        # Calculate number of chunks
        num_chunks = math.ceil(total_duration / chunk_duration_seconds)
        
        if num_chunks == 1:
            log("Audio is shorter than chunk duration, processing as single file")
            return [audio_path]
        
        log(f"Splitting audio into {num_chunks} chunks of {chunk_duration_seconds} seconds each...")
        
        # Create temporary directory for chunks
        temp_dir = Path(tempfile.mkdtemp())
        chunk_duration_ms = chunk_duration_seconds * 1000
        
        for i in range(num_chunks):
            start_ms = i * chunk_duration_ms
            end_ms = min((i + 1) * chunk_duration_ms, len(audio))
            
            # Extract chunk
            chunk = audio[start_ms:end_ms]
            
            # Save chunk
            chunk_path = temp_dir / f"chunk_{i+1:03d}.wav"
            chunk.export(chunk_path, format="wav")
            
            log(f"Created chunk {i+1}/{num_chunks} (duration: {(end_ms-start_ms)/1000:.1f}s)")
            chunks.append(chunk_path)
        
        log(f"Successfully created {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        log(f"Error splitting audio: {e}")
        return [audio_path]


def transcribe_audio_chunk(chunk_path: Path, chunk_number: int, total_chunks: int) -> Optional[str]:
    """Transcribe a single audio chunk using Gemini API."""
    try:
        log(f"Transcribing chunk {chunk_number}/{total_chunks}...")
        
        # Upload audio file to Gemini
        audio_file = genai.upload_file(path=str(chunk_path), display_name=f"chunk_{chunk_number}")
        
        # Wait for file to be processed
        while audio_file.state.name == "PROCESSING":
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)
        
        # Prepare the prompt
        prompt = f"""You are transcribing chunk {chunk_number} of {total_chunks} from a medical audio recording that contains both Mandarin Chinese and Medical English terminology.

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
        
        # Generate transcription
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([prompt, audio_file])
        
        # Delete uploaded file
        genai.delete_file(audio_file.name)
        
        return response.text
        
    except Exception as e:
        log(f"Error transcribing chunk {chunk_number}: {e}")
        return None


def transcribe_audio_file(audio_path: Path, chunk_duration_seconds: int = 300) -> Optional[str]:
    """Transcribe an audio file by splitting it into chunks."""
    try:
        # Split audio into chunks
        chunks = split_audio_into_chunks(audio_path, chunk_duration_seconds)
        
        if not chunks:
            log("No chunks created, cannot proceed with transcription")
            return None
        
        # Transcribe each chunk
        transcriptions = []
        total_chunks = len(chunks)
        
        for i, chunk_path in enumerate(chunks, 1):
            log(f"\n--- Processing chunk {i}/{total_chunks} ---")
            chunk_transcript = transcribe_audio_chunk(chunk_path, i, total_chunks)
            
            if chunk_transcript:
                transcriptions.append(chunk_transcript)
                log(f"Successfully transcribed chunk {i}/{total_chunks}")
            else:
                log(f"Failed to transcribe chunk {i}/{total_chunks}")
        
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
            log(f"\nMerging {len(transcriptions)} chunk transcriptions...")
            
            # Join chunks with timestamps
            merged_transcript = ""
            for i, transcript in enumerate(transcriptions, 1):
                timestamp = f"[{(i-1)*chunk_duration_seconds//60:02d}:{(i-1)*chunk_duration_seconds%60:02d}:00.000]"
                merged_transcript += f"{timestamp}\n{transcript.strip()}\n\n"
            
            return merged_transcript.strip()
        else:
            log("No chunks were successfully transcribed")
            return None
            
    except Exception as e:
        log(f"Error in chunked transcription: {e}")
        return None


def parse_transcript_simple(text: str) -> str:
    """Parse transcript into 5-minute blocks with preserved formatting."""
    lines = text.strip().split('\n')
    
    result = []
    current_block = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            # This is a timestamp line
            if current_block:
                result.append('\n'.join(current_block))
                result.append('')  # blank line
                current_block = []
            result.append(line)
        elif line:
            current_block.append(line)
    
    if current_block:
        result.append('\n'.join(current_block))
    
    return '\n'.join(result)


def get_doc_text(doc_id: str, docs_service) -> str:
    """Retrieve text content from a Google Doc."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    text = []
    
    for element in doc.get('body', {}).get('content', []):
        if 'paragraph' in element:
            for run in element['paragraph'].get('elements', []):
                txt = run.get('textRun', {}).get('content')
                if txt:
                    text.append(txt)
    
    return ''.join(text).strip()


def generate_summary_with_gemini(speech_text: str, system_prompt: str) -> Optional[str]:
    """Generate summary using Gemini API."""
    model = genai.GenerativeModel("gemini-2.0-flash")
    full_prompt = system_prompt.strip() + "\n\n" + speech_text.strip()
    
    try:
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.5),
            stream=False,
        )
        return response.text
    except Exception as e:
        log(f"Gemini API error: {e}")
        return None


def upload_to_hackmd(md_content: str, filename: str, api_token: str) -> Optional[Dict]:
    """Upload markdown content to HackMD."""
    # Derive a clean title from the filename
    if filename.endswith('.md'):
        filename = filename[:-3]
    raw_title = filename.replace('_parsed', '').strip()
    title = raw_title.replace('_', ' ').strip()

    # Ensure there's a top-level heading
    md_lines = md_content.lstrip().splitlines()
    if not md_lines or not md_lines[0].strip().startswith("# "):
        md_content = f"# {title}\n\n" + md_content.lstrip()
    else:
        md_lines[0] = f"# {title}"
        md_content = "\n".join(md_lines)

    # Append hashtag
    hashtag = "#gemini-stt-project"
    content_lines = md_content.rstrip().splitlines()
    if not any(line.strip() == hashtag for line in content_lines[-3:]):
        md_content = md_content.rstrip() + "\n\n" + hashtag + "\n"

    url = "https://api.hackmd.io/v1/notes"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    data = {
        "title": title,
        "content": md_content,
        "readPermission": "guest",
        "writePermission": "signed_in"
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.ok:
        note_id = response.json().get("id")
        shared_url = f"https://hackmd.io/{note_id}"
        log(f"Uploaded to HackMD: {shared_url}")
        return {"title": title, "url": shared_url}
    else:
        log(f"HackMD upload failed for {filename}: {response.status_code} {response.text}")
        return None


def ensure_subfolder(drive_service, parent_id: str, name: str) -> str:
    """Return id of subfolder 'name' under parent, creating if absent."""
    q = (f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' "
         f"and name='{name}' and trashed=false")
    res = drive_service.files().list(
        q=q,
        spaces="drive",
        fields="files(id)",
        supportsAllDrives=True
    ).execute()
    
    if res["files"]:
        return res["files"][0]["id"]
    
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    return drive_service.files().create(
        body=meta,
        fields="id",
        supportsAllDrives=True
    ).execute()["id"]


def upload_file_to_drive(drive_service, local_path: Path, parent_id: str):
    """Upload a file to Google Drive."""
    media = MediaFileUpload(str(local_path), resumable=False)
    meta = {"name": local_path.name, "parents": [parent_id]}
    drive_service.files().create(
        body=meta,
        media_body=media,
        fields="id",
        supportsAllDrives=True
    ).execute()
    log(f"Uploaded {local_path.name} to Google Drive")


def move_audio_in_drive(drive_service, audio_name: str, from_folder_id: str, to_folder_id: str):
    """Move audio file from one folder to another in Google Drive."""
    q = f"'{from_folder_id}' in parents and name='{audio_name}' and trashed=false"
    res = drive_service.files().list(
        q=q,
        spaces="drive",
        fields="files(id)",
        supportsAllDrives=True
    ).execute().get("files", [])
    
    if not res:
        return
    
    fid = res[0]["id"]
    drive_service.files().update(
        fileId=fid,
        addParents=to_folder_id,
        removeParents=from_folder_id,
        fields="id",
        supportsAllDrives=True
    ).execute()
    log(f"Moved {audio_name} to transcribed folder")


def send_email_notification(shared_links: List[Dict]):
    """Send email notification with HackMD links."""
    if not all([EMAIL_USER, EMAIL_PASS, EMAIL_TO]):
        log("Email configuration missing - skipping email notification")
        return
    
    if not shared_links:
        log("No links to send - skipping email")
        return
    
    # Build email body
    subject = "📝 Your Uploaded HackMD Speech Summaries (Gemini STT)"
    body_lines = [
        "Hello,",
        "",
        "Your audio files were transcribed using Gemini STT with chunking",
        "and summarized using Gemini 2.0 Flash. The summaries are now",
        "available on HackMD:",
        ""
    ] + [f"- {link['title']}: {link['url']}" for link in shared_links] + [
        "",
        "If you have questions just reply to this email.",
        "",
        "Best regards,",
        "Gemini-STT Bot"
    ]
    body = "\n".join(body_lines)
    
    # Compose & send
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = Header(subject, "utf-8")
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        log("Email sent successfully")
    except Exception as e:
        log(f"Email send failed: {e}")


def process_video_files() -> List[Path]:
    """Process video files and extract audio."""
    extracted_audio_files = []
    
    if PROCESS_VIDEOS and VIDEO_INPUT_DIR:
        video_dir = Path(VIDEO_INPUT_DIR)
        audio_output_dir = Path(AUDIO_INPUT_DIR) if AUDIO_INPUT_DIR else video_dir / "audio_only"
        
        if video_dir.exists():
            log(f"Checking for video files in {video_dir}")
            
            # Initialize video processor
            processor = VideoProcessor(
                audio_format=VIDEO_AUDIO_FORMAT,
                audio_bitrate=VIDEO_AUDIO_BITRATE,
                audio_samplerate=VIDEO_AUDIO_SAMPLERATE
            )
            
            # Process videos
            results = processor.process_videos(
                input_dir=video_dir,
                output_dir=audio_output_dir,
                move_to_processed=True
            )
            
            # Copy extracted audio files to inbox
            for audio_file in results["extracted_audio"]:
                dest = INBOX_DIR / audio_file.name
                shutil.copy2(audio_file, dest)
                extracted_audio_files.append(dest)
                log(f"Copied extracted audio {audio_file.name} to inbox")
    
    return extracted_audio_files


def process_local_audio_files() -> List[Path]:
    """Process audio files from local directory if configured."""
    local_audio_files = []
    
    if PROCESS_LOCAL_AUDIO and AUDIO_INPUT_DIR:
        audio_dir = Path(AUDIO_INPUT_DIR)
        if audio_dir.exists():
            log(f"Processing local audio files from {audio_dir}")
            
            # Find all audio files
            for ext in AUDIO_EXT:
                local_audio_files.extend(audio_dir.glob(f"*{ext}"))
            
            # Copy to inbox directory
            for audio_file in local_audio_files:
                dest = INBOX_DIR / audio_file.name
                shutil.copy2(audio_file, dest)
                log(f"Copied {audio_file.name} to inbox")
    
    return local_audio_files


def main():
    """Main execution flow."""
    try:
        # Setup
        log("Starting Gemini STT Transcriber")
        setup_directories()
        setup_gemini()
        
        # Set up Google services
        drive_service, docs_service, creds = setup_google_services()
        
        # PRIORITIZE LOCAL PROCESSING
        local_files_processed = False
        
        # Step 1: Process video files first (if any)
        video_audio_files = process_video_files()
        if video_audio_files:
            log(f"Extracted audio from {len(video_audio_files)} video file(s)")
            local_files_processed = True
        
        # Step 2: Process existing local audio files
        local_audio_files = process_local_audio_files()
        if local_audio_files:
            log(f"Found {len(local_audio_files)} local audio file(s)")
            local_files_processed = True
        
        # Step 3: Only check Google Drive if no local files were found
        if not local_files_processed:
            log("No local files found, checking Google Drive...")
            
            # Check for files in Google Drive
            files_in_drive = list_files_in_folder(drive_service, TO_BE_TRANSCRIBED_FOLDER_ID)
            
            # Download files from Google Drive
            if files_in_drive:
                log(f"Found {len(files_in_drive)} file(s) in Google Drive")
                download_files_from_drive(drive_service, TO_BE_TRANSCRIBED_FOLDER_ID, INBOX_DIR)
            else:
                log("No files found in Google Drive folder")
        else:
            log("Processing local files - skipping Google Drive download")
        
        # Gather all audio files
        audio_files = [p for p in INBOX_DIR.rglob("*") if p.suffix.lower() in AUDIO_EXT]
        
        if not audio_files:
            log("No audio files to process")
            return
        
        log(f"Found {len(audio_files)} audio file(s) to process")
        
        # Transcription process
        with tqdm(audio_files, desc="Transcribing files", unit="file") as pbar:
            for audio in pbar:
                pbar.set_description(f"Transcribing: {audio.name}")
                
                # Transcribe using Gemini with chunking
                transcript = transcribe_audio_file(audio, CHUNK_DURATION_SECONDS)
                
                if transcript:
                    # Save transcript
                    out_txt = TRANSCRIPTS_DIR / f"{audio.stem}.txt"
                    with open(out_txt, "w", encoding="utf-8") as f:
                        f.write(transcript)
                    log(f"Saved transcript to: {out_txt}")
                else:
                    log(f"Failed to transcribe {audio.name}")
        
        # Parse transcripts
        txt_files = list(TRANSCRIPTS_DIR.glob("*.txt"))
        if txt_files:
            log("Parsing transcripts...")
            for txtfile in txt_files:
                with txtfile.open(encoding="utf-8") as f:
                    text = f.read()
                
                processed = parse_transcript_simple(text)
                out_path = PARSED_DIR / txtfile.name.replace(".txt", "_parsed.txt")
                
                with out_path.open("w", encoding="utf-8") as f:
                    f.write(processed)
                log(f"Processed {txtfile.name} → {out_path.name}")
        
        # Get system prompt from Google Doc
        system_prompt = get_doc_text(SYSTEM_PROMPT_DOC_ID, docs_service)
        log("System prompt loaded from Google Doc")
        
        # Generate summaries
        parsed_files = list(PARSED_DIR.glob("*.txt"))
        if parsed_files:
            log("Generating summaries...")
            for txt_path in parsed_files:
                with open(txt_path, "r", encoding="utf-8") as f:
                    speech_text = f.read().strip()
                
                if not speech_text:
                    continue
                
                summary_md = generate_summary_with_gemini(speech_text, system_prompt)
                if summary_md:
                    md_path = MARKDOWN_DIR / (txt_path.stem.replace("_parsed", "") + ".md")
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(summary_md)
                    log(f"Saved summary → {md_path.name}")
        
        # Upload to HackMD
        shared_links = []
        if HACKMD_TOKEN:
            md_files = list(MARKDOWN_DIR.glob("*.md"))
            if md_files:
                log("Uploading to HackMD...")
                for md_file in md_files:
                    with open(md_file, "r", encoding="utf-8") as f:
                        md_content = f.read()
                    
                    result = upload_to_hackmd(md_content, md_file.name, HACKMD_TOKEN)
                    if result:
                        shared_links.append(result)
                        # Move to uploaded directory
                        dest_file = UPLOADED_DIR / md_file.name
                        shutil.move(str(md_file), dest_file)
        
        # Upload processed files to Google Drive only if we downloaded from Drive
        if not local_files_processed:
            md_files = list(UPLOADED_DIR.glob("*.md"))
            if md_files:
                log("Syncing processed files to Google Drive...")
                for md in md_files:
                    stem = md.stem
                    folder_id = ensure_subfolder(drive_service, PROCESSED_FOLDER_ID, stem)
                    
                    # Upload related files
                    txt_path = TRANSCRIPTS_DIR / f"{stem}.txt"
                    parsed_path = PARSED_DIR / f"{stem}_parsed.txt"
                    
                    for p in (txt_path, parsed_path, md):
                        if p.exists():
                            upload_file_to_drive(drive_service, p, folder_id)
                    
                    # Move corresponding audio from Google Drive
                    for audio_local in INBOX_DIR.glob(f"{stem}.*"):
                        if audio_local.is_file():
                            move_audio_in_drive(drive_service, audio_local.name, 
                                              TO_BE_TRANSCRIBED_FOLDER_ID, TRANSCRIBED_FOLDER_ID)
                            break
        
        # Send email notification
        if shared_links:
            send_email_notification(shared_links)
        
        log("Processing complete!")
        
    except Exception as e:
        log(f"Error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()