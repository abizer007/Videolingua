"""Automatic speaker similarity evaluation."""

from __future__ import annotations

import audioop
import math
import wave
from pathlib import Path
from typing import Any

from evaluation.quality_schema import clamp, metric


SARVAM_LANGS = {"bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}
XTTS_LANGS = {"ar", "cs", "de", "en", "es", "fr", "hu", "it", "ja", "ko", "nl", "pl", "pt", "ru", "tr", "zh"}


def _voice_backend(operational: dict[str, Any], translation_data: dict[str, Any]) -> str:
    backend = str(operational.get("voice_backend") or "").strip()
    if backend:
        return backend
    language = str(translation_data.get("language") or "").lower().replace("_", "-").split("-")[0]
    if language in SARVAM_LANGS:
        return "Sarvam"
    if language in XTTS_LANGS:
        return "XTTS"
    return "configured router"


def _wav_features(path: Path) -> dict[str, float]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.getnframes()
        raw = wf.readframes(frames)
    if channels > 1:
        raw = audioop.tomono(raw, sample_width, 0.5, 0.5)
    rms = audioop.rms(raw, sample_width) / float(1 << (8 * sample_width - 1))
    peak = audioop.max(raw, sample_width) / float(1 << (8 * sample_width - 1))
    zcr = audioop.cross(raw, sample_width) / max(1, frames)
    duration = frames / float(sample_rate) if sample_rate else 0.0
    dbfs = 20.0 * math.log10(max(rms, 1e-12))
    return {"duration": duration, "rms": rms, "peak": peak, "zcr": zcr, "dbfs": dbfs, "sample_rate": float(sample_rate)}


def _similarity(reference: dict[str, float], generated: dict[str, float]) -> tuple[float, dict[str, float]]:
    dbfs_score = 1.0 - min(1.0, abs(reference["dbfs"] - generated["dbfs"]) / 35.0)
    peak_score = 1.0 - min(1.0, abs(reference["peak"] - generated["peak"]) / 1.0)
    zcr_score = 1.0 - min(1.0, abs(reference["zcr"] - generated["zcr"]) / max(reference["zcr"], generated["zcr"], 0.01))
    duration_score = 1.0 - min(1.0, abs(reference["duration"] - generated["duration"]) / max(reference["duration"], generated["duration"], 1.0))
    score = clamp((dbfs_score * 0.35) + (peak_score * 0.20) + (zcr_score * 0.30) + (duration_score * 0.15))
    return score, {
        "dbfs_score": round(dbfs_score, 6),
        "peak_score": round(peak_score, 6),
        "zero_crossing_score": round(zcr_score, 6),
        "duration_score": round(duration_score, 6),
        "reference_dbfs": round(reference["dbfs"], 3),
        "generated_dbfs": round(generated["dbfs"], 3),
    }


def evaluate_speaker(
    *,
    job_dir: Path,
    reference_audio: Path | None,
    generated_audio: Path | None,
    operational: dict[str, Any],
    translation_data: dict[str, Any],
) -> dict[str, Any]:
    backend = _voice_backend(operational, translation_data)
    if backend.lower().startswith("sarvam"):
        item = metric(
            status="not_applicable",
            value=None,
            unit="none",
            method="managed_tts_not_exact_voice_clone",
            confidence="high",
            source="voice_backend",
            explanation="Sarvam managed TTS does not preserve exact speaker identity, so speaker similarity is not applicable.",
            reference_type="not_applicable",
        )
        return {"display_label": "Speaker similarity", "score": item, "voice_similarity": item, "signals": {"voice_backend": backend}}

    if not reference_audio or not reference_audio.is_file() or not generated_audio or not generated_audio.is_file():
        item = metric(
            status="evaluator_not_installed",
            value=None,
            unit="none",
            method="speaker_embedding_or_reference_audio_required",
            confidence="none",
            source="reference_audio_and_generated_tts",
            explanation="No speaker embedding evaluator is installed, and reference/generated audio was not available for an acoustic proxy.",
            reference_type="unavailable",
        )
        return {"display_label": "Speaker similarity", "score": item, "voice_similarity": item, "signals": {"voice_backend": backend}}

    try:
        reference_features = _wav_features(reference_audio)
        generated_features = _wav_features(generated_audio)
        score, details = _similarity(reference_features, generated_features)
    except Exception as exc:
        item = metric(
            status="error",
            value=None,
            unit="none",
            method="weak_acoustic_similarity_proxy",
            confidence="low",
            source="reference_audio_and_generated_tts",
            explanation=f"Acoustic speaker proxy failed: {exc}",
            reference_type="proxy",
        )
        return {"display_label": "Speaker similarity", "score": item, "voice_similarity": item, "signals": {"voice_backend": backend}}

    item = metric(
        status="proxy_computed",
        value=round(score * 100.0, 3),
        unit="percent",
        method="weak_acoustic_similarity_proxy",
        confidence="low",
        source="reference_audio_and_generated_tts",
        explanation="Weak acoustic proxy comparing reference and generated WAV energy/peak/zero-crossing features. This is not speaker-embedding cosine similarity.",
        reference_type="proxy",
        details=details,
    )
    return {
        "display_label": "Speaker similarity",
        "score": item,
        "voice_similarity": item,
        "signals": {"voice_backend": backend, "reference_audio": str(reference_audio), "generated_audio": str(generated_audio), **details},
    }
