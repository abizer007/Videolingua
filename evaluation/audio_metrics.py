"""Audio metrics computed from generated WAV files and segment timing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from voice.audio_validation import AudioValidationError, analyze_audio


def compute_audio_metrics(
    wav_path: str | Path | None,
    *,
    source_segments: list[dict] | None = None,
    normalization_applied: bool | None = None,
) -> dict[str, Any]:
    if not wav_path:
        return {"status": "missing_artifact", "reason": "No TTS WAV path was found."}
    path = Path(wav_path)
    if not path.is_file():
        return {"status": "missing_artifact", "reason": f"TTS WAV does not exist: {path}"}
    try:
        stats = analyze_audio(path)
    except AudioValidationError as exc:
        return {"status": "error", "reason": str(exc), "path": str(path)}

    if normalization_applied is None:
        normalization_applied = bool(
            list(path.parent.glob(f"{path.stem}.sarvam_clean{path.suffix}"))
            or list(path.parent.glob(f"{path.stem}*.clean{path.suffix}"))
        )

    report: dict[str, Any] = {
        "status": "computed",
        "path": str(path),
        "duration_sec": round(stats.duration_s, 3),
        "sample_rate": stats.sample_rate,
        "channels": stats.channels,
        "peak": round(stats.peak, 6),
        "rms": round(stats.rms, 6),
        "silence_ratio": round(stats.silence_ratio, 6),
        "clipping_ratio": round(stats.clipping_ratio, 6),
        "loudness_proxy_dbfs": round(20.0 * __import__("math").log10(max(stats.rms, 1e-12)), 3),
        "normalization_applied": bool(normalization_applied),
        "validation_passed": True,
    }

    if source_segments:
        source_duration = max(
            (
                float(segment.get("end", 0.0))
                for segment in source_segments
                if isinstance(segment, dict)
            ),
            default=0.0,
        )
        if source_duration > 0:
            report["source_timeline_duration_sec"] = round(source_duration, 3)
            report["duration_drift_sec"] = round(stats.duration_s - source_duration, 3)
            report["duration_drift_ratio"] = round((stats.duration_s - source_duration) / source_duration, 6)

    return report

