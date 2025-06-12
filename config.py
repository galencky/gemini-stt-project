# Audio transcription configuration

# Chunk duration in seconds (default: 5 minutes)
# Adjust this value if you need shorter or longer chunks
# Shorter chunks may help with transcription accuracy but will take longer overall
CHUNK_DURATION_SECONDS = 300  # 5 minutes

# Alternative chunk durations you might want to try:
# CHUNK_DURATION_SECONDS = 180  # 3 minutes
# CHUNK_DURATION_SECONDS = 600  # 10 minutes
# CHUNK_DURATION_SECONDS = 120  # 2 minutes

# Maximum file size for direct upload (MB)
MAX_FILE_SIZE_MB = 20

# Audio processing settings
AUDIO_SAMPLE_RATE = 16000  # 16kHz is good for speech
AUDIO_CHANNELS = 1  # Mono audio

# Silence removal settings (if you want to re-enable it)
SILENCE_REMOVAL_ENABLED = False
SILENCE_THRESHOLD_DB = -50  # Volume threshold for silence detection
SILENCE_MIN_DURATION = 1.0  # Minimum silence duration to remove (seconds)