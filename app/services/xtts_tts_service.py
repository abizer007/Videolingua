"""Coqui XTTSv2 voice cloning service.

This module is intentionally strict: when XTTS cloning is requested, a real
speaker WAV must be provided and passed to Coqui as `speaker_wav`. Generic or
default-speaker synthesis is not allowed here.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

from voice.audio_validation import file_sha256
from voice.xtts_cloner import (
    DEFAULT_XTTS_MAX_CHARS,
    XTTS_V2_MODEL,
    VoiceCloneConfig,
    VoiceCloningError,
    build_voice_cache_key,
    clone_voice,
    config_from_env,
    split_text_for_xtts,
)

logger = logging.getLogger(__name__)

_XTTS_MODEL_NAME = os.environ.get("VIDIOLINGUA_XTTS_MODEL", XTTS_V2_MODEL)
_XTTS_MAX_CHARS = int(os.environ.get("VIDIOLINGUA_XTTS_MAX_CHARS", str(DEFAULT_XTTS_MAX_CHARS)))


def _split_into_chunks(text: str, max_chars: int = _XTTS_MAX_CHARS) -> list[str]:
    """Compatibility wrapper used by existing verification scripts."""
    return split_text_for_xtts(text, max_chars)


def _write_silence(output_path: Path, duration_s: float = 0.1, sample_rate: int = 24000) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.zeros(int(sample_rate * duration_s), dtype=np.float32)
    try:
        import soundfile as sf

        sf.write(str(output_path), samples, sample_rate, subtype="PCM_16")
        return
    except ImportError:
        pass

    import wave

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((samples * 32767).astype("<i2").tobytes())


def _resolve_required_speaker_wav(speaker_wav: Optional[str]) -> str:
    candidates = [
        speaker_wav,
        os.environ.get("SPEAKER_REFERENCE_AUDIO"),
        os.environ.get("VIDIOLINGUA_VOICE_SAMPLE"),
    ]
    for candidate in candidates:
        path = (candidate or "").strip()
        if path:
            if Path(path).is_file():
                return path
            raise VoiceCloningError(f"Configured speaker reference does not exist: {path}")
    raise VoiceCloningError(
        "XTTS voice cloning requires SPEAKER_REFERENCE_AUDIO or VIDIOLINGUA_VOICE_SAMPLE"
    )


def synthesize_to_wav(
    text: str,
    output_path: Path,
    voice_options: Optional[dict] = None,
    voice_id: Optional[str] = None,
    speaker_wav: Optional[str] = None,
    language_code: str = "en",
) -> Path:
    """
    Synthesize speech with Coqui XTTSv2 using a required reference speaker WAV.

    Raises `VoiceCloningError` on missing/bad reference audio, model load
    failure, speaker conditioning failure, invalid generated audio, or forbidden
    fallback configuration.
    """
    del voice_id
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not text or not text.strip():
        _write_silence(output_path)
        return output_path

    reference = _resolve_required_speaker_wav(speaker_wav)
    config = config_from_env(language_code)
    config.model_name = os.environ.get("VIDIOLINGUA_XTTS_MODEL", config.model_name)

    if voice_options and voice_options.get("cloned") is False and config.voice_cloning_required:
        logger.warning("voice_options.cloned=false ignored because XTTS cloning is required")

    logger.info("XTTS clone reference path: %s", reference)
    logger.info("XTTS clone reference sha256: %s", file_sha256(reference))
    logger.info(
        "XTTS service settings: model=%s model_path=%s language=%s temperature=%s repetition_penalty=%s max_chars=%s sample_rate=%s crossfade_ms=%s device=%s",
        config.model_name,
        config.model_path,
        config.language,
        config.temperature,
        config.repetition_penalty,
        config.max_chars,
        config.sample_rate,
        config.crossfade_ms,
        config.device,
    )

    result = clone_voice(
        text=text,
        reference_audio_path=reference,
        output_path=output_path,
        language=language_code,
        config=config,
    )

    logger.info(
        "XTTS clone complete: output=%s raw=%s clean=%s model=%s language=%s speaker_wav_used=%s fallback=%s cache_key=%s",
        result.output_path,
        result.raw_xtts_path,
        result.clean_xtts_path,
        result.model_name,
        result.language,
        result.speaker_wav_used,
        result.fallback_attempted,
        result.cache_key,
    )
    return output_path


__all__ = [
    "VoiceCloneConfig",
    "VoiceCloningError",
    "XTTS_V2_MODEL",
    "build_voice_cache_key",
    "synthesize_to_wav",
    "_split_into_chunks",
]
