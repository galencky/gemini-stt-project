# Gemini STT - Speech-to-Text Pipeline

A modular, production-ready speech-to-text pipeline using Google's Gemini API with automatic audio chunking, multi-language support, and comprehensive error handling.

## Features

- 🎥 **Video Processing**: Automatically extract audio from video files
- 🎵 **Audio Chunking**: Handle long recordings by splitting into manageable chunks
- 🌏 **Multi-language Support**: Optimized for mixed Mandarin Chinese and English medical content
- ☁️ **Google Drive Integration**: Seamless file management with Google Drive
- 📁 **Organized Folder Structure**: Automatically organize processed files into structured folders
- 📝 **HackMD Integration**: Automatic upload of summaries to HackMD
- 📧 **Email Notifications**: Get notified when processing is complete
- 🔧 **Modular Architecture**: Clean, maintainable code structure
- 🛡️ **Comprehensive Error Handling**: Robust error handling throughout

## Project Structure

```
gemini-stt/
├── src/                    # Source code modules
│   ├── core/              # Core utilities and configuration
│   ├── audio/             # Audio and video processing
│   ├── transcription/     # Gemini API transcription
│   ├── storage/           # Google Drive and local storage
│   ├── summary/           # Summary generation and HackMD
│   └── notification/      # Email notifications
├── scripts/               # Utility scripts
├── tests/                 # Test files
├── logs/                  # Log files
├── working/              # Working directories
├── main.py               # Main entry point
├── setup.py              # Package setup
├── requirements.txt      # Dependencies
└── .env                  # Configuration (create from .env.example)
```

## Requirements

- Python 3.8 or higher (3.10-3.12 recommended)
- FFmpeg (for video/audio processing)
- Google Cloud service account
- Gemini API key

> **Note for Python 3.13+ users**: The `audioop` module was removed in Python 3.13. The pipeline includes compatibility workarounds, but for best performance, Python 3.10-3.12 is recommended.

## Installation

### Check Compatibility

```bash
python check_compatibility.py
```

### Windows Quick Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gemini-stt.git
cd gemini-stt
```

2. Run the setup script:
```bash
setup_windows.bat
```

This will:
- Create a virtual environment
- Install all dependencies
- Create necessary directories
- Set up your .env file

3. Install FFmpeg (required for video processing):
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add to your system PATH

### Manual Setup (All Platforms)

1. Create virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install FFmpeg:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`

4. Set up configuration:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

## Configuration

Create a `.env` file with the following variables:

```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key
HACKMD_TOKEN=your_hackmd_token  # Optional

# Google Drive Configuration
GDRIVE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
TO_BE_TRANSCRIBED_FOLDER_ID=folder_id_for_input_files
TRANSCRIBED_FOLDER_ID=folder_id_for_processed_files
PROCESSED_FOLDER_ID=folder_id_for_final_output

# Local Processing
PROCESS_VIDEOS=true
VIDEO_INPUT_DIR=C:\Users\yourname\Videos\to_process
AUDIO_INPUT_DIR=C:\Users\yourname\Videos\audio_only
PROCESS_LOCAL_AUDIO=true

# Google Drive Organization
ORGANIZE_TO_FOLDERS=true  # Create organized folder structure
UPLOAD_AUDIO_TO_DRIVE=false  # Skip audio files (usually too large)

# Audio Processing
CHUNK_DURATION_SECONDS=300
VIDEO_AUDIO_FORMAT=m4a
VIDEO_AUDIO_BITRATE=192k
VIDEO_AUDIO_SAMPLERATE=44100

# Email Configuration (Optional)
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
EMAIL_TO=recipient@example.com
```

## Usage

### Windows Batch Files

```bash
# Quick run with virtual environment
run.bat

# Extract audio from videos only
run_video_only.bat

# Manage pipeline state
manage_state.bat
```

### Command Line Usage

#### Full Pipeline

Process videos/audio with transcription, summary generation, and upload:

```bash
python main.py
```

#### Resume Capability

The pipeline automatically saves its state and can resume from where it left off:

```bash
# Resume from previous state (default)
python main.py

# Start fresh, ignoring previous state
python main.py --no-resume

# Show current pipeline state
python main.py --show-state

# Clear all state
python main.py --clear-state
```

#### Video Processing Only

Extract audio from videos without transcription:

```bash
python scripts/process_videos_only.py
```

### Priority Order

The pipeline prioritizes local files over Google Drive:
1. Check for video files in `VIDEO_INPUT_DIR`
2. Extract audio from videos to `AUDIO_INPUT_DIR`
3. Process existing audio files in `AUDIO_INPUT_DIR`
4. Only if no local files found, check Google Drive

### Resume Features

- **Automatic State Saving**: Every step saves progress
- **Skip Processed Files**: Won't reprocess completed files
- **Error Recovery**: Continue after fixing errors
- **Incremental Processing**: Add new files anytime

### Google Drive Folder Organization

When `ORGANIZE_TO_FOLDERS=true` (default), the pipeline automatically organizes processed files into structured folders:

```
Processed/
├── audio_file_1/
│   ├── audio_file_1.txt          # Raw transcript
│   ├── audio_file_1_parsed.txt   # Parsed transcript
│   └── audio_file_1.md           # Summary
└── audio_file_2/
    └── ...
```

Note: Audio files are not uploaded by default to save storage quota. They remain in the original location or can be moved separately.

Each audio file gets its own folder containing all related files, making it easy to:
- Find all files related to a specific recording
- Share complete sets of processed files
- Maintain organized archives
- Track processing history

**Automatic Local Fallback**: If Google Drive uploads fail (e.g., quota exceeded), the pipeline automatically creates the same folder structure locally in `working/organized_for_upload/`. You can then manually upload these folders to Google Drive or any other cloud storage when ready.

## API Documentation

### Core Modules

#### Config
```python
from src.core import Config

config = Config()  # Loads from .env
is_valid, errors = config.validate()
config.setup_directories()
```

#### Logger
```python
from src.core import Logger

logger = Logger("MyApp", log_file="app.log")
logger.info("Processing started")
logger.success("File processed")
logger.error("An error occurred")
```

### Audio Processing

#### VideoProcessor
```python
from src.audio import VideoProcessor

processor = VideoProcessor(audio_format="m4a")
results = processor.process_videos(
    input_dir=Path("/videos"),
    output_dir=Path("/audio"),
    move_to_processed=True
)
```

#### AudioProcessor
```python
from src.audio import AudioProcessor

processor = AudioProcessor(chunk_duration_seconds=300)
chunks = processor.split_audio_into_chunks(audio_path)
```

### Transcription

#### GeminiTranscriber
```python
from src.transcription import GeminiTranscriber

transcriber = GeminiTranscriber(api_key="...", chunk_duration_seconds=300)
transcript = transcriber.transcribe_audio_file(audio_path)
```

## Error Handling

The pipeline includes comprehensive error handling:

- **Configuration errors**: Validated at startup
- **Network errors**: Retries and graceful degradation
- **Processing errors**: Individual file failures don't stop the pipeline
- **Email notifications**: Automatic error notifications if configured

## Logging

Logs are written to:
- Console output with timestamps
- `logs/gemini_stt.log` file
- Email notifications for critical errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details