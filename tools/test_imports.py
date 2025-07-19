#!/usr/bin/env python3
"""Test imports and basic functionality."""

print("Testing Gemini STT imports...")

try:
    print("1. Testing audio compatibility...")
    from src.core.audio_compat import setup_audio_compatibility
    print("   ✓ Audio compatibility loaded")
except Exception as e:
    print(f"   ✗ Error: {e}")

try:
    print("2. Testing core modules...")
    from src.core import Config, PipelineState
    from src.core.logger import logger
    from src.core.exceptions import GeminiSTTError
    print("   ✓ Core modules loaded")
except Exception as e:
    print(f"   ✗ Error: {e}")

try:
    print("3. Testing logger...")
    logger.info("Test info message")
    logger.success("Test success message")
    logger.error("Test error message")
    logger.warning("Test warning message")
    print("   ✓ Logger working")
except Exception as e:
    print(f"   ✗ Error: {e}")

try:
    print("4. Testing configuration...")
    config = Config()
    print("   ✓ Configuration loaded")
    print(f"   - Working directory: {config.working_dir}")
except Exception as e:
    print(f"   ✗ Error: {e}")

try:
    print("5. Testing audio modules...")
    from src.audio import AudioProcessor, VideoProcessor
    print("   ✓ Audio modules loaded")
except Exception as e:
    print(f"   ✗ Error: {e}")

try:
    print("6. Testing other modules...")
    from src.transcription import GeminiTranscriber
    from src.storage import GoogleDriveManager
    from src.summary import SummaryGenerator
    print("   ✓ All modules loaded successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\nImport test complete!")