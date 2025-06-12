# Gemini Speech-to-Text (STT) with Audio Chunking

A robust speech-to-text transcription system using Google's Gemini API, optimized for long audio files containing mixed Mandarin Chinese and Medical English content. Features automatic audio chunking for complete transcription of lengthy recordings.

## 🌟 Features

- **Automatic Audio Chunking**: Splits long audio files into 5-minute segments for reliable transcription
- **Multi-language Support**: Optimized for Traditional Mandarin Chinese (zh-tw) and Medical English terminology
- **Smart Processing**: Handles files up to several hours in length without missing content
- **Multiple Deployment Options**: Run locally or on Kaggle with Google Drive integration
- **Batch Processing**: Automatically processes multiple audio files
- **Format Support**: WAV, MP3, M4A, FLAC, OGG, AAC, WEBM
- **Progress Tracking**: Real-time status updates during chunk processing
- **Error Recovery**: Continues processing even if individual chunks fail

## 🚀 Quick Start

### Local Usage

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Install FFmpeg**:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

3. **Set up API key**:
Create a `.env` file:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

4. **Run transcription**:
```bash
# Place audio files in inbox/
python transcribe_audio.py
# Find transcripts in transcripts/
```

### Kaggle Usage

Use the provided `gemini-stt-on-kaggle.ipynb` notebook for cloud-based processing with Google Drive integration.

Required Kaggle secrets:
- `GEMINI_API_KEY`: Your Gemini API key
- `TO_BE_TRANSCRIBED`: Google Drive folder ID for input files
- `TRANSCRIBED`: Google Drive folder ID for processed audio
- `PROCESSED`: Google Drive folder ID for transcripts
- `GDRIVE_SA_JSON`: Google Drive service account JSON
- `HACKMD_TOKEN`: (Optional) For uploading summaries to HackMD
- `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_TO`: (Optional) For email notifications

## 📁 Directory Structure

```
gemini-stt/
├── inbox/              # Place audio files here
├── transcribed/        # Processed audio files (moved here after transcription)
├── transcripts/        # Generated transcription files
├── transcribe_audio.py # Main transcription script
├── config.py          # Configuration settings
├── gemini-stt-on-kaggle.ipynb  # Kaggle notebook version
└── README.md
```

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Chunk duration (default: 5 minutes)
CHUNK_DURATION_SECONDS = 300

# Audio settings
AUDIO_SAMPLE_RATE = 16000  # 16kHz for speech
AUDIO_CHANNELS = 1         # Mono audio

# File size limits
MAX_FILE_SIZE_MB = 20
```

## 🔧 How It Works

1. **Audio Analysis**: Detects audio duration using FFprobe/PyDub
2. **Smart Chunking**: 
   - Files < 5 minutes: Processed as-is
   - Files > 5 minutes: Split into 5-minute chunks
3. **Chunk Transcription**: Each chunk is transcribed separately with context
4. **Intelligent Merging**: Chunks are combined with timestamps for reference
5. **Quality Assurance**: Prompts ensure complete transcription without gaps

### Example Output

```
[00:00:00.000]
對不起對不起，這樣有人有聽到嗎？那有人知道我剛剛講話...

[00:05:00.000]
好像是誒。好棒哦英文裡面當有人難過...
```

## 🌐 Kaggle Notebook Features

The Kaggle notebook adds:
- **Google Drive Integration**: Automatic file sync
- **Transcript Parsing**: Groups content into 5-minute blocks
- **Summary Generation**: Uses Gemini to create summaries
- **HackMD Upload**: Publishes summaries online
- **Email Notifications**: Sends links when complete

## 📝 Transcription Prompts

The system uses specialized prompts for medical content:
- Preserves medical terminology in original language
- Handles code-switching between languages
- Maintains speaker changes when distinguishable
- Ensures complete transcription without summarization

## 🛠️ Troubleshooting

### Blank Transcriptions
- Check console for chunk processing errors
- Verify audio contains speech content
- Try shorter chunk durations (edit `CHUNK_DURATION_SECONDS`)

### FFmpeg Errors
- Ensure FFmpeg is installed: `ffmpeg -version`
- Check audio file isn't corrupted
- Try converting to WAV format first

### API Errors
- Verify your Gemini API key is valid
- Check API quotas and limits
- Ensure internet connectivity

## 🔒 Privacy & Security

- Audio files are processed locally (or in your Kaggle environment)
- Only transcriptions are sent to Gemini API
- Use `.gitignore` to exclude sensitive files from version control
- API keys are stored in environment variables

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- Google Gemini API for powerful speech recognition
- FFmpeg for audio processing capabilities
- The medical transcription community for testing and feedback

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review debug instructions in `DEBUG_INSTRUCTIONS.md`