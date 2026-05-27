"""Automatic lip-sync and A/V sync evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evaluation.quality_schema import clamp, metric, unavailable


def _lse_available(project_root: Path) -> tuple[bool, str]:
    score_script = project_root / "ml" / "Wav2Lip" / "evaluation" / "scores_LSE" / "calculate_scores_real_videos.py"
    model = project_root / "ml" / "Wav2Lip" / "evaluation" / "scores_LSE" / "data" / "syncnet_v2.model"
    return score_script.is_file() and model.is_file(), str(score_script)


def evaluate_sync(job_dir: Path, media: dict[str, Any], audio: dict[str, Any]) -> dict[str, Any]:
    project_root = job_dir.resolve()
    for parent in [job_dir.resolve(), *job_dir.resolve().parents]:
        if (parent / "backend").is_dir() and (parent / "evaluation").is_dir():
            project_root = parent
            break
    evaluator_available, evaluator_source = _lse_available(project_root)
    if evaluator_available:
        # The evaluator is intentionally not run inline because the historical
        # SyncNet script is heavyweight and needs prepared face crops/checkpoints.
        lse_note = "SyncNet LSE scripts and checkpoint were found, but automatic inline execution is not wired for this lightweight worker."
        lse_method = "unavailable"
    else:
        lse_note = "LSE evaluator script/checkpoint is not installed."
        lse_method = "not_installed"

    media_duration = float(media.get("duration_sec") or 0.0)
    tts_duration = float(audio.get("duration_sec") or 0.0)
    drift = abs(media_duration - tts_duration) if media_duration and tts_duration else None
    drift_ratio = drift / max(media_duration, tts_duration, 1.0) if drift is not None else 1.0
    stream_score = 1.0 if media.get("video_stream_exists") and media.get("audio_stream_exists") else 0.0
    drift_score = 1.0 - min(1.0, drift_ratio / 0.08)
    fps_score = 1.0 if float(media.get("fps") or 0.0) > 0.0 else 0.0
    duration_score = 1.0 if media_duration > 0.5 else 0.0
    sync_score = clamp((stream_score * 0.38) + (drift_score * 0.42) + (fps_score * 0.10) + (duration_score * 0.10))

    return {
        "display_label": "A/V sync quality",
        "score": metric(
            status="proxy_computed",
            value=round(sync_score * 100.0, 3),
            unit="percent",
            method="av_duration_stream_proxy",
            confidence="medium",
            source="ffprobe_media_and_tts_wav_duration",
            explanation="A/V sync proxy from final MP4 stream presence, duration drift, FPS, and generated WAV duration. This is not LSE-C/LSE-D.",
            reference_type="proxy",
            details={
                "final_mp4_duration_sec": media_duration or None,
                "tts_wav_duration_sec": tts_duration or None,
                "duration_drift_sec": round(drift, 6) if drift is not None else None,
                "duration_drift_ratio": round(drift_ratio, 6),
                "lse_evaluator_available": evaluator_available,
                "lse_evaluator_source": evaluator_source if evaluator_available else None,
            },
        ),
        "lse_c": unavailable(lse_method, lse_note, source=evaluator_source),
        "lse_d": unavailable(lse_method, lse_note, source=evaluator_source),
        "signals": {
            "video_stream_present": media.get("video_stream_exists"),
            "audio_stream_present": media.get("audio_stream_exists"),
            "fps": media.get("fps"),
            "final_mp4_duration_sec": media_duration or None,
            "tts_wav_duration_sec": tts_duration or None,
            "duration_drift_sec": round(drift, 6) if drift is not None else None,
        },
    }
