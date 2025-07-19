# Gemini STT - Quick Start Guide

## 🚀 First Time Setup (Windows)

1. **Run setup**:
   ```cmd
   setup.cmd
   ```

2. **Configure** - Edit `.env` file with your:
   - Gemini API key
   - Google Drive service account JSON
   - Folder IDs

3. **Test setup**:
   ```cmd
   bin\diagnose.bat
   ```

## 📁 Daily Usage

### Process Everything (Local + Google Drive)
```cmd
run.cmd
```
Or:
```cmd
python main.py
```

### Process Videos Only
```cmd
bin\run_video_only.bat
```

### Check Progress
```cmd
python main.py --show-state
```

### Manage Pipeline State
```cmd
bin\manage_state.bat
```

## 🔧 Troubleshooting

### Test imports and compatibility:
```cmd
python tools\test_imports.py
python tools\check_compatibility.py
```

### Retry failed Google Drive uploads:
```cmd
python tools\retry_failed.py --sync
```

### Clear state and start fresh:
```cmd
python main.py --clear-state
python main.py --no-resume
```

## 📂 Where to Find Output

- **Transcripts**: `working\transcription\`
- **Summaries**: `working\markdown\`
- **Logs**: `logs\gemini_stt.log`
- **State**: `working\pipeline_state.json`
- **Organized folders** (if Drive upload fails): `working\organized_for_upload\`

## 🎯 Common Tasks

### Add new audio/video files:
1. Place videos in: `C:\Users\yourname\Videos\audio_strip`
2. Or audio in: `C:\Users\yourname\Videos\audio_strip\audio_only`
3. Run: `run.cmd`

### Process from Google Drive:
1. Upload audio to your Google Drive folder
2. Run: `run.cmd`
3. Files will be moved to "transcribed" folder when done

### Resume after interruption:
Just run again - the pipeline automatically resumes:
```cmd
run.cmd
```

### If Google Drive uploads fail (quota exceeded):
1. Check `working\organized_for_upload\` for local folders
2. Open the folder: `bin\open_organized_folders.bat`
3. Manually upload these folders to Google Drive or other storage

## ⚡ Pro Tips

- Pipeline saves state after each step
- Already processed files are skipped
- Failed uploads can be retried without re-processing
- Check `bin\diagnose.bat` if something seems wrong
- Python 3.10-3.12 recommended (3.13+ has warnings)