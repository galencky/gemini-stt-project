# Debugging Blank Transcriptions

If you're getting blank transcriptions, try the following:

## 1. Skip Silence Removal (Recommended First Step)
Set the environment variable to skip silence removal:
```bash
export SKIP_SILENCE_REMOVAL=true
python transcribe_audio.py
```

## 2. Check FFmpeg Installation
Ensure ffmpeg is properly installed:
```bash
ffmpeg -version
```

## 3. Manual Testing
Test the silence removal manually:
```bash
# Test with less aggressive settings
ffmpeg -i inbox/your_audio.mp3 -af "silenceremove=start_periods=1:start_duration=1:start_threshold=-50dB:stop_periods=-1:stop_duration=1:stop_threshold=-50dB:detection=peak:window=0.05" -acodec pcm_s16le -ar 16000 test_output.wav

# Check the output file size
ls -la test_output.wav
```

## 4. Changes Made to Fix the Issue:

### Less Aggressive Silence Removal:
- Changed threshold from -30dB to -50dB (more lenient)
- Changed minimum silence duration from 0.1s to 1s (only removes longer pauses)
- Added file size checking to detect if output is too small

### Debug Features Added:
- File size comparison logging
- FFmpeg command logging
- Input file info logging
- Option to skip silence removal entirely

### Environment Variable:
- `SKIP_SILENCE_REMOVAL=true` - Skip silence removal and use original audio

## 5. If Still Having Issues:
1. Check the console output for error messages
2. Verify your audio file is not corrupted
3. Try with a different audio format
4. Ensure the audio file actually contains speech