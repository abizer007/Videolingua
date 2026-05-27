"""Compatibility facade for reference audio validation."""

from voice.audio_validation import AudioStats, AudioValidationError, validate_reference_audio
from voice.reference_audio import ReferenceAudioError, prepare_reference_audio

__all__ = [
    "AudioStats",
    "AudioValidationError",
    "ReferenceAudioError",
    "prepare_reference_audio",
    "validate_reference_audio",
]

