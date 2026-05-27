"""HuBERT prosody adapter inference and report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prosody.adapter_model import cosine_similarity, load_adapter
from prosody.adapter_train import _duration_similarity, _load_embedding, _profile_for_audio, _scalar_similarity
from voice.hubert_prosody import DEFAULT_MODEL, extract_hubert_features
from voice.speech_rate import rate_similarity


def _first(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.is_file()), None)


def _discover_job(job_dir: Path) -> dict[str, Path | None]:
    return {
        "source_video": _first([job_dir / "results" / "input_video.mp4", *sorted((job_dir / "asr" / "input").glob("*.mp4"))]),
        "asr_json": _first(sorted((job_dir / "asr" / "output").glob("*.json"))),
        "tts_wav": _first(sorted((job_dir / "tts" / "output").glob("*.wav"))),
    }


def build_prosody_validation_report(
    *,
    source_profile: dict[str, Any],
    tts_profile: dict[str, Any],
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    source_global = source_profile.get("global") if isinstance(source_profile.get("global"), dict) else {}
    tts_global = tts_profile.get("global") if isinstance(tts_profile.get("global"), dict) else {}
    duration_drift = None
    if source_global.get("speech_duration_sec") is not None and tts_global.get("speech_duration_sec") is not None:
        duration_drift = round(float(tts_global["speech_duration_sec"]) - float(source_global["speech_duration_sec"]), 3)
    pause_score = _scalar_similarity(source_global.get("pause_count"), tts_global.get("pause_count"))
    report = {
        "schema_version": 1,
        "status": "computed",
        "engine": "Prosody & Elocution Engine",
        "global": {
            "source_speech_rate_wpm": source_global.get("speech_rate_wpm"),
            "dub_speech_rate_wpm": tts_global.get("speech_rate_wpm"),
            "speech_rate_similarity": rate_similarity(source_global.get("speech_rate_wpm"), tts_global.get("speech_rate_wpm")),
            "source_pause_count": source_global.get("pause_count"),
            "dub_pause_count": tts_global.get("pause_count"),
            "pause_preservation_proxy": round(pause_score * 100.0, 3) if pause_score is not None else None,
            "duration_drift_sec": duration_drift,
        },
        "warnings": [],
        "errors": [],
        "note": "Prosody validation is a measurable proxy, not exact emotion transfer.",
    }
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def validate_adapter_for_job(
    job_dir: str | Path,
    adapter_dir: str | Path,
    output_path: str | Path,
    *,
    model_name: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    job = Path(job_dir)
    output = Path(output_path)
    work = output.parent / "hubert_adapter_validation_features" / job.name
    paths = _discover_job(job)
    warnings: list[str] = []
    errors: list[str] = []
    if not paths["source_video"] or not paths["asr_json"] or not paths["tts_wav"]:
        report = {
            "status": "unavailable",
            "hubert_model": model_name,
            "adapter_path": str(adapter_dir),
            "adapter_status": "missing_inputs",
            "global": {"prosody_similarity_score_0_100": None, "embedding_cosine_similarity": None, "confidence": "low"},
            "segments": [],
            "warnings": ["Missing source video, ASR JSON, or dubbed WAV."],
            "errors": [],
            "note": "HuBERT-guided similarity, not exact emotion transfer.",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report
    source_profile = _profile_for_audio(paths["source_video"], paths["asr_json"], work / "source_profile.json")
    dub_profile = _profile_for_audio(paths["tts_wav"], paths["asr_json"], work / "dub_profile.json")
    source_features = extract_hubert_features(
        audio_path=paths["source_video"],
        segments=source_profile.get("segments") if isinstance(source_profile.get("segments"), list) else [],
        output_dir=work / "source_hubert",
        model_name=model_name,
    )
    dub_features = extract_hubert_features(
        audio_path=paths["tts_wav"],
        segments=dub_profile.get("segments") if isinstance(dub_profile.get("segments"), list) else [],
        output_dir=work / "dub_hubert",
        model_name=model_name,
    )
    adapter = load_adapter(adapter_dir)
    if source_features.get("status") != "computed" or dub_features.get("status") != "computed":
        errors.extend(source_features.get("errors") or [])
        errors.extend(dub_features.get("errors") or [])
        warnings.extend(source_features.get("warnings") or [])
        warnings.extend(dub_features.get("warnings") or [])
        report = {
            "status": "unavailable",
            "hubert_model": model_name,
            "adapter_path": str(adapter_dir),
            "adapter_status": adapter.status,
            "global": {"prosody_similarity_score_0_100": None, "embedding_cosine_similarity": None, "confidence": "low"},
            "segments": [],
            "warnings": warnings,
            "errors": errors,
            "note": "HuBERT-guided similarity, not exact emotion transfer.",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return report
    source_emb = _load_embedding(source_features.get("global_embedding_path"))
    dub_emb = _load_embedding(dub_features.get("global_embedding_path"))
    source_global = source_profile.get("global") if isinstance(source_profile.get("global"), dict) else {}
    dub_global = dub_profile.get("global") if isinstance(dub_profile.get("global"), dict) else {}
    features = {
        "embedding_cosine": cosine_similarity(source_emb, dub_emb) if source_emb is not None and dub_emb is not None else None,
        "duration_similarity": _duration_similarity(source_global.get("speech_duration_sec"), dub_global.get("speech_duration_sec")),
        "speech_rate_similarity": rate_similarity(source_global.get("speech_rate_wpm"), dub_global.get("speech_rate_wpm")),
        "energy_similarity": _scalar_similarity(source_global.get("average_energy_rms"), dub_global.get("average_energy_rms")),
        "pause_similarity": _scalar_similarity(source_global.get("pause_count"), dub_global.get("pause_count")),
    }
    segment_reports: list[dict[str, Any]] = []
    source_segments = source_features.get("segment_embeddings") or []
    dub_segments = dub_features.get("segment_embeddings") or []
    if len(source_segments) != len(dub_segments):
        warnings.append("Source and dubbed segment embedding counts differ; segment similarity is partial.")
    for source_segment, dub_segment in zip(source_segments, dub_segments):
        if not isinstance(source_segment, dict) or not isinstance(dub_segment, dict):
            continue
        s_emb = _load_embedding(source_segment.get("embedding_path"))
        d_emb = _load_embedding(dub_segment.get("embedding_path"))
        if s_emb is None or d_emb is None:
            continue
        similarity = cosine_similarity(s_emb, d_emb)
        segment_reports.append(
            {
                "segment_id": source_segment.get("segment_id"),
                "embedding_cosine_similarity": round(similarity, 6),
                "prosody_similarity_score_0_100": round(((similarity + 1.0) / 2.0) * 100.0, 3),
            }
        )
    report = {
        "status": "computed",
        "hubert_model": model_name,
        "adapter_path": str(adapter_dir),
        "adapter_status": adapter.status,
        "features": {key: round(value, 6) if isinstance(value, float) else value for key, value in features.items()},
        "global": {
            "prosody_similarity_score_0_100": adapter.predict_score(features),
            "embedding_cosine_similarity": round(features["embedding_cosine"], 6) if features["embedding_cosine"] is not None else None,
            "confidence": adapter.confidence,
        },
        "segments": segment_reports,
        "warnings": warnings,
        "errors": errors,
        "note": "HuBERT-guided similarity, not exact emotion transfer.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
