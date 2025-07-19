# Gemini Speech-to-Text Pipeline

A Python application for transcribing audio files using Google's Gemini API with automatic chunking for long recordings. Designed for medical audio with mixed Mandarin Chinese and English content.

## Features

- **Video to Audio Extraction**: Automatically extract audio from screen recordings and video files
- **Automatic Audio Chunking**: Splits long audio files into 5-minute chunks for optimal transcription
- **Multi-language Support**: Handles mixed Mandarin Chinese and English medical terminology
- **Google Drive Integration**: Automatically downloads audio files and uploads results
- **Transcript Processing**: Parses transcripts into readable time-stamped blocks
- **AI Summarization**: Generates summaries using Gemini 2.0 Flash
- **HackMD Integration**: Uploads summaries to HackMD for easy sharing
- **Email Notifications**: Sends links to uploaded summaries via email

## Prerequisites

- Python 3.8 or higher
- FFmpeg (for audio processing with pydub)
- Google Cloud Service Account with Drive API access
- Gemini API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gemini-stt.git
cd gemini-stt
```

2. Run the setup script:
```bash
python setup.py
```

This will:
- Check Python version (3.8+ required)
- Verify FFmpeg installation
- Install Python dependencies
- Create necessary directories
- Check for .env configuration

3. Configure environment variables:
```bash
cp .env.example .env
```

4. Edit `.env` file with your credentials:
   - `GEMINI_API_KEY`: Your Gemini API key
   - `GDRIVE_SERVICE_ACCOUNT_JSON`: Your service account JSON (see below)
   - Google Drive folder IDs for audio management
   - Optional: HackMD token and email credentials

   **For Google Drive service account**, you can either:
   - Paste the entire JSON content directly in the .env file (recommended)
   - Provide a path to the JSON file

   Example with JSON content:
   ```
   GDRIVE_SERVICE_ACCOUNT_JSON={"type": "service_account", "project_id": "..."}
   ```

5. Test your configuration:
```bash
python test_apis.py
```

This will verify:
- Gemini API connection
- Google Drive API access
- HackMD API (if configured)

## Usage

Run the main script:
```bash
python main.py
```

The script will:
1. Process local video files and extract audio (if enabled)
2. Download audio files from Google Drive
3. Transcribe all audio using Gemini (with automatic chunking)
4. Parse the transcripts
5. Generate summaries
6. Upload to HackMD (if configured)
7. Send email notifications (if configured)
8. Upload results back to Google Drive

### Video Processing

To enable video processing for screen recordings:

1. Set `PROCESS_VIDEOS=true` in your `.env` file
2. Set `VIDEO_INPUT_DIR` to the directory containing your video files
3. The script will:
   - Extract audio from all video files in the directory
   - Move processed videos to a `processed_videos` subfolder
   - Add extracted audio to the transcription pipeline

Supported video formats: MP4, AVI, MOV, MKV, FLV, WMV, WEBM, M4V, MPG, MPEG

## Project Structure

```
gemini-stt/
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── README.md                    # This file
├── src/                         # Source code
│   ├── __init__.py
│   ├── processors/              # Processing modules
│   │   ├── __init__.py
│   │   ├── audio_processor.py   # Audio chunking and processing
│   │   ├── video_processor.py   # Video to audio extraction
│   │   ├── gemini_transcriber.py # Gemini API transcription
│   │   ├── transcript_parser.py # Transcript parsing
│   │   └── summarizer.py        # Summary generation
│   ├── integrations/            # External service integrations
│   │   ├── __init__.py
│   │   ├── google_drive.py      # Google Drive operations
│   │   ├── hackmd_uploader.py   # HackMD integration
│   │   └── email_sender.py      # Email notifications
│   └── utils/                   # Utility modules
│       ├── __init__.py
│       └── config.py            # Configuration management
└── data/                        # Working directories
    ├── inbox/                   # Downloaded/extracted audio files
    ├── transcripts/             # Raw transcriptions
    ├── parsed/                  # Parsed transcripts
    ├── markdown/                # Generated summaries
    └── uploaded/                # Processed files
```

## Configuration

### Required Environment Variables

- `GEMINI_API_KEY`: Your Gemini API key
- `GDRIVE_SERVICE_ACCOUNT_JSON`: Service account JSON content or file path
- `TO_BE_TRANSCRIBED_FOLDER_ID`: Google Drive folder with audio files
- `TRANSCRIBED_FOLDER_ID`: Archive folder for processed audio
- `PROCESSED_FOLDER_ID`: Folder for transcription results

### Optional Environment Variables

- `SYSTEM_PROMPT_DOC_ID`: Google Doc ID with summary prompt
- `HACKMD_TOKEN`: HackMD API token for uploading summaries
- `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_TO`: Email configuration
- `CHUNK_DURATION_SECONDS`: Audio chunk duration (default: 300)
- `DELETE_LOCAL_FILES_AFTER_UPLOAD`: Delete local files after successful upload (default: false)

### Video Processing Variables

- `PROCESS_VIDEOS`: Enable video processing (true/false, default: false)
- `VIDEO_INPUT_DIR`: Directory containing video files to process
- `VIDEO_AUDIO_FORMAT`: Audio format for extraction (default: m4a)
- `VIDEO_AUDIO_BITRATE`: Audio bitrate (default: 192k)
- `VIDEO_AUDIO_SAMPLERATE`: Sample rate (default: 44100)

## Google Drive Setup

1. Create a service account in Google Cloud Console
2. Enable Google Drive API
3. Share the required folders with the service account email
4. Download the service account JSON key file

## Troubleshooting

- **FFmpeg not found**: Ensure FFmpeg is installed and in your PATH
- **Google Drive access denied**: Check folder permissions and service account access
- **Gemini API errors**: Verify your API key and check rate limits
- **Audio processing errors**: Ensure audio files are in supported formats

## License

This project is licensed under the MIT License.