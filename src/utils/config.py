import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys and Secrets
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
HACKMD_TOKEN = os.getenv('HACKMD_TOKEN')

# Google Drive Configuration
GDRIVE_SERVICE_ACCOUNT_JSON = os.getenv('GDRIVE_SERVICE_ACCOUNT_JSON')
TO_BE_TRANSCRIBED_FOLDER_ID = os.getenv('TO_BE_TRANSCRIBED_FOLDER_ID')
TRANSCRIBED_FOLDER_ID = os.getenv('TRANSCRIBED_FOLDER_ID')
PROCESSED_FOLDER_ID = os.getenv('PROCESSED_FOLDER_ID')

# Google Docs Configuration
SYSTEM_PROMPT_DOC_ID = os.getenv('SYSTEM_PROMPT_DOC_ID', '1p44XUpBu7lPjyux4eANd_9FHT5F1UDbgUyx7q6Libvk')

# Email Configuration
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
EMAIL_TO = os.getenv('EMAIL_TO')

# Audio Processing Configuration
CHUNK_DURATION_SECONDS = int(os.getenv('CHUNK_DURATION_SECONDS', '300'))  # 5 minutes default
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm', '.aac', '.wma'}

# File Management Configuration
DELETE_LOCAL_FILES_AFTER_UPLOAD = os.getenv('DELETE_LOCAL_FILES_AFTER_UPLOAD', 'false').lower() == 'true'

# Video Processing Configuration
VIDEO_INPUT_DIR = os.getenv('VIDEO_INPUT_DIR', '')
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}
PROCESS_VIDEOS = os.getenv('PROCESS_VIDEOS', 'false').lower() == 'true'
VIDEO_AUDIO_FORMAT = os.getenv('VIDEO_AUDIO_FORMAT', 'm4a')  # Output format for extracted audio
VIDEO_AUDIO_BITRATE = os.getenv('VIDEO_AUDIO_BITRATE', '192k')
VIDEO_AUDIO_SAMPLERATE = int(os.getenv('VIDEO_AUDIO_SAMPLERATE', '44100'))

# Paths Configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
INBOX_DIR = DATA_DIR / 'inbox'
TRANSCRIPTS_DIR = DATA_DIR / 'transcripts'
PARSED_DIR = DATA_DIR / 'parsed'
MARKDOWN_DIR = DATA_DIR / 'markdown'
UPLOADED_DIR = DATA_DIR / 'uploaded'
LOGS_DIR = BASE_DIR / 'logs'

# Ensure directories exist
for dir_path in [DATA_DIR, INBOX_DIR, TRANSCRIPTS_DIR, PARSED_DIR, MARKDOWN_DIR, UPLOADED_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Validate required environment variables
def validate_config():
    """Validate required configuration and provide helpful error messages."""
    errors = []
    
    # Check required environment variables
    required_vars = {
        'GEMINI_API_KEY': GEMINI_API_KEY,
        'GDRIVE_SERVICE_ACCOUNT_JSON': GDRIVE_SERVICE_ACCOUNT_JSON,
        'TO_BE_TRANSCRIBED_FOLDER_ID': TO_BE_TRANSCRIBED_FOLDER_ID,
        'TRANSCRIBED_FOLDER_ID': TRANSCRIBED_FOLDER_ID,
        'PROCESSED_FOLDER_ID': PROCESSED_FOLDER_ID,
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        errors.append(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Check if service account JSON is valid (can be JSON string or file path)
    if GDRIVE_SERVICE_ACCOUNT_JSON:
        import json
        # Try to parse as JSON first
        try:
            json.loads(GDRIVE_SERVICE_ACCOUNT_JSON)
            # It's valid JSON content
        except json.JSONDecodeError:
            # Not JSON, check if it's a valid file path
            sa_path = Path(GDRIVE_SERVICE_ACCOUNT_JSON)
            if not sa_path.exists():
                errors.append(f"Google Drive service account is neither valid JSON nor an existing file: {GDRIVE_SERVICE_ACCOUNT_JSON[:50]}...")
            elif not sa_path.is_file():
                errors.append(f"Service account path exists but is not a file: {GDRIVE_SERVICE_ACCOUNT_JSON}")
    
    # Check video processing configuration if enabled
    if PROCESS_VIDEOS:
        if not VIDEO_INPUT_DIR:
            errors.append("VIDEO_INPUT_DIR must be set when PROCESS_VIDEOS is true")
        else:
            video_path = Path(VIDEO_INPUT_DIR)
            if not video_path.exists():
                errors.append(f"Video input directory not found: {VIDEO_INPUT_DIR}")
    
    if errors:
        error_msg = "\n".join(f"  - {err}" for err in errors)
        raise ValueError(f"Configuration errors:\n{error_msg}")