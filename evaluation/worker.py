"""Automatic backend evaluation worker."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.asr_eval import evaluate_asr
from evaluation.audio_metrics import compute_audio_metrics
from evaluation.media_metrics import probe_media
from evaluation.quality_schema import clamp, confidence_from_ranks, metric, score_to_grade, utc_now_iso
from evaluation.reference_builder import build_reference_context, discover_artifacts, read_json
from evaluation.speaker_eval import evaluate_speaker
from evaluation.sync_eval import evaluate_sync
from evaluation.translation_eval import evaluate_translation
from evaluation.voice_eval import evaluate_voice


SARVAM_LANGS = {"bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}
XTTS_LANGS = {"ar", "cs", "de", "en", "es", "fr", "hu", "it", "ja", "ko", "nl", "pl", "pt", "ru", "tr", "zh"}


def _human_quality(path: Path | None) -> dict[str, Any]:
    data = read_json(path)
    rating = data.get("human_mos_rating")
    if rating is not None:
        try:
            data["human_mos_rating"] = float(rating)
        except (TypeError, ValueError):
            data.pop("human_mos_rating", None)
    return data


def _operational(pipeline_result: dict[str, Any], translation_data: dict[str, Any], media: dict[str, Any], audio: dict[str, Any]) -> dict[str, Any]:
    metrics = pipeline_result.get("metrics") if isinstance(pipeline_result.get("metrics"), dict) else {}
    analysis = pipeline_result.get("analysis") if isinstance(pipeline_result.get("analysis"), dict) else {}
    run_evidence = analysis.get("run_evidence") if isinstance(analysis.get("run_evidence"), dict) else {}
    target_language = translation_data.get("language") or run_evidence.get("target_language") or metrics.get("target_language")
    target_base = str(target_language or "").lower().replace("_", "-").split("-")[0]
    inferred_voice_backend = "Sarvam" if target_base in SARVAM_LANGS else "XTTS" if target_base in XTTS_LANGS else None
    return {
        "total_elapsed_sec": metrics.get("totalTime") or run_evidence.get("total_elapsed_sec"),
        "current_stage": pipeline_result.get("stage") or ("complete" if pipeline_result.get("localizedVideos") else None),
        "terminal_stage": "error" if pipeline_result.get("error") else "complete" if pipeline_result.get("localizedVideos") else None,
        "source_language": translation_data.get("source_language") or run_evidence.get("source_language"),
        "target_language": target_language,
        "translation_backend": translation_data.get("translation_engine") or run_evidence.get("translation_backend") or metrics.get("translation_backend"),
        "voice_backend": run_evidence.get("voice_backend") or metrics.get("voice_backend") or inferred_voice_backend,
        "validation_passed": bool(audio.get("validation_passed")) and bool(media.get("validation_passed")),
    }


def _lipsync_evidence(pipeline_result: dict[str, Any], sync: dict[str, Any]) -> dict[str, Any]:
    metrics = pipeline_result.get("metrics") if isinstance(pipeline_result.get("metrics"), dict) else {}
    analysis = pipeline_result.get("analysis") if isinstance(pipeline_result.get("analysis"), dict) else {}
    lipsync = analysis.get("lipsync") if isinstance(analysis.get("lipsync"), dict) else {}
    lse_c = sync.get("lse_c") if isinstance(sync.get("lse_c"), dict) else {}
    lse_d = sync.get("lse_d") if isinstance(sync.get("lse_d"), dict) else {}
    method = lipsync.get("method") or metrics.get("lipsync_method") or "unknown"
    return {
        "method": method,
        "visual_sync_applied": bool(lipsync.get("visual_sync_applied", metrics.get("lipsync_visual_sync_applied", False))),
        "visual_sync_requested": bool(lipsync.get("visual_sync_requested", metrics.get("visual_lipsync_requested", False))),
        "fallback_used": bool(lipsync.get("fallback_used", metrics.get("lipsync_fallback_used", False))),
        "wav2lip_preflight_ok": bool(lipsync.get("wav2lip_preflight_ok", metrics.get("wav2lip_preflight_ok", False))),
        "wav2lip_python": lipsync.get("wav2lip_python") or metrics.get("wav2lip_python"),
        "checkpoint_exists": bool(lipsync.get("checkpoint_exists", metrics.get("wav2lip_checkpoint_exists", False))),
        "alignment_level": lipsync.get("alignment_level") or metrics.get("alignment_level") or "unknown",
        "lse_c_status": lse_c.get("method") or "unavailable",
        "lse_d_status": lse_d.get("method") or "unavailable",
        "source_video_duration_s": lipsync.get("source_video_duration_s") or metrics.get("video_duration_s"),
        "generated_audio_duration_s": lipsync.get("generated_audio_duration_s") or metrics.get("tts_duration_s"),
        "prepared_audio_duration_s": lipsync.get("prepared_audio_duration_s") or metrics.get("prepared_audio_duration_s"),
        "final_mp4_duration_s": lipsync.get("final_mp4_duration_s") or metrics.get("final_mp4_duration_s"),
        "duration_delta_s": lipsync.get("duration_delta_s") or metrics.get("duration_delta_s"),
        "audio_padded_sec": lipsync.get("audio_padded_sec") or metrics.get("audio_padded_sec"),
        "audio_trimmed_sec": lipsync.get("audio_trimmed_sec") or metrics.get("audio_trimmed_sec"),
        "wav2lip_error": lipsync.get("wav2lip_error") or metrics.get("wav2lip_error"),
        "warnings": lipsync.get("warnings") if isinstance(lipsync.get("warnings"), list) else [],
        "errors": lipsync.get("errors") if isinstance(lipsync.get("errors"), list) else [],
    }


def _score_value(section: dict[str, Any]) -> tuple[float | None, str]:
    item = section.get("score")
    if not isinstance(item, dict):
        return None, "none"
    value = item.get("value")
    if not isinstance(value, (int, float)):
        return None, str(item.get("confidence") or "none")
    unit = item.get("unit")
    score = float(value) if unit == "percent" else float(value) * 100.0
    return clamp(score, 0.0, 100.0), str(item.get("confidence") or "low")


def _media_score(media: dict[str, Any]) -> dict[str, Any]:
    stream_score = 1.0 if media.get("video_stream_exists") and media.get("audio_stream_exists") else 0.0
    duration_score = 1.0 if float(media.get("duration_sec") or 0.0) > 0.5 else 0.0
    size_score = 1.0 if int(media.get("size_bytes") or 0) > 1024 else 0.0
    score = clamp((stream_score * 0.55) + (duration_score * 0.25) + (size_score * 0.20))
    return {
        "display_label": "Output validation",
        "score": metric(
            status="computed" if media.get("status") == "computed" else "missing_artifact",
            value=round(score * 100.0, 3),
            unit="percent",
            method="ffprobe_media_validation",
            confidence="high" if media.get("status") == "computed" else "low",
            source="final_mp4_ffprobe",
            explanation="Validates final MP4 presence, audio/video streams, duration, and file size.",
            reference_type="artifact",
        ),
        "signals": media,
    }


def _overall(sections: dict[str, dict[str, Any]], output_validation: dict[str, Any]) -> dict[str, Any]:
    weighted = [
        ("asr", sections["asr"], 0.22),
        ("translation", sections["translation"], 0.26),
        ("voice", sections["voice"], 0.18),
        ("sync", sections["sync"], 0.18),
        ("output_validation", output_validation, 0.10),
        ("speaker", sections["speaker"], 0.06),
    ]
    available: list[tuple[str, float, float, str]] = []
    excluded: dict[str, str] = {}
    for name, section, weight in weighted:
        score, confidence = _score_value(section)
        status = (section.get("score") or {}).get("status") if isinstance(section.get("score"), dict) else None
        if status == "not_applicable":
            excluded[name] = "not_applicable"
            continue
        if score is None:
            excluded[name] = str(status or "unavailable")
            continue
        available.append((name, score, weight, confidence))
    weight_total = sum(item[2] for item in available)
    score_0_100 = sum(score * (weight / weight_total) for _, score, weight, _ in available) if weight_total else 0.0
    components = {
        name: {"score_0_100": round(score, 3), "base_weight": weight, "effective_weight": round(weight / weight_total, 6) if weight_total else 0.0}
        for name, score, weight, _ in available
    }
    return {
        "overall_quality_index": metric(
            status="computed" if available else "unavailable",
            value=round(score_0_100, 3),
            unit="score_0_100",
            method="weighted_available_metric_index",
            confidence=confidence_from_ranks([confidence for *_, confidence in available]),
            source="automatic_evaluation_sections",
            explanation="Automatic evaluation based on available true-reference, auto-reference, and proxy metrics; unavailable/not-applicable components are redistributed.",
            reference_type="mixed",
            details={"components": components, "excluded_components": excluded},
        ),
        "score_0_100": round(score_0_100, 3),
        "grade": score_to_grade(score_0_100),
        "confidence": confidence_from_ranks([confidence for *_, confidence in available]),
        "components": components,
        "excluded_components": excluded,
        "explanation": "Automatic evaluation based on artifact-derived and evaluator-derived metrics.",
    }


def build_automatic_metrics_report(job_dir: str | Path) -> dict[str, Any]:
    artifacts = discover_artifacts(job_dir)
    context = build_reference_context(artifacts)
    pipeline_result = read_json(artifacts.get("pipeline_result"))
    asr_data = context.get("asr_data") if isinstance(context.get("asr_data"), dict) else {}
    translation_data = context.get("translation_data") if isinstance(context.get("translation_data"), dict) else {}
    audio = compute_audio_metrics(artifacts.get("tts_wav"), source_segments=asr_data.get("segments") if isinstance(asr_data.get("segments"), list) else [])
    media = probe_media(artifacts.get("final_mp4"))
    operational = _operational(pipeline_result, translation_data, media, audio)
    human_quality = _human_quality(artifacts.get("human_quality"))

    sections = {
        "asr": evaluate_asr(context),
        "translation": evaluate_translation(context),
        "voice": evaluate_voice(audio, human_quality),
        "sync": evaluate_sync(Path(job_dir), media, audio),
        "speaker": evaluate_speaker(
            job_dir=Path(job_dir),
            reference_audio=artifacts.get("reference_audio"),
            generated_audio=artifacts.get("tts_wav"),
            operational=operational,
            translation_data=translation_data,
        ),
    }
    lipsync_evidence = _lipsync_evidence(pipeline_result, sections["sync"])
    output_validation = _media_score(media)
    warnings: list[str] = []
    errors: list[str] = []
    if sections["sync"]["lse_c"]["status"] == "unavailable":
        warnings.append("LSE-C/LSE-D evaluator not installed; A/V sync proxy was used.")
    if sections["translation"]["score"]["status"] == "proxy_computed":
        warnings.append("No reference translation or independent translation evaluator was available; translation proxy was used.")
    if sections["asr"]["score"]["status"] == "proxy_computed":
        warnings.append("No transcript reference or independent ASR consensus was available; ASR reliability proxy was used.")
    if media.get("status") != "computed":
        errors.append(str(media.get("reason") or "Final MP4 could not be inspected."))
    if audio.get("status") != "computed":
        errors.append(str(audio.get("reason") or "Generated TTS WAV could not be inspected."))

    report: dict[str, Any] = {
        "schema_version": 2,
        "evaluation_mode": "automatic",
        "generated_at": utc_now_iso(),
        "job_dir": str(job_dir),
        "metric_sources": {
            "asr": sections["asr"]["score"]["reference_type"],
            "translation": sections["translation"]["score"]["reference_type"],
            "voice": sections["voice"]["score"]["reference_type"],
            "sync": sections["sync"]["score"]["reference_type"],
            "speaker": sections["speaker"]["score"]["reference_type"],
        },
        **sections,
        "lipsync": lipsync_evidence,
        "overall": _overall(sections, output_validation),
        "output_validation": output_validation,
        "operational": operational,
        "voice_audio": audio,
        "media_output": media,
        "warnings": warnings,
        "errors": errors,
        "inputs": {
            "ground_truth_transcript_provided": bool(context.get("true_transcript")),
            "reference_translation_provided": bool(context.get("reference_translation")),
            "human_mos_rating_provided": human_quality.get("human_mos_rating") is not None,
            "auto_consensus_transcript_available": bool(context.get("auto_consensus_transcript")),
            "auto_reference_translation_available": bool(context.get("auto_reference_translation")),
        },
    }
    return report


def write_metrics_report(report: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def run_evaluation(job_dir: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    report = build_automatic_metrics_report(job_dir)
    output = Path(output_path) if output_path else Path(job_dir) / "evaluation" / "metrics_report.json"
    write_metrics_report(report, output)
    return report
