#!/usr/bin/env python3
"""
Gemini Speech-to-Text Pipeline V2
Smart pipeline that tracks state and skips completed steps
"""

import sys
import argparse
import datetime
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Import configuration
try:
    from src.utils import config, PipelineStateManager, PipelineStage
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


class SmartPipeline:
    """Smart pipeline that tracks state and can resume from any stage."""
    
    def __init__(self, resume: bool = False, force_reprocess: List[str] = None):
        self.state_manager = PipelineStateManager(config.DATA_DIR / "pipeline_state.json")
        self.resume = resume
        self.force_reprocess = force_reprocess or []
        self.stats = {
            "total_files": 0,
            "skipped_stages": 0,
            "processed_stages": 0,
            "errors": []
        }
        
        # Initialize components lazily
        self._drive_client = None
        self._transcriber = None
        self._parser = None
        self._summarizer = None
        self._uploader = None
        self._email_sender = None
    
    @property
    def drive_client(self):
        if not self._drive_client:
            self._drive_client = GoogleDriveClient(config.GDRIVE_SERVICE_ACCOUNT_JSON)
        return self._drive_client
    
    @property
    def transcriber(self):
        if not self._transcriber:
            self._transcriber = GeminiTranscriber(config.GEMINI_API_KEY, config.CHUNK_DURATION_SECONDS)
        return self._transcriber
    
    def analyze_pipeline(self) -> Dict[str, List[str]]:
        """Analyze current state and determine what needs to be processed."""
        log("\n🔍 Analyzing pipeline state...")
        
        # Clean up references to missing files
        self.state_manager.clean_missing_artifacts()
        
        # Get all audio files
        all_audio_files = self._gather_all_audio_files()
        self.stats["total_files"] = len(all_audio_files)
        
        # Categorize files by what stages they need
        needs_processing = {
            "transcription": [],
            "parsing": [],
            "summarization": [],
            "hackmd_upload": [],
            "drive_upload": []
        }
        
        for audio_file in all_audio_files:
            filename = audio_file.stem
            state = self.state_manager.get_or_create_file_state(filename, audio_file)
            
            # Check what stages are needed
            if not self._check_stage_complete(filename, PipelineStage.TRANSCRIBED):
                needs_processing["transcription"].append(audio_file)
            elif not self._check_stage_complete(filename, PipelineStage.PARSED):
                needs_processing["parsing"].append(audio_file)
            elif not self._check_stage_complete(filename, PipelineStage.SUMMARIZED):
                needs_processing["summarization"].append(audio_file)
            elif config.HACKMD_TOKEN and not self._check_stage_complete(filename, PipelineStage.HACKMD_UPLOADED):
                needs_processing["hackmd_upload"].append(audio_file)
            elif not self._check_stage_complete(filename, PipelineStage.DRIVE_UPLOADED):
                needs_processing["drive_upload"].append(audio_file)
        
        # Print analysis
        log("\n📊 Pipeline Analysis Report:")
        log(f"   Total files: {len(all_audio_files)}")
        for stage, files in needs_processing.items():
            if files:
                log(f"   Need {stage}: {len(files)} files")
        
        # Count already completed
        completed = len([f for f in all_audio_files if self._check_stage_complete(
            f.stem, PipelineStage.COMPLETED)])
        if completed:
            log(f"   Fully completed: {completed} files")
        
        return needs_processing
    
    def _check_stage_complete(self, filename: str, stage: PipelineStage) -> bool:
        """Check if a stage is complete, considering force reprocess flags."""
        if filename in self.force_reprocess:
            return False
        
        if not self.resume:
            return False
            
        # Check if stage is marked complete and artifacts exist
        if stage == PipelineStage.TRANSCRIBED:
            return self.state_manager.check_artifacts_exist(filename, [stage])
        elif stage == PipelineStage.PARSED:
            return self.state_manager.check_artifacts_exist(filename, [stage])
        elif stage == PipelineStage.SUMMARIZED:
            return self.state_manager.check_artifacts_exist(filename, [stage])
        else:
            return self.state_manager.is_stage_complete(filename, stage)
    
    def _gather_all_audio_files(self) -> List[Path]:
        """Gather all audio files from various sources."""
        all_files = []
        
        # 1. Process local videos if enabled
        if config.PROCESS_VIDEOS and config.VIDEO_INPUT_DIR:
            extracted = self._process_local_videos()
            all_files.extend(extracted)
        
        # 2. Download from Google Drive
        downloaded = self._download_audio_files()
        all_files.extend(downloaded)
        
        # 3. Check existing files in inbox
        for ext in config.AUDIO_EXTENSIONS:
            all_files.extend(config.INBOX_DIR.glob(f"*{ext}"))
        
        # Remove duplicates
        return list(set(all_files))
    
    def _process_local_videos(self) -> List[Path]:
        """Process local video files and extract audio."""
        video_input_path = Path(config.VIDEO_INPUT_DIR)
        if not video_input_path.exists():
            log(f"⚠️  Video input directory not found: {video_input_path}")
            return []
        
        log("🎥 Checking for video files to process...")
        
        # Initialize video processor
        video_processor = VideoProcessor(
            video_extensions=config.VIDEO_EXTENSIONS,
            audio_format=config.VIDEO_AUDIO_FORMAT,
            audio_bitrate=config.VIDEO_AUDIO_BITRATE,
            audio_samplerate=config.VIDEO_AUDIO_SAMPLERATE
        )
        
        # Find videos
        video_files = video_processor.find_video_files(video_input_path)
        if not video_files:
            log("   No new video files found")
            return []
        
        # Check which videos need processing
        videos_to_process = []
        for video in video_files:
            expected_audio = config.INBOX_DIR / f"{video.stem}_audio.{config.VIDEO_AUDIO_FORMAT}"
            if not expected_audio.exists() or not self.resume:
                videos_to_process.append(video)
        
        if not videos_to_process:
            log(f"   All {len(video_files)} videos already processed (audio extracted)")
            # Return existing audio files
            return [config.INBOX_DIR / f"{v.stem}_audio.{config.VIDEO_AUDIO_FORMAT}" 
                   for v in video_files]
        
        log(f"   Found {len(videos_to_process)} videos to process")
        
        # Process only new videos
        results = video_processor.process_videos(
            video_input_path,
            config.INBOX_DIR,
            move_to_processed=True
        )
        
        extracted_audio = results.get("extracted_audio", [])
        
        # Mark as extracted
        for audio_file in extracted_audio:
            self.state_manager.mark_stage_complete(
                audio_file.stem.replace("_audio", ""),
                PipelineStage.AUDIO_EXTRACTED,
                audio_file
            )
        
        return extracted_audio
    
    def _download_audio_files(self) -> List[Path]:
        """Download audio files from Google Drive."""
        log("🔍 Checking Google Drive for audio files...")
        
        # List files in Drive
        drive_files = self.drive_client.list_files_in_folder(config.TO_BE_TRANSCRIBED_FOLDER_ID)
        audio_files = [f for f in drive_files 
                      if any(f["name"].endswith(ext) for ext in config.AUDIO_EXTENSIONS)]
        
        if not audio_files:
            log("   No audio files found in Google Drive")
            return []
        
        # Check which files need downloading
        files_to_download = []
        for file in audio_files:
            local_path = config.INBOX_DIR / file["name"]
            if not local_path.exists() or not self.resume:
                files_to_download.append(file)
        
        if not files_to_download:
            log(f"   All {len(audio_files)} files already downloaded")
            return [config.INBOX_DIR / f["name"] for f in audio_files]
        
        log(f"   Downloading {len(files_to_download)} new files...")
        
        # Download only new files
        downloaded = []
        for file in files_to_download:
            if self.drive_client.download_file(file["id"], file["name"], config.INBOX_DIR):
                local_path = config.INBOX_DIR / file["name"]
                downloaded.append(local_path)
                self.state_manager.mark_stage_complete(
                    local_path.stem,
                    PipelineStage.AUDIO_DOWNLOADED,
                    local_path
                )
        
        return downloaded
    
    def process_transcriptions(self, audio_files: List[Path]) -> Dict[str, Path]:
        """Process only files that need transcription."""
        if not audio_files:
            return {}
        
        log(f"\n📝 Processing {len(audio_files)} files for transcription...")
        
        transcripts = {}
        for audio_file in audio_files:
            filename = audio_file.stem
            
            # Skip if already done
            existing_transcript = config.TRANSCRIPTS_DIR / f"{filename}.txt"
            if existing_transcript.exists() and self.resume and filename not in self.force_reprocess:
                log(f"   ⏭️  Skipping {filename} (transcript exists)")
                transcripts[filename] = existing_transcript
                self.stats["skipped_stages"] += 1
                continue
            
            # Transcribe
            log(f"   🎤 Transcribing {filename}...")
            transcript = self.transcriber.transcribe_audio_file(audio_file)
            
            if transcript:
                transcript_path = config.TRANSCRIPTS_DIR / f"{filename}.txt"
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write(transcript)
                
                transcripts[filename] = transcript_path
                self.state_manager.mark_stage_complete(
                    filename,
                    PipelineStage.TRANSCRIBED,
                    transcript_path
                )
                self.stats["processed_stages"] += 1
            else:
                log(f"   ❌ Failed to transcribe {filename}")
                self.stats["errors"].append(f"Transcription failed: {filename}")
        
        return transcripts
    
    def process_parsing(self, audio_files: List[Path]) -> Dict[str, Path]:
        """Parse transcripts for files that need it."""
        if not audio_files:
            return {}
        
        log(f"\n📄 Processing {len(audio_files)} files for parsing...")
        
        if not self._parser:
            self._parser = TranscriptParser()
        
        parsed_files = {}
        for audio_file in audio_files:
            filename = audio_file.stem
            transcript_path = config.TRANSCRIPTS_DIR / f"{filename}.txt"
            parsed_path = config.PARSED_DIR / f"{filename}_parsed.txt"
            
            # Skip if already done
            if parsed_path.exists() and self.resume and filename not in self.force_reprocess:
                log(f"   ⏭️  Skipping {filename} (parsed file exists)")
                parsed_files[filename] = parsed_path
                self.stats["skipped_stages"] += 1
                continue
            
            # Check if transcript exists
            if not transcript_path.exists():
                transcript_artifact = self.state_manager.get_artifact_path(filename, PipelineStage.TRANSCRIBED)
                if transcript_artifact and transcript_artifact.exists():
                    transcript_path = transcript_artifact
                else:
                    log(f"   ⚠️  No transcript found for {filename}")
                    continue
            
            # Parse
            log(f"   📋 Parsing {filename}...")
            if self._parser.parse_transcript_file(transcript_path, parsed_path):
                parsed_files[filename] = parsed_path
                self.state_manager.mark_stage_complete(
                    filename,
                    PipelineStage.PARSED,
                    parsed_path
                )
                self.stats["processed_stages"] += 1
        
        return parsed_files
    
    def process_summaries(self, audio_files: List[Path]) -> Dict[str, Path]:
        """Generate summaries for files that need them."""
        if not audio_files:
            return {}
        
        log(f"\n🤖 Processing {len(audio_files)} files for summarization...")
        
        # Get system prompt
        system_prompt = self.drive_client.get_document_text(config.SYSTEM_PROMPT_DOC_ID)
        if not system_prompt:
            log("❌ Failed to retrieve system prompt")
            return {}
        
        if not self._summarizer:
            self._summarizer = Summarizer(config.GEMINI_API_KEY, system_prompt)
        
        summaries = {}
        for audio_file in audio_files:
            filename = audio_file.stem
            parsed_path = config.PARSED_DIR / f"{filename}_parsed.txt"
            summary_path = config.MARKDOWN_DIR / f"{filename}.md"
            
            # Skip if already done
            if summary_path.exists() and self.resume and filename not in self.force_reprocess:
                log(f"   ⏭️  Skipping {filename} (summary exists)")
                summaries[filename] = summary_path
                self.stats["skipped_stages"] += 1
                continue
            
            # Check if parsed file exists
            if not parsed_path.exists():
                parsed_artifact = self.state_manager.get_artifact_path(filename, PipelineStage.PARSED)
                if parsed_artifact and parsed_artifact.exists():
                    parsed_path = parsed_artifact
                else:
                    log(f"   ⚠️  No parsed transcript found for {filename}")
                    continue
            
            # Summarize
            log(f"   📝 Summarizing {filename}...")
            summary = self._summarizer.summarize_transcript_file(parsed_path)
            
            if summary:
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(summary)
                
                summaries[filename] = summary_path
                self.state_manager.mark_stage_complete(
                    filename,
                    PipelineStage.SUMMARIZED,
                    summary_path
                )
                self.stats["processed_stages"] += 1
        
        return summaries
    
    def run(self):
        """Run the smart pipeline."""
        start_time = time.time()
        log("🚀 Starting Smart Gemini Speech-to-Text Pipeline")
        
        # Analyze what needs to be done
        needs_processing = self.analyze_pipeline()
        
        # Process each stage only for files that need it
        
        # 1. Transcription
        if needs_processing["transcription"]:
            self.process_transcriptions(needs_processing["transcription"])
        
        # 2. Parsing
        if needs_processing["parsing"]:
            self.process_parsing(needs_processing["parsing"])
        
        # 3. Summarization
        if needs_processing["summarization"]:
            self.process_summaries(needs_processing["summarization"])
        
        # 4. HackMD Upload
        if needs_processing["hackmd_upload"] and config.HACKMD_TOKEN:
            log(f"\n☁️  Uploading {len(needs_processing['hackmd_upload'])} files to HackMD...")
            if not self._uploader:
                self._uploader = HackMDUploader(config.HACKMD_TOKEN)
            
            # Only upload files that haven't been uploaded
            files_to_upload = []
            for audio_file in needs_processing["hackmd_upload"]:
                filename = audio_file.stem
                if not self.state_manager.is_stage_complete(filename, PipelineStage.HACKMD_UPLOADED):
                    md_file = config.MARKDOWN_DIR / f"{filename}.md"
                    if md_file.exists():
                        files_to_upload.append(md_file)
            
            if files_to_upload:
                # Custom upload that doesn't move files yet
                shared_links = []
                for md_file in files_to_upload:
                    result = self._uploader.upload_file(md_file)
                    if result:
                        shared_links.append(result)
                        self.state_manager.mark_stage_complete(
                            md_file.stem,
                            PipelineStage.HACKMD_UPLOADED
                        )
                        self.stats["processed_stages"] += 1
                
                # Send email if configured
                if shared_links and config.EMAIL_USER and config.EMAIL_PASS and config.EMAIL_TO:
                    log("\n📧 Sending email notification...")
                    if not self._email_sender:
                        self._email_sender = EmailSender(config.EMAIL_USER, config.EMAIL_PASS)
                    self._email_sender.send_hackmd_links(config.EMAIL_TO, shared_links)
        
        # 5. Google Drive Upload (SKIPPED - Manual upload mode)
        if needs_processing["drive_upload"]:
            log(f"\n📤 Skipping Google Drive upload (manual mode)...")
            log(f"   {len(needs_processing['drive_upload'])} file sets ready for manual upload")
            
            # Mark as completed locally without uploading
            for audio_file in needs_processing["drive_upload"]:
                filename = audio_file.stem
                
                # Check all artifacts exist
                transcript = config.TRANSCRIPTS_DIR / f"{filename}.txt"
                parsed = config.PARSED_DIR / f"{filename}_parsed.txt"
                summary = config.MARKDOWN_DIR / f"{filename}.md"
                
                if all(f.exists() for f in [transcript, parsed, summary]):
                    # Mark as complete without uploading
                    self.state_manager.mark_stage_complete(
                        filename,
                        PipelineStage.DRIVE_UPLOADED
                    )
                    self.state_manager.mark_stage_complete(
                        filename,
                        PipelineStage.COMPLETED
                    )
                    self.stats["processed_stages"] += 1
            
            log("\n   ℹ️  Run 'organize_files.bat' to prepare files for manual upload")
        
        # Final report
        duration = time.time() - start_time
        log(f"\n{'='*60}")
        log("✅ Smart Pipeline Complete!")
        log(f"   Total files: {self.stats['total_files']}")
        log(f"   Stages processed: {self.stats['processed_stages']}")
        log(f"   Stages skipped: {self.stats['skipped_stages']}")
        log(f"   Errors: {len(self.stats['errors'])}")
        log(f"   Duration: {duration/60:.1f} minutes")
        log(f"{'='*60}")
        
        # Show pipeline state summary
        if self.resume:
            summary = self.state_manager.get_pipeline_summary()
            completed = sum(1 for f, s in summary.items() 
                          if PipelineStage.COMPLETED.value in s["stages_completed"])
            log(f"\n📊 Pipeline State: {completed}/{len(summary)} files fully completed")
    
    def _upload_single_result_to_drive(self, filename: str, transcript_path: Path) -> bool:
        """Upload a single file's results to Drive."""
        try:
            # Create folder
            folder_id = self.drive_client.ensure_subfolder(config.PROCESSED_FOLDER_ID, filename)
            if not folder_id:
                return False
            
            # Upload files
            files_to_upload = [
                transcript_path,
                config.PARSED_DIR / f"{filename}_parsed.txt",
                config.MARKDOWN_DIR / f"{filename}.md"
            ]
            
            success = True
            for file_path in files_to_upload:
                if file_path.exists():
                    if not self.drive_client.upload_file(file_path, folder_id):
                        success = False
            
            # Move original audio if successful
            if success:
                audio_name = f"{filename}.{list(config.AUDIO_EXTENSIONS)[0]}"  # Approximate
                audio_in_drive = self.drive_client.find_file_by_name(
                    audio_name, 
                    config.TO_BE_TRANSCRIBED_FOLDER_ID
                )
                if audio_in_drive:
                    self.drive_client.move_file(
                        audio_in_drive["id"],
                        config.TRANSCRIBED_FOLDER_ID,
                        config.TO_BE_TRANSCRIBED_FOLDER_ID
                    )
            
            return success
        except Exception as e:
            log(f"❌ Error uploading {filename}: {e}")
            return False


