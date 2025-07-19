# Project Structure

```
gemini-stt/
├── data/                     # Runtime data directories
│   ├── inbox/               # Input audio files
│   ├── transcripts/         # Raw transcriptions
│   ├── parsed/              # Parsed transcripts
│   ├── markdown/            # Summarized markdown files
│   └── uploaded/            # Files uploaded to HackMD
│
├── scripts/                 # Utility scripts and batch files
│   ├── batch/              # Less-used batch files
│   └── utilities/          # Python utility scripts
│
├── src/                     # Source code
│   ├── integrations/       # External service integrations
│   │   ├── google_drive.py
│   │   ├── hackmd_uploader.py
│   │   └── email_sender.py
│   │
│   ├── processors/         # Core processing modules
│   │   ├── audio_processor.py
│   │   ├── video_processor.py
│   │   ├── gemini_transcriber.py
│   │   ├── transcript_parser.py
│   │   └── summarizer.py
│   │
│   └── utils/              # Utility modules
│       ├── config.py       # Configuration management
│       └── pipeline_state.py # State tracking
│
├── main.py                  # Main pipeline script
├── setup_windows.bat        # Environment setup
├── run_with_venv.bat       # Run pipeline with resume
├── organize_files.bat      # Organize files for upload
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── gemini-stt-on-kaggle.ipynb # Original notebook
```

## Key Scripts

- **main.py** - Smart pipeline that tracks state and can resume
- **run_with_venv.bat** - Quick way to run the pipeline with virtual environment
- **organize_files.bat** - Prepare processed files for manual Google Drive upload
- **setup_windows.bat** - Initial setup for Windows users