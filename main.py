#!/usr/bin/env python3
"""
Gemini Speech-to-Text Transcriber
Main entry point for the modular transcription pipeline.
"""

import sys
from pathlib import Path
from typing import List, Dict

# Import audio compatibility first for Python 3.13+
from src.core.audio_compat import setup_audio_compatibility

from tqdm import tqdm

from src.core import Config, PipelineState
from src.core.logger import logger
from src.core.exceptions import GeminiSTTError, ConfigurationError
from src.audio import AudioProcessor, VideoProcessor
from src.transcription import GeminiTranscriber, TranscriptParser
from src.storage import GoogleDriveManager, LocalStorageManager, FolderOrganizer
from src.summary import SummaryGenerator, HackMDUploader
from src.notification import EmailNotifier


class GeminiSTTPipeline:
    """Main pipeline for Gemini STT processing."""
    
    def __init__(self, config: Config, resume: bool = True):
        """Initialize the pipeline with configuration.
        
        Args:
            config: Configuration object
            resume: Whether to resume from previous state
        """
        self.config = config
        
        # Validate configuration
        is_valid, errors = config.validate()
        if not is_valid:
            raise ConfigurationError(f"Invalid configuration: {', '.join(errors)}")
        
        # Initialize state manager
        self.state = PipelineState()
        
        # Check if we should resume
        if resume and self.state.should_resume():
            logger.info("Resuming from previous pipeline state")
        elif not resume and self.state.state_file.exists():
            logger.info("Starting fresh pipeline run")
            self.state.clear()
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize all pipeline components."""
        try:
            # Storage managers
            self.gdrive = GoogleDriveManager(
                self.config.gdrive_service_account_json,
                self.config.google_scopes
            )
            self.local_storage = LocalStorageManager()
            
            # Audio processors
            self.video_processor = VideoProcessor(
                video_extensions=self.config.video_extensions,
                audio_format=self.config.video_audio_format,
                audio_bitrate=self.config.video_audio_bitrate,
                audio_samplerate=self.config.video_audio_samplerate
            )
            
            # Transcription
            self.transcriber = GeminiTranscriber(
                api_key=self.config.gemini_api_key,
                chunk_duration_seconds=self.config.chunk_duration_seconds
            )
            self.transcript_parser = TranscriptParser()
            
            # Summary generation
            self.summary_generator = SummaryGenerator(
                api_key=self.config.gemini_api_key
            )
            
            # Folder organizer
            self.folder_organizer = FolderOrganizer(
                gdrive_manager=self.gdrive,
                local_storage=self.local_storage,
                upload_audio=self.config.upload_audio_to_drive,
                state=self.state
            )
            
            # HackMD uploader (optional)
            self.hackmd = None
            if self.config.hackmd_token:
                self.hackmd = HackMDUploader(self.config.hackmd_token)
            
            # Email notifier (optional)
            self.email = None
            if all([self.config.email_user, self.config.email_pass, self.config.email_to]):
                self.email = EmailNotifier(
                    smtp_user=self.config.email_user,
                    smtp_pass=self.config.email_pass
                )
            
            logger.success("All components initialized successfully")
            
        except Exception as e:
            raise GeminiSTTError(f"Failed to initialize components: {e}") from e
    
    def run(self):
        """Run the complete transcription pipeline."""
        try:
            logger.info("Starting Gemini STT Pipeline")
            
            # Setup directories
            self.config.setup_directories()
            
            # Process files
            local_files_processed = self._process_local_files()
            
            # Only process Google Drive if no local files
            if not local_files_processed:
                self._process_google_drive_files()
            
            # Process all collected audio files
            audio_files = self.local_storage.find_files(
                self.config.inbox_dir,
                self.config.audio_extensions
            )
            
            if not audio_files:
                logger.warning("No audio files to process")
                return
            
            # Filter out files that are already organized
            audio_files = self._filter_already_organized(audio_files)
            
            if not audio_files:
                logger.info("All files already organized, nothing to process")
                return
            
            # Transcribe files
            transcripts = self._transcribe_files(audio_files)
            
            if not transcripts:
                logger.error("No files were successfully transcribed")
                return
            
            # Parse transcripts
            parsed_transcripts = self._parse_transcripts(transcripts)
            
            # Generate summaries
            summaries = self._generate_summaries(parsed_transcripts)
            
            # Upload to HackMD
            shared_links = []
            if summaries and self.hackmd:
                shared_links = self._upload_to_hackmd(summaries)
            
            # Sync to Google Drive (only if files came from Drive)
            if not local_files_processed:
                self._sync_to_google_drive(summaries)
            
            # Organize files into Google Drive folders if configured
            if self.config.organize_to_folders:
                self._organize_to_drive_folders(summaries)
            
            # Send email notification
            if shared_links and self.email:
                self._send_email_notification(shared_links)
            
            logger.success("Pipeline completed successfully!")
            
        except Exception as e:
            logger.failure(f"Pipeline failed: {e}")
            
            # Send error notification if email is configured
            if self.email and self.config.email_to:
                self.email.send_error_notification(
                    self.config.email_to,
                    str(e),
                    "Main pipeline execution"
                )
            
            raise
    
    def _process_local_files(self) -> bool:
        """Process local video and audio files.
        
        Returns:
            True if local files were processed
        """
        local_files_found = False
        
        # Check if this step is already complete
        if self.state.is_step_complete("process_local_files"):
            logger.info("Local file processing already complete, skipping")
            return len(self.state.get_processed_files("audio")) > 0
        
        self.state.set_current_step("process_local_files")
        
        # Process video files
        if self.config.process_videos and self.config.video_input_dir:
            video_dir = Path(self.config.video_input_dir)
            
            if video_dir.exists():
                logger.info(f"Checking for video files in {video_dir}")
                
                audio_output_dir = Path(self.config.audio_input_dir) if self.config.audio_input_dir else video_dir / "audio_only"
                
                try:
                    # Find video files
                    video_files = self.video_processor.find_video_files(video_dir)
                    
                    # Filter out already processed videos
                    new_videos = []
                    for video in video_files:
                        if not self.state.is_file_processed("video", video.name):
                            new_videos.append(video)
                    
                    if new_videos:
                        logger.info(f"Processing {len(new_videos)} new video(s)")
                        
                        results = self.video_processor.process_videos(
                            input_dir=video_dir,
                            output_dir=audio_output_dir,
                            move_to_processed=True
                        )
                        
                        # Record processed videos
                        for video in results["successful"]:
                            self.state.add_processed_file("video", video.name, {
                                "output_audio": str(audio_output_dir / f"{video.stem}_audio.{self.config.video_audio_format}")
                            })
                        
                        # Copy extracted audio to inbox
                        if results["extracted_audio"]:
                            copied = self.local_storage.copy_files(
                                results["extracted_audio"],
                                self.config.inbox_dir
                            )
                            
                            # Record audio files
                            for audio_file in copied:
                                self.state.add_processed_file("audio", audio_file.name, {
                                    "source": "video_extraction",
                                    "path": str(audio_file)
                                })
                            
                            local_files_found = True
                    else:
                        logger.info("All videos already processed")
                        
                except Exception as e:
                    logger.error(f"Video processing failed: {e}")
                    self.state.add_error(str(e), "video_processing")
        
        # Process existing audio files
        if self.config.process_local_audio and self.config.audio_input_dir:
            audio_dir = Path(self.config.audio_input_dir)
            
            if audio_dir.exists():
                logger.info(f"Checking for audio files in {audio_dir}")
                
                audio_files = self.local_storage.find_files(
                    audio_dir,
                    self.config.audio_extensions,
                    recursive=False
                )
                
                # Filter out already processed audio files
                new_audio = []
                for audio in audio_files:
                    if not self.state.is_file_processed("audio", audio.name):
                        new_audio.append(audio)
                
                if new_audio:
                    logger.info(f"Processing {len(new_audio)} new audio file(s)")
                    
                    copied = self.local_storage.copy_files(
                        new_audio,
                        self.config.inbox_dir
                    )
                    
                    # Record audio files
                    for audio_file in copied:
                        self.state.add_processed_file("audio", audio_file.name, {
                            "source": "local_audio",
                            "path": str(audio_file)
                        })
                    
                    local_files_found = True
                else:
                    logger.info("All audio files already processed")
        
        if local_files_found:
            self.state.mark_step_complete("process_local_files")
        
        return local_files_found
    
    def _process_google_drive_files(self):
        """Download and process files from Google Drive."""
        logger.info("Checking Google Drive for files...")
        
        try:
            files = self.gdrive.list_files_in_folder(
                self.config.to_be_transcribed_folder_id
            )
            
            if files:
                logger.info(f"Found {len(files)} file(s) in Google Drive")
                
                # Download audio files only
                audio_extensions = list(self.config.audio_extensions)
                self.gdrive.download_files_from_folder(
                    self.config.to_be_transcribed_folder_id,
                    self.config.inbox_dir,
                    file_filter=audio_extensions
                )
            else:
                logger.info("No files found in Google Drive")
                
        except Exception as e:
            logger.error(f"Failed to process Google Drive files: {e}")
    
    def _transcribe_files(self, audio_files: List[Path]) -> Dict[str, str]:
        """Transcribe audio files.
        
        Args:
            audio_files: List of audio file paths
            
        Returns:
            Dictionary mapping file stems to transcripts
        """
        transcripts = {}
        
        # Load existing transcriptions
        existing_transcriptions = self.state.get_transcriptions()
        
        # Filter out already transcribed files
        files_to_transcribe = []
        for audio_file in audio_files:
            if audio_file.stem in existing_transcriptions:
                # Load existing transcript
                transcript_path = Path(existing_transcriptions[audio_file.stem]["path"])
                if transcript_path.exists():
                    transcript = self.local_storage.read_file(transcript_path)
                    transcripts[audio_file.stem] = transcript
                    logger.info(f"Loaded existing transcript for {audio_file.name}")
                else:
                    files_to_transcribe.append(audio_file)
            else:
                files_to_transcribe.append(audio_file)
        
        if not files_to_transcribe:
            logger.info("All files already transcribed")
            return transcripts
        
        logger.info(f"Transcribing {len(files_to_transcribe)} new file(s)")
        
        with tqdm(files_to_transcribe, desc="Transcribing files", unit="file") as pbar:
            for audio_file in pbar:
                pbar.set_description(f"Transcribing: {audio_file.name}")
                
                try:
                    transcript = self.transcriber.transcribe_audio_file(audio_file)
                    
                    if transcript:
                        # Save transcript
                        transcript_path = self.config.transcripts_dir / f"{audio_file.stem}.txt"
                        self.local_storage.write_file(transcript_path, transcript)
                        
                        # Record in state
                        self.state.add_transcription(audio_file.stem, str(transcript_path))
                        
                        transcripts[audio_file.stem] = transcript
                        logger.success(f"Transcribed {audio_file.name}")
                    else:
                        logger.error(f"Failed to transcribe {audio_file.name}")
                        self.state.add_error(f"Failed to transcribe {audio_file.name}", "transcription")
                        
                except Exception as e:
                    logger.error(f"Error transcribing {audio_file.name}: {e}")
                    self.state.add_error(str(e), f"transcription_{audio_file.name}")
        
        return transcripts
    
    def _parse_transcripts(self, transcripts: Dict[str, str]) -> Dict[str, str]:
        """Parse transcripts into formatted blocks.
        
        Args:
            transcripts: Dictionary of raw transcripts
            
        Returns:
            Dictionary of parsed transcripts
        """
        parsed = {}
        
        for stem, transcript in transcripts.items():
            logger.info(f"Parsing transcript for {stem}")
            
            parsed_text = self.transcript_parser.parse_transcript_simple(transcript)
            
            # Save parsed transcript
            parsed_path = self.config.parsed_dir / f"{stem}_parsed.txt"
            self.local_storage.write_file(parsed_path, parsed_text)
            
            parsed[stem] = parsed_text
        
        return parsed
    
    def _generate_summaries(self, transcripts: Dict[str, str]) -> Dict[str, str]:
        """Generate summaries from transcripts.
        
        Args:
            transcripts: Dictionary of parsed transcripts
            
        Returns:
            Dictionary of summaries
        """
        summaries = {}
        
        try:
            # Get system prompt from Google Doc
            system_prompt = self.gdrive.get_document_text(self.config.system_prompt_doc_id)
            logger.info("Retrieved system prompt from Google Doc")
            
            # Load existing summaries
            existing_summaries = self.state.get_summaries()
            
            # Filter transcripts that need summaries
            transcripts_to_summarize = {}
            for stem, transcript in transcripts.items():
                # Check if summary already exists in uploaded directory
                uploaded_summary_path = self.config.uploaded_dir / f"{stem}.md"
                
                if uploaded_summary_path.exists():
                    # Summary already uploaded, just load it
                    summary = self.local_storage.read_file(uploaded_summary_path)
                    summaries[stem] = summary
                    logger.info(f"Found existing summary in uploaded directory for {stem}")
                elif stem in existing_summaries:
                    # Load existing summary from state
                    summary_path = Path(existing_summaries[stem]["path"])
                    if summary_path.exists():
                        summary = self.local_storage.read_file(summary_path)
                        summaries[stem] = summary
                        logger.info(f"Loaded existing summary for {stem}")
                    else:
                        transcripts_to_summarize[stem] = transcript
                else:
                    transcripts_to_summarize[stem] = transcript
            
            if not transcripts_to_summarize:
                logger.info("All summaries already generated")
                return summaries
            
            logger.info(f"Generating {len(transcripts_to_summarize)} new summaries")
            
            # Generate new summaries
            new_summaries = self.summary_generator.batch_generate_summaries(
                transcripts_to_summarize,
                system_prompt
            )
            
            # Save summaries
            for stem, summary in new_summaries.items():
                summary_path = self.config.markdown_dir / f"{stem}.md"
                self.local_storage.write_file(summary_path, summary)
                
                # Record in state
                self.state.add_summary(stem, str(summary_path))
                
                summaries[stem] = summary
            
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to generate summaries: {e}")
            self.state.add_error(str(e), "summary_generation")
            return summaries
    
    def _upload_to_hackmd(self, summaries: Dict[str, str]) -> List[Dict]:
        """Upload summaries to HackMD.
        
        Args:
            summaries: Dictionary of summaries
            
        Returns:
            List of shared links
        """
        if not self.hackmd:
            return []
        
        logger.info("Uploading summaries to HackMD...")
        
        # Filter out summaries that are already uploaded
        notes_to_upload = {}
        already_uploaded = []
        
        for stem, content in summaries.items():
            # Check if already in uploaded directory
            uploaded_path = self.config.uploaded_dir / f"{stem}.md"
            if uploaded_path.exists():
                logger.info(f"Skipping HackMD upload for {stem} - already in uploaded directory")
                already_uploaded.append(stem)
            else:
                notes_to_upload[f"{stem}.md"] = content
        
        # Upload only new summaries
        shared_links = []
        if notes_to_upload:
            logger.info(f"Uploading {len(notes_to_upload)} new summaries to HackMD")
            shared_links = self.hackmd.batch_upload_notes(notes_to_upload)
        else:
            logger.info("No new summaries to upload to HackMD")
        
        if already_uploaded:
            logger.info(f"Skipped {len(already_uploaded)} already uploaded summaries")
        
        # Move only newly uploaded files
        for stem in summaries:
            # Only process files that were actually uploaded
            if f"{stem}.md" in notes_to_upload:
                source = self.config.markdown_dir / f"{stem}.md"
                dest = self.config.uploaded_dir / f"{stem}.md"
                
                if source.exists():
                    # Check if destination already exists
                    if dest.exists():
                        # File already in uploaded, just remove source
                        source.unlink()
                        logger.info(f"File {stem}.md already in uploaded directory, removed duplicate")
                    else:
                        source.rename(dest)
        
        return shared_links
    
    def _sync_to_google_drive(self, summaries: Dict[str, str]):
        """Sync processed files to Google Drive."""
        logger.info("Syncing processed files to Google Drive...")
        
        sync_failures = []
        sync_successes = []
        
        for stem in summaries:
            # Skip if already synced
            if self.state.is_gdrive_synced(stem):
                logger.info(f"Already synced {stem} to Google Drive, skipping")
                continue
                
            try:
                # Create folder for this audio file
                folder_id = self.gdrive.ensure_folder(
                    self.config.processed_folder_id,
                    stem
                )
                
                # Upload related files
                files_to_upload = [
                    self.config.transcripts_dir / f"{stem}.txt",
                    self.config.parsed_dir / f"{stem}_parsed.txt",
                    self.config.uploaded_dir / f"{stem}.md"
                ]
                
                for file_path in files_to_upload:
                    if file_path.exists():
                        self.gdrive.upload_file(file_path, folder_id)
                
                # Move original audio in Google Drive
                audio_files = self.local_storage.find_files(
                    self.config.inbox_dir,
                    self.config.audio_extensions,
                    recursive=False
                )
                
                for audio_file in audio_files:
                    if audio_file.stem == stem:
                        file_id = self.gdrive.find_file_by_name(
                            self.config.to_be_transcribed_folder_id,
                            audio_file.name
                        )
                        
                        if file_id:
                            self.gdrive.move_file(
                                file_id,
                                self.config.to_be_transcribed_folder_id,
                                self.config.transcribed_folder_id
                            )
                        break
                
                # Mark as successfully synced
                self.state.add_gdrive_sync(stem, folder_id)
                sync_successes.append(stem)
                logger.success(f"Successfully synced {stem} to Google Drive")
                        
            except Exception as e:
                error_msg = f"Failed to sync {stem} to Google Drive: {e}"
                logger.error(error_msg)
                self.state.add_error(error_msg, "gdrive_sync")
                sync_failures.append(stem)
        
        # Report summary
        if sync_successes:
            logger.info(f"Successfully synced {len(sync_successes)} files to Google Drive")
        if sync_failures:
            logger.warning(f"Failed to sync {len(sync_failures)} files: {', '.join(sync_failures)}")
            logger.info("Failed files can be retried by running the pipeline again")
    
    def _filter_already_organized(self, audio_files: List[Path]) -> List[Path]:
        """Filter out files that are already organized and clean up their working files.
        
        Args:
            audio_files: List of audio file paths
            
        Returns:
            Filtered list of audio files to process
        """
        filtered_files = []
        organized_dir = self.config.working_dir / "organized_for_upload"
        
        for audio_file in audio_files:
            stem = audio_file.stem
            
            # Check if already organized locally
            local_folder = organized_dir / stem
            if local_folder.exists() and any(local_folder.iterdir()):
                logger.info(f"Skipping {stem} - already organized in {local_folder}")
                
                # Clean up working files for this stem
                self._cleanup_working_files(stem)
                
                # Mark as organized in state
                self.state.add_folder_organized(stem, "local")
                continue
            
            # Check if already organized in state
            if self.state.is_folder_organized(stem):
                logger.info(f"Skipping {stem} - already organized (tracked in state)")
                
                # Clean up working files for this stem
                self._cleanup_working_files(stem)
                continue
            
            filtered_files.append(audio_file)
        
        if len(filtered_files) < len(audio_files):
            logger.info(f"Filtered out {len(audio_files) - len(filtered_files)} already organized files")
        
        return filtered_files
    
    def _cleanup_working_files(self, stem: str):
        """Clean up all working files for a given stem.
        
        Args:
            stem: The file stem to clean up
        """
        files_to_clean = [
            self.config.transcripts_dir / f"{stem}.txt",
            self.config.parsed_dir / f"{stem}_parsed.txt",
            self.config.markdown_dir / f"{stem}.md",
            self.config.uploaded_dir / f"{stem}.md",
            self.config.inbox_dir / f"{stem}.m4a",
            self.config.inbox_dir / f"{stem}_audio.m4a",
        ]
        
        for file_path in files_to_clean:
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"  Cleaned up: {file_path.name}")
                except Exception as e:
                    logger.error(f"  Failed to clean up {file_path.name}: {e}")
    
    def _send_email_notification(self, shared_links: List[Dict]):
        """Send email notification with results."""
        if not self.email or not self.config.email_to:
            return
        
        logger.info("Sending email notification...")
        
        try:
            self.email.send_summary_notification(
                self.config.email_to,
                shared_links
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    def _organize_to_drive_folders(self, summaries: Dict[str, str]):
        """Organize processed files into structured Google Drive folders."""
        logger.info("Organizing processed files into Google Drive folders...")
        
        try:
            # Get list of audio files
            audio_files = self.local_storage.find_files(
                self.config.inbox_dir,
                self.config.audio_extensions
            )
            
            # Filter to only the audio files we processed
            processed_audio = []
            for audio_file in audio_files:
                if audio_file.stem in summaries:
                    processed_audio.append(audio_file)
            
            # Prepare local backup directory
            local_backup_dir = self.config.working_dir / "organized_for_upload"
            local_backup_dir.mkdir(exist_ok=True)
            
            # Organize files to Drive
            folder_map = self.folder_organizer.organize_to_drive(
                processed_folder_id=self.config.processed_folder_id,
                transcripts_dir=self.config.transcripts_dir,
                parsed_dir=self.config.parsed_dir,
                summaries_dir=self.config.uploaded_dir,  # Summaries are in uploaded dir after HackMD
                audio_files=processed_audio,
                local_backup_dir=local_backup_dir
            )
            
            # If successful, sync audio files from to_be_transcribed to transcribed folder
            if folder_map and hasattr(self.config, 'to_be_transcribed_folder_id') and hasattr(self.config, 'transcribed_folder_id'):
                self.folder_organizer.sync_audio_files(
                    from_folder_id=self.config.to_be_transcribed_folder_id,
                    to_folder_id=self.config.transcribed_folder_id,
                    processed_stems=list(folder_map.keys())
                )
            
        except Exception as e:
            logger.error(f"Failed to organize files to Google Drive folders: {e}")
            self.state.add_error(str(e), "folder_organization")


def main():
    """Main entry point."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Gemini STT Pipeline")
    parser.add_argument("--no-resume", action="store_true", 
                       help="Start fresh, ignoring previous state")
    parser.add_argument("--clear-state", action="store_true",
                       help="Clear all state and exit")
    parser.add_argument("--show-state", action="store_true",
                       help="Show current pipeline state and exit")
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = Config()
        
        # Handle state operations
        if args.clear_state:
            state = PipelineState()
            state.clear()
            logger.info("Pipeline state cleared")
            return
        
        if args.show_state:
            state = PipelineState()
            logger.info("Current pipeline state:")
            logger.info(f"  Created: {state.state.get('created_at', 'Unknown')}")
            logger.info(f"  Last updated: {state.state.get('last_updated', 'Unknown')}")
            logger.info(f"  Completed steps: {', '.join(state.state.get('completed_steps', []))}")
            logger.info(f"  Files processed: {sum(len(files) for files in state.state.get('files_processed', {}).values())}")
            logger.info(f"  Transcriptions: {len(state.state.get('transcriptions', {}))}")
            logger.info(f"  Summaries: {len(state.state.get('summaries', {}))}")
            logger.info(f"  Google Drive synced: {len(state.state.get('gdrive_synced', {}))}")
            logger.info(f"  Folders organized: {len(state.state.get('folders_organized', {}))}")
            logger.info(f"  HackMD uploads: {len(state.state.get('uploads', {}).get('hackmd', {}))}")
            logger.info(f"  Errors: {len(state.state.get('errors', []))}")
            
            # Show failed syncs
            failed_syncs = state.get_failed_syncs()
            if failed_syncs:
                logger.warning(f"  Failed syncs: {', '.join(failed_syncs)}")
            
            # Show recent errors
            errors = state.state.get('errors', [])
            if errors and len(errors) > 0:
                logger.info("\n  Recent errors:")
                for error in errors[-3:]:  # Show last 3 errors
                    logger.info(f"    - {error.get('context', 'Unknown')}: {error.get('error', 'Unknown error')[:80]}...")
            return
        
        # Create and run pipeline
        pipeline = GeminiSTTPipeline(config, resume=not args.no_resume)
        pipeline.run()
        
    except ConfigurationError as e:
        logger.failure(f"Configuration error: {e}")
        logger.info("Please check your .env file and ensure all required values are set")
        sys.exit(1)
    except GeminiSTTError as e:
        logger.failure(f"Pipeline error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.failure(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()