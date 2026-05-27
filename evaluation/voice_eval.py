"""Automatic voice quality and MOS-like evaluation."""

from __future__ import annotations

from typing import Any

from evaluation.quality_schema import clamp, metric


def _score_from_audio(audio: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    clipping = float(audio.get("clipping_ratio") or 0.0)
    silence = float(audio.get("silence_ratio") or 1.0)
    peak = float(audio.get("peak") or 0.0)
    rms = float(audio.get("rms") or 0.0)
    drift_ratio = abs(float(audio.get("duration_drift_ratio") or 0.0))
    sample_rate = int(audio.get("sample_rate") or 0)
    duration = float(audio.get("duration_sec") or 0.0)
    loudness_dbfs = float(audio.get("loudness_proxy_dbfs") or -80.0)

    clipping_score = 1.0 - min(1.0, clipping * 250.0)
    silence_score = 1.0 - min(1.0, max(0.0, silence - 0.42) / 0.58)
    peak_score = 1.0 - min(1.0, max(0.0, peak - 0.98) / 0.02)
    rms_score = clamp(1.0 - (abs(loudness_dbfs + 18.0) / 32.0))
    drift_score = 1.0 - min(1.0, drift_ratio / 0.20)
    sample_rate_score = 1.0 if sample_rate >= 22050 else 0.65 if sample_rate else 0.0
    duration_score = 1.0 if duration > 0.5 and rms > 0 else 0.0
    score = clamp(
        (clipping_score * 0.20)
        + (silence_score * 0.18)
        + (peak_score * 0.12)
        + (rms_score * 0.18)
        + (drift_score * 0.17)
        + (sample_rate_score * 0.08)
        + (duration_score * 0.07)
    )
    return score, {
        "clipping_score": round(clipping_score, 6),
        "silence_score": round(silence_score, 6),
        "peak_score": round(peak_score, 6),
        "rms_score": round(rms_score, 6),
        "duration_drift_score": round(drift_score, 6),
        "sample_rate_score": round(sample_rate_score, 6),
        "duration_score": round(duration_score, 6),
    }


def evaluate_voice(audio: dict[str, Any], human_quality: dict[str, Any] | None = None) -> dict[str, Any]:
    human_quality = human_quality or {}
    if human_quality.get("human_mos_rating") is not None:
        value = float(human_quality["human_mos_rating"])
        return {
            "display_label": "Human MOS",
            "score": metric(status="computed", value=round((value - 1.0) / 4.0 * 100.0, 3), unit="percent", method="human_mos_rating", confidence="high", source="evaluation_human_quality", explanation="Score derived from a human MOS rating supplied in the expert reference section.", reference_type="true_reference"),
            "mos": metric(status="computed", value=round(value, 3), unit="mos_1_5", method="human_mos_rating", confidence="high", source="evaluation_human_quality", explanation="Human-provided MOS rating.", reference_type="true_reference"),
            "naturalness_score": metric(status="computed", value=round((value - 1.0) / 4.0 * 100.0, 3), unit="percent", method="human_mos_rating", confidence="high", source="evaluation_human_quality", explanation="Naturalness score derived from human MOS.", reference_type="true_reference"),
            "signals": {},
        }

    if audio.get("status") != "computed":
        explanation = str(audio.get("reason") or "No generated WAV was available for voice quality analysis.")
        missing = metric(status="missing_artifact", value=None, unit="none", method="audio_artifact_required", confidence="none", source="tts_wav", explanation=explanation, reference_type="unavailable")
        return {"display_label": "Voice naturalness", "score": missing, "mos": missing, "naturalness_score": missing, "signals": {}}

    score, signals = _score_from_audio(audio)
    mos_proxy = 1.0 + (4.0 * score)
    return {
        "display_label": "Voice naturalness proxy",
        "score": metric(
            status="proxy_computed",
            value=round(score * 100.0, 3),
            unit="percent",
            method="audio_naturalness_proxy",
            confidence="medium",
            source="tts_wav_audio_signals",
            explanation="Automatic audio-quality proxy from clipping, silence, loudness, sample rate, and duration drift. This is not human MOS.",
            reference_type="proxy",
            details=signals,
        ),
        "mos": metric(
            status="proxy_computed",
            value=round(mos_proxy, 3),
            unit="mos_1_5",
            method="audio_naturalness_proxy",
            confidence="medium",
            source="tts_wav_audio_signals",
            explanation="MOS-like value converted from the audio naturalness proxy; it is not a human MOS rating.",
            reference_type="proxy",
        ),
        "naturalness_score": metric(
            status="proxy_computed",
            value=round(score * 100.0, 3),
            unit="percent",
            method="audio_naturalness_proxy",
            confidence="medium",
            source="tts_wav_audio_signals",
            explanation="Audio naturalness proxy, not a speech-quality evaluator model.",
            reference_type="proxy",
        ),
        "signals": {key: audio.get(key) for key in ("duration_sec", "sample_rate", "channels", "peak", "rms", "silence_ratio", "clipping_ratio", "duration_drift_ratio", "normalization_applied")},
    }
