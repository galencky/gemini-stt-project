#!/usr/bin/env python3
"""
Gemini Speech-to-Text Pipeline
Main entry point for transcribing audio files using Google's Gemini API
"""

import sys
import datetime
import time
from pathlib import Path
from typing import List, Dict

# Import configuration
try:
    from src.utils import config
    config.validate_config()
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print("\n Please check your .env file and ensure all required variables are set.")
    sys.exit(1)

# Import modules
from src.integrations import GoogleDriveClient, HackMDUploader, EmailSender
from src.processors import (
    AudioProcessor, 
    VideoProcessor, 
    GeminiTranscriber, 
    TranscriptParser, 
    Summarizer
)


def log(message: str):
    """Print a timestamped log message."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def process_local_videos() -> List[Path]:
    """Process local video files and extract audio."""
    extracted_audio = []
    
    if not config.PROCESS_VIDEOS or not config.VIDEO_INPUT_DIR:
        return extracted_audio
    
    video_input_path = Path(config.VIDEO_INPUT_DIR)
    if not video_input_path.exists():
        log(f"⚠️  Video input directory not found: {video_input_path}")
        return extracted_audio
    
    log("🎥 Processing local video files...")
    
    # Initialize video processor
    video_processor = VideoProcessor(
        video_extensions=config.VIDEO_EXTENSIONS,
        audio_format=config.VIDEO_AUDIO_FORMAT,
        audio_bitrate=config.VIDEO_AUDIO_BITRATE,
        audio_samplerate=config.VIDEO_AUDIO_SAMPLERATE
    )
    
    # Process videos and extract audio to inbox
    results = video_processor.process_videos(
        video_input_path,
        config.INBOX_DIR,
        move_to_processed=True
    )
    
    extracted_audio = results.get("extracted_audio", [])
    
    if extracted_audio:
        log(f"✅ Extracted audio from {len(extracted_audio)} video files")
    
    return extracted_audio


def download_audio_files(drive_client: GoogleDriveClient) -> List[Path]:
    """Download audio files from Google Drive."""
    log("🔍 Checking Google Drive for new audio files...")
    
    # Download files from the "to be transcribed" folder
    downloaded_files = drive_client.download_folder_contents(
        config.TO_BE_TRANSCRIBED_FOLDER_ID,
        config.INBOX_DIR,
        file_types=list(config.AUDIO_EXTENSIONS)
    )
    
    if downloaded_files:
        log(f"✅ Downloaded {len(downloaded_files)} audio files")
    else:
        log("ℹ️  No new audio files found")
    
    return downloaded_files


def process_audio_files(audio_files: List[Path]) -> Dict:
    """Process audio files through the complete pipeline."""
    start_time = time.time()
    stats = {
        "audio_files": len(audio_files),
        "successful_transcriptions": 0,
        "failed_transcriptions": 0,
        "summaries_generated": 0,
        "hackmd_uploads": 0,
        "errors": []
    }
    
    if not audio_files:
        log("ℹ️  No audio files to process")
        return stats
    
    # Initialize components
    transcriber = GeminiTranscriber(config.GEMINI_API_KEY, config.CHUNK_DURATION_SECONDS)
    parser = TranscriptParser()
    drive_client = GoogleDriveClient(config.GDRIVE_SERVICE_ACCOUNT_JSON)
    
    # Get system prompt from Google Doc
    log("📄 Retrieving system prompt from Google Doc...")
    system_prompt = drive_client.get_document_text(config.SYSTEM_PROMPT_DOC_ID)
    if not system_prompt:
        log("❌ Failed to retrieve system prompt")
        stats["errors"].append({"error": "Failed to retrieve system prompt"})
        return stats
    
    summarizer = Summarizer(config.GEMINI_API_KEY, system_prompt)
    
    # Process each audio file
    log(f"\n🎵 Processing {len(audio_files)} audio files...")
    
    # Step 1: Transcribe audio files
    transcription_results = transcriber.batch_transcribe(audio_files, config.TRANSCRIPTS_DIR)
    stats["successful_transcriptions"] = len(transcription_results["successful"])
    stats["failed_transcriptions"] = len(transcription_results["failed"])
    stats["errors"].extend(transcription_results["failed"])
    
    # Step 2: Parse transcripts
    if transcription_results["successful"]:
        log("\n📝 Parsing transcripts...")
        parse_results = parser.batch_parse_transcripts(config.TRANSCRIPTS_DIR, config.PARSED_DIR)
    
    # Step 3: Generate summaries
    log("\n🤖 Generating summaries...")
    summary_results = summarizer.batch_summarize(config.PARSED_DIR, config.MARKDOWN_DIR)
    stats["summaries_generated"] = len(summary_results["successful"])
    
    # Step 4: Upload to HackMD
    shared_links = []
    if config.HACKMD_TOKEN and summary_results["successful"]:
        log("\n☁️  Uploading to HackMD...")
        uploader = HackMDUploader(config.HACKMD_TOKEN)
        shared_links = uploader.batch_upload_and_move(config.MARKDOWN_DIR, config.UPLOADED_DIR)
        stats["hackmd_uploads"] = len(shared_links)
    
    # Step 5: Upload results back to Google Drive
    log("\n📤 Uploading results to Google Drive...")
    successfully_uploaded, failed_uploads = upload_results_to_drive(drive_client, transcription_results["successful"])
    stats["drive_uploads_successful"] = len(successfully_uploaded)
    stats["drive_uploads_failed"] = len(failed_uploads)
    
    # Step 6: Send email notification
    if config.EMAIL_USER and config.EMAIL_PASS and config.EMAIL_TO and shared_links:
        log("\n📧 Sending email notification...")
        email_sender = EmailSender(config.EMAIL_USER, config.EMAIL_PASS)
        email_sender.send_hackmd_links(config.EMAIL_TO, shared_links)
    
    # Calculate processing time
    processing_time = time.time() - start_time
    stats["processing_time"] = f"{processing_time/60:.1f} minutes"
    
    return stats


def upload_results_to_drive(drive_client: GoogleDriveClient, successful_transcriptions: List[Dict]):
    """Upload transcription results to Google Drive and move processed audio files."""
    successfully_uploaded = []
    failed_uploads = []
    
    for item in successful_transcriptions:
        audio_file = item["audio_file"]
        transcript_file = item["transcript_file"]
        
        # Create a folder for this audio file in the processed folder
        folder_name = audio_file.stem
        folder_id = drive_client.ensure_subfolder(config.PROCESSED_FOLDER_ID, folder_name)
        
        if not folder_id:
            log(f"❌ Failed to create folder for {folder_name}")
            failed_uploads.append(item)
            continue
            
        log(f"📂 Processing folder '{folder_name}' (id {folder_id})")
        
        # Files to upload
        files_to_upload = [
            (transcript_file, f"{audio_file.stem}.txt"),
            (config.PARSED_DIR / f"{audio_file.stem}_parsed.txt", f"{audio_file.stem}_parsed.txt"),
            (config.MARKDOWN_DIR / f"{audio_file.stem}.md", f"{audio_file.stem}.md")
        ]
        
        uploaded_files = []
        upload_failed = False
        
        # Upload each file
        for file_path, expected_name in files_to_upload:
            if file_path.exists():
                file_id = drive_client.upload_file(file_path, folder_id)
                if file_id:
                    uploaded_files.append((file_path, expected_name))
                else:
                    log(f"  ❌ Failed to upload {expected_name}")
                    upload_failed = True
        
        # Verify uploads
        files_in_folder = drive_client.list_files_in_folder(folder_id)
        present_files = {f["name"] for f in files_in_folder}
        expected_files = {name for _, name in uploaded_files}
        
        if expected_files.issubset(present_files) and not upload_failed:
            log("  ✅ All files verified")
            
            # Only move files if upload was successful
            # Find and move the original audio file in Google Drive
            audio_in_drive = drive_client.find_file_by_name(audio_file.name, config.TO_BE_TRANSCRIBED_FOLDER_ID)
            if audio_in_drive:
                if drive_client.move_file(
                    audio_in_drive["id"],
                    config.TRANSCRIBED_FOLDER_ID,
                    config.TO_BE_TRANSCRIBED_FOLDER_ID
                ):
                    log(f"  ↳ Moved {audio_file.name} → transcribed")
            
            # Mark as successfully uploaded
            successfully_uploaded.append({
                'item': item,
                'uploaded_files': uploaded_files
            })
        else:
            missing = expected_files - present_files
            log(f"  ✖ Missing files: {missing}")
            failed_uploads.append(item)
    
    # Clean up only successfully uploaded files if configured to do so
    if successfully_uploaded and config.DELETE_LOCAL_FILES_AFTER_UPLOAD:
        log(f"\n🧹 Cleaning up {len(successfully_uploaded)} successfully uploaded file sets...")
        for upload_info in successfully_uploaded:
            for file_path, _ in upload_info['uploaded_files']:
                try:
                    if file_path.exists():
                        file_path.unlink()
                        log(f"  ✅ Deleted local file: {file_path.name}")
                except Exception as e:
                    log(f"  ⚠️  Could not delete {file_path.name}: {e}")
    elif successfully_uploaded:
        log(f"\n📁 Keeping local files (DELETE_LOCAL_FILES_AFTER_UPLOAD=false)")
    
    if failed_uploads:
        log(f"\n⚠️  {len(failed_uploads)} items failed to upload and were kept locally")
        
    return successfully_uploaded, failed_uploads


def main():
    """Main entry point."""
    log("🚀 Starting Gemini Speech-to-Text Pipeline")
    
    try:
        # Initialize Google Drive client
        drive_client = GoogleDriveClient(config.GDRIVE_SERVICE_ACCOUNT_JSON)
        
        # Process local videos first (if enabled)
        extracted_audio = process_local_videos()
        
        # Download audio files from Google Drive
        downloaded_audio = download_audio_files(drive_client)
        
        # Combine all audio files
        all_audio_files = extracted_audio + downloaded_audio
        
        # Also check for any existing audio files in inbox
        existing_audio = []
        for ext in config.AUDIO_EXTENSIONS:
            existing_audio.extend(config.INBOX_DIR.glob(f"*{ext}"))
        
        # Remove duplicates
        all_audio_files = list(set(all_audio_files + existing_audio))
        
        # Process audio files
        stats = process_audio_files(all_audio_files)
        
        # Print final summary
        log("\n" + "="*60)
        log("✅ Pipeline completed successfully!")
        log(f"   Audio files processed: {stats['audio_files']}")
        log(f"   Successful transcriptions: {stats['successful_transcriptions']}")
        log(f"   Failed transcriptions: {stats['failed_transcriptions']}")
        log(f"   Summaries generated: {stats['summaries_generated']}")
        log(f"   HackMD uploads: {stats['hackmd_uploads']}")
        if stats.get('processing_time'):
            log(f"   Processing time: {stats['processing_time']}")
        log("="*60)
        
    except KeyboardInterrupt:
        log("\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()