def main():
    """Main entry point with command line arguments."""
    parser = argparse.ArgumentParser(description="Smart Gemini Speech-to-Text Pipeline")
    parser.add_argument(
        "--resume", 
        action="store_true",
        help="Resume from previous state, skipping completed stages"
    )
    parser.add_argument(
        "--force",
        nargs="+",
        metavar="FILENAME",
        help="Force reprocess specific files (by stem name)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show pipeline status and exit"
    )
    
    args = parser.parse_args()
    
    # Just show status if requested
    if args.status:
        state_manager = PipelineStateManager(config.DATA_DIR / "pipeline_state.json")
        summary = state_manager.get_pipeline_summary()
        
        print("\n📊 Pipeline Status Report")
        print("=" * 60)
        
        if not summary:
            print("No files in pipeline state.")
        else:
            for filename, info in summary.items():
                print(f"\n📄 {filename}")
                print(f"   Stages completed: {', '.join(info['stages_completed'])}")
                print(f"   Last updated: {info['last_updated']}")
                
                # Check artifacts
                missing = [stage for stage, exists in info['artifacts_exist'].items() if not exists]
                if missing:
                    print(f"   ⚠️  Missing artifacts: {', '.join(missing)}")
        
        print("\n" + "=" * 60)
        sys.exit(0)
    
    # Run the pipeline
    pipeline = SmartPipeline(resume=args.resume, force_reprocess=args.force or [])
    pipeline.run()


if __name__ == "__main__":
    main()