# Project Structure

## Directory Layout

```
gemini-stt/
│
├── bin/                    # Executable scripts and batch files
│   ├── diagnose.bat       # System diagnostics
│   ├── manage_state.bat   # Pipeline state management
│   ├── run.bat           # Run main pipeline
│   ├── run_video_only.bat # Process videos only
│   └── setup_windows.bat  # Windows setup script
│
├── src/                   # Source code modules
│   ├── audio/            # Audio and video processing
│   ├── core/             # Core utilities and configuration
│   ├── notification/     # Email notifications
│   ├── storage/          # Google Drive and local storage
│   ├── summary/          # Summary generation and HackMD
│   └── transcription/    # Gemini API transcription
│
├── scripts/              # Standalone scripts
│   └── process_videos_only.py
│
├── tools/                # Utility and diagnostic tools
│   ├── check_compatibility.py
│   ├── retry_failed.py
│   ├── test_imports.py
│   └── update_batch_files.py
│
├── docs/                 # Documentation (if any)
├── tests/                # Test files
├── logs/                 # Log files (auto-created)
├── working/              # Working directories (auto-created)
└── archive/              # Old/deprecated files
```

## Key Files in Root

- `main.py` - Main entry point for the pipeline
- `setup.py` - Python package setup
- `requirements.txt` - Python dependencies
- `.env` - Configuration (create from .env.example)
- `.env.example` - Example configuration
- `README.md` - Main documentation
- `run.cmd` - Quick launcher for Windows
- `setup.cmd` - Quick setup for Windows

## Quick Start

1. **Setup**: Run `setup.cmd` or `bin\setup_windows.bat`
2. **Configure**: Copy `.env.example` to `.env` and add your API keys
3. **Run**: Execute `run.cmd` or `python main.py`

## Working Directories

Created automatically during runtime:

- `working/from_google_drive/` - Downloaded audio files
- `working/transcription/` - Raw transcripts
- `working/parsed/` - Parsed transcripts
- `working/markdown/` - Generated summaries
- `working/uploaded/` - Files uploaded to HackMD
- `working/organized_for_upload/` - Local organized folders (fallback for Drive quota issues)
- `logs/` - Application logs