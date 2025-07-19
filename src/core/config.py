"""Configuration management for Gemini STT."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Central configuration management."""
    
    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration from environment variables."""
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # API Keys and Authentication
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gdrive_service_account_json = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON")
        self.hackmd_token = os.getenv("HACKMD_TOKEN")
        
        # Google Drive Configuration
        self.to_be_transcribed_folder_id = os.getenv("TO_BE_TRANSCRIBED_FOLDER_ID")
        self.transcribed_folder_id = os.getenv("TRANSCRIBED_FOLDER_ID")
        self.processed_folder_id = os.getenv("PROCESSED_FOLDER_ID")
        self.system_prompt_doc_id = os.getenv("SYSTEM_PROMPT_DOC_ID", "1p44XUpBu7lPjyux4eANd_9FHT5F1UDbgUyx7q6Libvk")
        
        # Email Configuration
        self.email_user = os.getenv("EMAIL_USER")
        self.email_pass = os.getenv("EMAIL_PASS")
        self.email_to = os.getenv("EMAIL_TO")
        
        # Local Processing Configuration
        self.process_local_audio = os.getenv("PROCESS_LOCAL_AUDIO", "false").lower() == "true"
        self.audio_input_dir = os.getenv("AUDIO_INPUT_DIR", "")
        self.process_videos = os.getenv("PROCESS_VIDEOS", "false").lower() == "true"
        self.video_input_dir = os.getenv("VIDEO_INPUT_DIR", "")
        
        # Google Drive Organization
        self.organize_to_folders = os.getenv("ORGANIZE_TO_FOLDERS", "true").lower() == "true"
        self.upload_audio_to_drive = os.getenv("UPLOAD_AUDIO_TO_DRIVE", "false").lower() == "true"
        
        # Audio Processing Configuration
        self.chunk_duration_seconds = int(os.getenv("CHUNK_DURATION_SECONDS", "300"))
        self.video_audio_format = os.getenv("VIDEO_AUDIO_FORMAT", "m4a")
        self.video_audio_bitrate = os.getenv("VIDEO_AUDIO_BITRATE", "192k")
        self.video_audio_samplerate = int(os.getenv("VIDEO_AUDIO_SAMPLERATE", "44100"))
        
        # Working Directories
        self.working_dir = Path("./working")
        self.inbox_dir = self.working_dir / "from_google_drive"
        self.transcripts_dir = self.working_dir / "transcription"
        self.parsed_dir = self.working_dir / "parsed"
        self.markdown_dir = self.working_dir / "markdown"
        self.uploaded_dir = self.working_dir / "uploaded"
        
        # Audio Extensions
        self.audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}
        
        # Video Extensions
        self.video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}
        
        # Google API Scopes
        self.google_scopes = ["https://www.googleapis.com/auth/drive"]
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate required configuration values.
        
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required API keys
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY is missing")
        
        if not self.gdrive_service_account_json:
            errors.append("GDRIVE_SERVICE_ACCOUNT_JSON is missing")
        
        # Check Google Drive folder IDs
        if not self.to_be_transcribed_folder_id:
            errors.append("TO_BE_TRANSCRIBED_FOLDER_ID is missing")
        
        if not self.transcribed_folder_id:
            errors.append("TRANSCRIBED_FOLDER_ID is missing")
        
        if not self.processed_folder_id:
            errors.append("PROCESSED_FOLDER_ID is missing")
        
        # Check local directories if processing is enabled
        if self.process_videos and not self.video_input_dir:
            errors.append("VIDEO_INPUT_DIR is missing but PROCESS_VIDEOS is enabled")
        
        if self.process_local_audio and not self.audio_input_dir:
            errors.append("AUDIO_INPUT_DIR is missing but PROCESS_LOCAL_AUDIO is enabled")
        
        return len(errors) == 0, errors
    
    def setup_directories(self):
        """Create all necessary working directories."""
        for dir_path in [
            self.working_dir,
            self.inbox_dir,
            self.transcripts_dir,
            self.parsed_dir,
            self.markdown_dir,
            self.uploaded_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)