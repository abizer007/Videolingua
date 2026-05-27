"""Compatibility facade for generated audio validation."""

from voice.audio_validation import AudioStats, AudioValidationError, analyze_audio, validate_generated_audio

__all__ = ["AudioStats", "AudioValidationError", "analyze_audio", "validate_generated_audio"]

