"""Reference audio preparation for XTTS speaker cloning."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .audio_validation import AudioStats, AudioValidationError, validate_reference_audio


class ReferenceAudioError(RuntimeError):
    """Raised when a speaker reference cannot be prepared safely."""


def prepare_reference_audio(
    reference_audio_path: str | Path,
    *,
    intermediate_dir: str | Path = "outputs/intermediate",
    output_name: str = "reference_clean.wav",
    sample_rate: int = 24000,
    min_duration_s: float = 6.0,
    max_duration_s: float = 60.0,
) -> tuple[Path, AudioStats]:
    """
    Convert a user/source reference into a conservative WAV for XTTS.

    This intentionally avoids aggressive denoising or loudness normalization because
    those can erase speaker identity. It only decodes, converts to mono PCM WAV,
    resamples, and validates the result.
    """
    source = Path(reference_audio_path)
    if not source.is_file():
        raise ReferenceAudioError(f"Speaker reference audio is missing: {source}")
    if source.stat().st_size <= 44:
        raise ReferenceAudioError(f"Speaker reference audio is empty: {source}")

    # Validate the source before conversion so corrupted or silent input fails early.
    try:
        validate_reference_audio(
            source,
            min_duration_s=min_duration_s,
            max_duration_s=max_duration_s,
        )
    except AudioValidationError as exc:
        raise ReferenceAudioError(str(exc)) from exc

    out_dir = Path(intermediate_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned = out_dir / output_name

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        str(cleaned),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not cleaned.is_file():
        raise ReferenceAudioError(
            f"Could not convert speaker reference to WAV: {result.stderr or result.stdout}"
        )

    try:
        stats = validate_reference_audio(
            cleaned,
            min_duration_s=min_duration_s,
            max_duration_s=max_duration_s,
        )
    except AudioValidationError as exc:
        raise ReferenceAudioError(f"Cleaned speaker reference failed validation: {exc}") from exc

    return cleaned, stats
