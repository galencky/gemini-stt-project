"""Custom exceptions for Gemini STT."""


class GeminiSTTError(Exception):
    """Base exception for all Gemini STT errors."""
    pass


class AudioProcessingError(GeminiSTTError):
    """Error in audio processing operations."""
    pass


class TranscriptionError(GeminiSTTError):
    """Error in transcription operations."""
    pass


class StorageError(GeminiSTTError):
    """Error in storage operations (Google Drive, local files)."""
    pass


class NetworkError(GeminiSTTError):
    """Error in network operations."""
    pass


class ConfigurationError(GeminiSTTError):
    """Error in configuration."""
    pass


class AuthenticationError(GeminiSTTError):
    """Error in authentication."""
    pass