"""Thin IndicF5 service wrapper.

The API/TTS process does not import IndicF5 model code directly. Real synthesis
is delegated to voice.engines.indicf5_engine, which runs the isolated worker.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from voice.base import VoiceSynthesisRequest, indicf5_supports_language, normalize_voice_language
from voice.engines.indicf5_engine import IndicF5Engine


SUPPORTED_LANGS = {"as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}


def supports_language(language_code: str) -> bool:
    return indicf5_supports_language(language_code)


def synthesize_to_wav(
    text: str,
    output_path: Path,
    voice_options: Optional[dict] = None,
    voice_id: Optional[str] = None,
    speaker_wav: Optional[str] = None,
    language_code: str = "hi",
    ref_text: Optional[str] = None,
) -> Path:
    language = normalize_voice_language(language_code)
    if not supports_language(language):
        raise RuntimeError(f"IndicF5 does not support language '{language_code}'")
    if not speaker_wav:
        raise RuntimeError("IndicF5 requires a valid speaker_wav reference")
    if not (ref_text or "").strip():
        raise RuntimeError("IndicF5 requires the exact transcript of the reference audio")

    request = VoiceSynthesisRequest(
        text=text,
        target_language=language,
        output_path=Path(output_path),
        reference_audio_path=Path(speaker_wav),
        reference_text=ref_text,
        preferred_engine="indicf5",
        cloning_required=True,
        allow_generic_fallback=False,
    )
    return IndicF5Engine().synthesize(request).output_path
