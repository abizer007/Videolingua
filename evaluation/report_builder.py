"""Build metrics reports from VideoLingua job folders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from asr.speaker_analysis import analyze_speakers_from_asr
from evaluation.audio_metrics import compute_audio_metrics
from evaluation.media_metrics import probe_media
from evaluation.metrics import advanced_evaluator_status, computed, error_result, unavailable
from evaluation.text_metrics import asr_accuracy_from_wer, bleu_lite, cer, chrf_lite, join_segment_text, wer

XTTS_LANGS = {"ar", "cs", "de", "en", "es", "fr", "hu", "it", "ja", "ko", "nl", "pl", "pt", "ru", "tr", "zh"}
SARVAM_LANGS = {"bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}


def _read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_text_file(path: str | Path | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="replace").strip()


def _text_from_path_or_literal(value: str | Path | None) -> str:
    if not value:
        return ""
    raw = str(value)
    try:
        path = Path(raw)
        if path.is_file():
            return _read_text_file(path)
    except (OSError, ValueError):
        pass
    return raw.strip()


def _first_file(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.is_file()), None)


def _discover(job_dir: Path) -> dict[str, Path | None]:
    asr_jsons = sorted((job_dir / "asr" / "output").glob("*.json"))
    translation_jsons = sorted((job_dir / "translation" / "output").glob("*.json"))
    translation_payloads = [
        path
        for path in translation_jsons
        if not (
            path.name == "translation_qa_report.json"
            or path.name.endswith(".translation_qa_report.json")
            or path.name == "linguistic_integrity_report.json"
            or path.name.endswith(".linguistic_integrity_report.json")
        )
    ]
    translation_qa_reports = [
        path
        for path in translation_jsons
        if path.name == "translation_qa_report.json" or path.name.endswith(".translation_qa_report.json")
    ]
    tts_wavs = sorted((job_dir / "tts" / "output").glob("*.wav"))
    phonetic_reports = sorted((job_dir / "tts" / "output").glob("*phonetic_resolution_report.json"))
    mp4s = sorted((job_dir / "results").glob("*_dubbed_*.mp4"))
    if not mp4s:
        mp4s = sorted(path for path in (job_dir / "results").glob("*.mp4") if path.name != "input_video.mp4")
    return {
        "pipeline_result": job_dir / "pipeline_result.json",
        "asr_json": _first_file(asr_jsons),
        "translation_json": _first_file(translation_payloads),
        "translation_qa_report": _first_file(translation_qa_reports),
        "linguistic_integrity_report": _first_file(sorted((job_dir / "translation" / "output").glob("*linguistic_integrity_report.json"))),
        "phonetic_resolution_report": _first_file(phonetic_reports),
        "source_prosody_profile": job_dir / "prosody" / "source_prosody_profile.json",
        "tts_prosody_plan": job_dir / "prosody" / "tts_prosody_plan.json",
        "prosody_validation_report": job_dir / "prosody" / "prosody_validation_report.json",
        "hubert_prosody_report": job_dir / "prosody" / "hubert_prosody_report.json",
        "tts_wav": _first_file(tts_wavs),
        "final_mp4": _first_file(mp4s),
        "ground_truth_transcript": job_dir / "evaluation" / "ground_truth_transcript.txt",
        "reference_translation": job_dir / "evaluation" / "reference_translation.txt",
        "human_quality": job_dir / "evaluation" / "human_quality.json",
        "compliance_passport": job_dir / "compliance" / "compliance_passport.json",
        "sgi_risk_report": job_dir / "compliance" / "sgi_risk_report.json",
        "abuse_risk_report": job_dir / "compliance" / "abuse_risk_report.json",
        "provenance_manifest": job_dir / "compliance" / "provenance_manifest.json",
        "fingerprint_report": job_dir / "compliance" / "fingerprint_report.json",
    }


def _stage_timings(pipeline_result: dict[str, Any]) -> dict[str, float]:
    history = pipeline_result.get("stageHistory") or pipeline_result.get("stage_history") or []
    timings: dict[str, float] = {}
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict):
                continue
            stage = str(item.get("stage") or "")
            duration = item.get("durationSeconds") or item.get("duration_seconds")
            if stage and isinstance(duration, (int, float)):
                timings[stage] = round(float(duration), 3)
    return timings


def _word_count(text: str) -> int:
    return len([part for part in text.split() if part.strip()])


def _segment_duration(segment: dict[str, Any]) -> float:
    try:
        return max(0.0, float(segment.get("end", 0.0)) - float(segment.get("start", 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _segment_summary(segments: list[Any]) -> dict[str, Any]:
    normalized = [segment for segment in segments if isinstance(segment, dict)]
    text = join_segment_text(normalized)
    durations = [_segment_duration(segment) for segment in normalized]
    total_duration = sum(durations)
    word_total = _word_count(text)
    return {
        "segment_count": len(normalized),
        "total_characters": len(text),
        "total_words": word_total,
        "total_duration_sec": round(total_duration, 3),
        "average_segment_duration_sec": round(total_duration / len(normalized), 3) if normalized else None,
        "average_words_per_segment": round(word_total / len(normalized), 3) if normalized else None,
        "text": text,
    }


def _current_stage(pipeline_result: dict[str, Any]) -> str | None:
    stage = pipeline_result.get("stage")
    if isinstance(stage, str) and stage:
        return stage
    if pipeline_result.get("error"):
        return "error"
    if pipeline_result.get("localizedVideos"):
        return "complete"
    return None


def _warnings_from_report(audio: dict[str, Any], media: dict[str, Any], translation: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    empty_segments = translation.get("empty_translation_segment_count")
    if isinstance(empty_segments, int) and empty_segments > 0:
        warnings.append(f"{empty_segments} translated segment(s) are empty.")
    long_segments = translation.get("suspiciously_long_segment_count")
    if isinstance(long_segments, int) and long_segments > 0:
        warnings.append(f"{long_segments} translated segment(s) are more than 2.5x the source length.")
    qa_warnings = translation.get("translation_qa_warnings_count")
    if isinstance(qa_warnings, int) and qa_warnings > 0:
        warnings.append(f"Translation QA reported {qa_warnings} warning(s).")
    qa_errors = translation.get("translation_qa_errors_count")
    if isinstance(qa_errors, int) and qa_errors > 0:
        warnings.append(f"Translation QA reported {qa_errors} error(s).")
    if audio.get("status") not in {"computed", None}:
        warnings.append(str(audio.get("reason") or "TTS audio metrics were not computed."))
    if media.get("status") not in {"computed", None}:
        warnings.append(str(media.get("reason") or "Final media metrics were not computed."))
    return warnings


def _translation_policy(translation_data: dict[str, Any]) -> dict[str, Any]:
    policy = translation_data.get("translation_policy")
    return policy if isinstance(policy, dict) else {}


def _infer_voice_backend(target_language: str | None) -> str | None:
    language = (target_language or "").strip().lower().replace("_", "-").split("-")[0]
    if language in XTTS_LANGS:
        return "XTTS"
    if language in SARVAM_LANGS:
        return "Sarvam"
    return None


def _lipsync_evidence(metrics: dict[str, Any], analysis: dict[str, Any], media: dict[str, Any], audio: dict[str, Any]) -> dict[str, Any]:
    lipsync = analysis.get("lipsync") if isinstance(analysis.get("lipsync"), dict) else {}
    return {
        "method": lipsync.get("method") or metrics.get("lipsync_method") or "unknown",
        "visual_sync_applied": bool(lipsync.get("visual_sync_applied", metrics.get("lipsync_visual_sync_applied", False))),
        "visual_sync_requested": bool(lipsync.get("visual_sync_requested", metrics.get("visual_lipsync_requested", False))),
        "fallback_used": bool(lipsync.get("fallback_used", metrics.get("lipsync_fallback_used", False))),
        "wav2lip_preflight_ok": bool(lipsync.get("wav2lip_preflight_ok", metrics.get("wav2lip_preflight_ok", False))),
        "wav2lip_python": lipsync.get("wav2lip_python") or metrics.get("wav2lip_python"),
        "checkpoint_exists": bool(lipsync.get("checkpoint_exists", metrics.get("wav2lip_checkpoint_exists", False))),
        "alignment_level": lipsync.get("alignment_level") or metrics.get("alignment_level") or "unknown",
        "lse_c_status": lipsync.get("lse_c_status") or "not_installed",
        "lse_d_status": lipsync.get("lse_d_status") or "not_installed",
        "source_video_duration_s": lipsync.get("source_video_duration_s") or metrics.get("video_duration_s"),
        "generated_audio_duration_s": lipsync.get("generated_audio_duration_s") or audio.get("duration_sec"),
        "prepared_audio_duration_s": lipsync.get("prepared_audio_duration_s") or metrics.get("prepared_audio_duration_s"),
        "final_mp4_duration_s": lipsync.get("final_mp4_duration_s") or media.get("duration_sec"),
        "duration_delta_s": lipsync.get("duration_delta_s") or metrics.get("duration_delta_s"),
        "audio_padded_sec": lipsync.get("audio_padded_sec") or metrics.get("audio_padded_sec"),
        "audio_trimmed_sec": lipsync.get("audio_trimmed_sec") or metrics.get("audio_trimmed_sec"),
        "wav2lip_error": lipsync.get("wav2lip_error") or metrics.get("wav2lip_error"),
        "warnings": lipsync.get("warnings") if isinstance(lipsync.get("warnings"), list) else [],
        "errors": lipsync.get("errors") if isinstance(lipsync.get("errors"), list) else [],
    }


def _human_quality(path: Path | None, rating: float | None, notes: str | None) -> tuple[float | None, str | None]:
    if rating is not None or notes:
        return rating, notes
    data = _read_json(path)
    loaded_rating = data.get("human_mos_rating")
    try:
        loaded_rating = float(loaded_rating) if loaded_rating is not None else None
    except (TypeError, ValueError):
        loaded_rating = None
    loaded_notes = data.get("human_quality_notes")
    return loaded_rating, str(loaded_notes) if loaded_notes else None


def _asr_metrics(ground_truth: str, hypothesis: str) -> dict[str, Any]:
    if not ground_truth:
        missing = unavailable("requires_ground_truth", "Upload a ground-truth transcript to compute this metric.")
        return {"wer": missing, "cer": missing, "accuracy": missing}
    try:
        wer_value = wer(ground_truth, hypothesis)
        cer_value = cer(ground_truth, hypothesis)
        return {
            "wer": computed(round(wer_value, 6)),
            "cer": computed(round(cer_value, 6)),
            "accuracy": computed(round(asr_accuracy_from_wer(wer_value), 6)),
        }
    except Exception as exc:
        err = error_result(str(exc))
        return {"wer": err, "cer": err, "accuracy": err}


def _translation_metrics(reference: str, hypothesis: str) -> dict[str, Any]:
    if not reference:
        missing = unavailable(
            "requires_reference_translation",
            "Upload a reference translation to compute this metric.",
        )
        return {"bleu": missing, "chrf": missing}
    try:
        return {
            "bleu": computed(round(bleu_lite(reference, hypothesis), 6), label="BLEU-lite"),
            "chrf": computed(round(chrf_lite(reference, hypothesis), 6), label="chrF-lite"),
        }
    except Exception as exc:
        err = error_result(str(exc))
        return {"bleu": err, "chrf": err}


def build_metrics_report(
    job_dir: str | Path,
    *,
    ground_truth_transcript: str | Path | None = None,
    reference_translation: str | Path | None = None,
    human_mos_rating: float | None = None,
    human_quality_notes: str | None = None,
) -> dict[str, Any]:
    job_dir = Path(job_dir)
    paths = _discover(job_dir)
    pipeline_result = _read_json(paths["pipeline_result"])
    metrics = pipeline_result.get("metrics") if isinstance(pipeline_result.get("metrics"), dict) else {}
    analysis = pipeline_result.get("analysis") if isinstance(pipeline_result.get("analysis"), dict) else {}
    asr_data = _read_json(paths["asr_json"])
    translation_data = _read_json(paths["translation_json"])
    translation_qa_report = _read_json(paths["translation_qa_report"])
    linguistic_integrity_report = _read_json(paths["linguistic_integrity_report"])
    phonetic_resolution_report = _read_json(paths["phonetic_resolution_report"])
    source_prosody_profile = _read_json(paths["source_prosody_profile"])
    tts_prosody_plan = _read_json(paths["tts_prosody_plan"])
    prosody_validation_report = _read_json(paths["prosody_validation_report"])
    hubert_prosody_report = _read_json(paths["hubert_prosody_report"])
    compliance_passport = _read_json(paths["compliance_passport"])
    sgi_risk_report = _read_json(paths["sgi_risk_report"])
    abuse_risk_report = _read_json(paths["abuse_risk_report"])
    provenance_manifest = _read_json(paths["provenance_manifest"])
    fingerprint_report = _read_json(paths["fingerprint_report"])
    translation_qa_summary = translation_data.get("translation_qa") if isinstance(translation_data.get("translation_qa"), dict) else {}
    linguistic_summary = translation_data.get("linguistic_integrity") if isinstance(translation_data.get("linguistic_integrity"), dict) else {}
    phonetic_summary = translation_data.get("phonetic_resolution") if isinstance(translation_data.get("phonetic_resolution"), dict) else {}
    asr_segments = asr_data.get("segments") if isinstance(asr_data.get("segments"), list) else []
    translated_segments = translation_data.get("segments") if isinstance(translation_data.get("segments"), list) else []
    translation_policy = _translation_policy(translation_data)

    ground_truth_text = _text_from_path_or_literal(ground_truth_transcript) or _read_text_file(paths["ground_truth_transcript"])
    reference_translation_text = _text_from_path_or_literal(reference_translation) or _read_text_file(paths["reference_translation"])

    audio = compute_audio_metrics(paths["tts_wav"], source_segments=asr_segments)
    media = probe_media(paths["final_mp4"])
    speaker = analyze_speakers_from_asr([paths["asr_json"]] if paths["asr_json"] else [])
    loaded_human_rating, loaded_human_notes = _human_quality(paths["human_quality"], human_mos_rating, human_quality_notes)

    target_language = translation_data.get("language") or metrics.get("target_language")
    voice_backend = (
        (analysis.get("run_evidence") or {}).get("voice_backend")
        if isinstance(analysis.get("run_evidence"), dict)
        else None
    ) or metrics.get("voice_backend") or _infer_voice_backend(target_language)
    translation_backend = translation_data.get("translation_engine") or metrics.get("translation_backend")

    transcript_summary = _segment_summary(asr_segments)
    translation_summary_base = _segment_summary(translated_segments)
    source_chars = transcript_summary["total_characters"]
    translated_chars = translation_summary_base["total_characters"]
    empty_translation_count = sum(
        1
        for segment in translated_segments
        if isinstance(segment, dict) and not str(segment.get("text") or "").strip()
    )
    suspiciously_long_count = 0
    for source_segment, translated_segment in zip(asr_segments, translated_segments):
        if not isinstance(source_segment, dict) or not isinstance(translated_segment, dict):
            continue
        source_len = max(1, len(str(source_segment.get("text") or "").strip()))
        translated_len = len(str(translated_segment.get("text") or "").strip())
        if translated_len / source_len > 2.5:
            suspiciously_long_count += 1

    operational = {
        "total_elapsed_sec": metrics.get("totalTime") or (analysis.get("run_evidence") or {}).get("total_elapsed_sec") if isinstance(analysis.get("run_evidence"), dict) else metrics.get("totalTime"),
        "per_stage_elapsed_sec": _stage_timings(pipeline_result),
        "current_stage": _current_stage(pipeline_result),
        "terminal_stage": _current_stage(pipeline_result),
        "source_language": translation_data.get("source_language") or asr_data.get("language") or metrics.get("translation_source_language"),
        "target_language": target_language,
        "translation_backend": translation_backend,
        "voice_backend": voice_backend,
        "fallback_used": bool(translation_policy.get("fallback_used", False) or metrics.get("fallback_used", False)),
        "generic_fallback_used": bool(metrics.get("generic_fallback_used", False)),
    }
    transcript = {
        "asr_segment_count": transcript_summary["segment_count"],
        "total_transcript_characters": transcript_summary["total_characters"],
        "total_transcript_words": transcript_summary["total_words"],
        "average_segment_duration_sec": transcript_summary["average_segment_duration_sec"],
        "average_words_per_segment": transcript_summary["average_words_per_segment"],
        "detected_source_language": asr_data.get("language") or operational["source_language"],
        "speaker_analysis_status": speaker.get("status"),
        "speakers_detected": speaker.get("speakers_detected") if speaker.get("status") == "computed" else None,
    }
    translation = {
        "translated_segment_count": translation_summary_base["segment_count"],
        "total_translated_characters": translation_summary_base["total_characters"],
        "total_translated_words": translation_summary_base["total_words"],
        "segment_count_matches_source": transcript_summary["segment_count"] == translation_summary_base["segment_count"],
        "expansion_ratio": round(translated_chars / source_chars, 6) if source_chars else None,
        "empty_translation_segment_count": empty_translation_count,
        "suspiciously_long_segment_count": suspiciously_long_count,
        "backend_selected": translation_backend,
        "translation_qa_status": translation_qa_summary.get("status") or translation_qa_report.get("status"),
        "translation_qa_checks_passed": translation_qa_summary.get("checksPassed"),
        "translation_qa_warnings_count": translation_qa_summary.get("warningsCount") if translation_qa_summary else len(translation_qa_report.get("warnings") or []),
        "translation_qa_errors_count": translation_qa_summary.get("errorsCount") if translation_qa_summary else len(translation_qa_report.get("errors") or []),
        "translation_qa_empty_segments": translation_qa_summary.get("emptySegments"),
        "translation_qa_script_match": translation_qa_summary.get("scriptMatch"),
        "translation_qa_number_issues": translation_qa_summary.get("numberIssues"),
        "translation_qa_entity_issues": translation_qa_summary.get("entityIssues"),
        "translation_qa_expansion_ratio_warnings": translation_qa_summary.get("expansionRatioWarnings"),
        "translation_qa_report": paths["translation_qa_report"].name if paths["translation_qa_report"] else translation_qa_summary.get("reportPath"),
        "linguistic_integrity_status": linguistic_summary.get("status") or linguistic_integrity_report.get("status"),
        "linguistic_integrity_score": linguistic_summary.get("score") or linguistic_integrity_report.get("score_0_100"),
        "linguistic_integrity_script_status": linguistic_summary.get("scriptStatus"),
        "linguistic_integrity_number_warnings": linguistic_summary.get("numberWarnings"),
        "linguistic_integrity_name_warnings": linguistic_summary.get("nameWarnings"),
        "linguistic_integrity_expansion_warnings": linguistic_summary.get("expansionWarnings"),
        "linguistic_integrity_report": paths["linguistic_integrity_report"].name if paths["linguistic_integrity_report"] else linguistic_summary.get("reportPath"),
        "bleu": None,
        "chrf": None,
    }
    voice_audio = {
        "tts_wav_exists": bool(paths["tts_wav"] and paths["tts_wav"].is_file()),
        "tts_duration_sec": audio.get("duration_sec"),
        "sample_rate": audio.get("sample_rate"),
        "channels": audio.get("channels"),
        "peak": audio.get("peak"),
        "rms": audio.get("rms"),
        "clipping_ratio": audio.get("clipping_ratio"),
        "silence_ratio": audio.get("silence_ratio"),
        "normalization_applied": audio.get("normalization_applied"),
        "duration_drift_sec": audio.get("duration_drift_sec"),
        "duration_drift_ratio": audio.get("duration_drift_ratio"),
        "status": audio.get("status"),
        "validation_passed": audio.get("validation_passed"),
        "phonetic_resolution_status": phonetic_summary.get("status") or phonetic_resolution_report.get("status"),
        "phonetic_risk_score": phonetic_summary.get("phoneticRiskScore") or phonetic_resolution_report.get("phonetic_risk_score_0_100"),
        "pronunciation_dictionary_used": phonetic_summary.get("dictionaryUsed") if phonetic_summary else phonetic_resolution_report.get("dictionary_used"),
        "acronyms_detected": phonetic_summary.get("acronymsDetected") or len(phonetic_resolution_report.get("acronyms_detected") or []),
        "ambiguity_warnings": phonetic_summary.get("ambiguityWarnings") or len(phonetic_resolution_report.get("ambiguity_warnings") or []),
        "phonetic_resolution_report": paths["phonetic_resolution_report"].name if paths["phonetic_resolution_report"] else phonetic_summary.get("reportPath"),
    }
    source_prosody_global = source_prosody_profile.get("global") if isinstance(source_prosody_profile.get("global"), dict) else {}
    prosody_plan_global = tts_prosody_plan.get("global") if isinstance(tts_prosody_plan.get("global"), dict) else {}
    prosody_validation_global = prosody_validation_report.get("global") if isinstance(prosody_validation_report.get("global"), dict) else {}
    hubert_global = hubert_prosody_report.get("global") if isinstance(hubert_prosody_report.get("global"), dict) else {}
    prosody = {
        "profile_computed": source_prosody_profile.get("summary", {}).get("status") == "computed" if isinstance(source_prosody_profile.get("summary"), dict) else False,
        "profile_status": source_prosody_profile.get("summary", {}).get("status") if isinstance(source_prosody_profile.get("summary"), dict) else source_prosody_profile.get("status"),
        "preset": tts_prosody_plan.get("preset"),
        "speech_rate_class": source_prosody_global.get("speech_rate_class"),
        "average_speech_rate_wpm": source_prosody_global.get("speech_rate_wpm"),
        "pause_count": source_prosody_global.get("pause_count"),
        "average_pause_sec": source_prosody_global.get("average_pause_sec"),
        "duration_pressure": prosody_plan_global.get("duration_pressure"),
        "max_duration_pressure_ratio": prosody_plan_global.get("max_duration_pressure_ratio"),
        "duration_drift_sec": prosody_validation_global.get("duration_drift_sec"),
        "pause_preservation_proxy": prosody_validation_global.get("pause_preservation_proxy"),
        "hubert_features_computed": hubert_prosody_report.get("status") == "computed",
        "hubert_prosody_status": hubert_prosody_report.get("status"),
        "hubert_model": hubert_prosody_report.get("hubert_model"),
        "hubert_adapter_status": hubert_prosody_report.get("adapter_status"),
        "hubert_prosody_similarity_score": hubert_global.get("prosody_similarity_score_0_100"),
        "hubert_embedding_cosine_similarity": hubert_global.get("embedding_cosine_similarity"),
        "adapter_confidence": hubert_global.get("confidence"),
        "speed_guardrail_violations": sum(
            1
            for item in (tts_prosody_plan.get("segments") or [])
            if isinstance(item, dict) and item.get("duration_pressure") == "high"
        ),
        "warnings": [
            *((source_prosody_profile.get("warnings") or []) if isinstance(source_prosody_profile.get("warnings"), list) else []),
            *((tts_prosody_plan.get("warnings") or []) if isinstance(tts_prosody_plan.get("warnings"), list) else []),
            *((prosody_validation_report.get("warnings") or []) if isinstance(prosody_validation_report.get("warnings"), list) else []),
            *((hubert_prosody_report.get("warnings") or []) if isinstance(hubert_prosody_report.get("warnings"), list) else []),
        ],
    }
    media_output = {
        "final_mp4_exists": media.get("mp4_exists"),
        "final_mp4_duration_sec": media.get("duration_sec"),
        "file_size_bytes": media.get("size_bytes"),
        "video_codec": media.get("video_codec"),
        "resolution": media.get("resolution"),
        "fps": media.get("fps"),
        "audio_codec": media.get("audio_codec"),
        "audio_sample_rate": media.get("audio_sample_rate"),
        "audio_channels": media.get("audio_channels"),
        "audio_stream_present": media.get("audio_stream_exists"),
        "video_stream_present": media.get("video_stream_exists"),
        "status": media.get("status"),
    }
    lipsync = _lipsync_evidence(metrics, analysis, media, audio)
    validation = {
        "audio_validation_passed": bool(audio.get("validation_passed")) if audio.get("status") == "computed" else False,
        "media_validation_passed": bool(media.get("validation_passed")) if media.get("status") == "computed" else False,
        "result_file_present": paths["pipeline_result"].is_file() if paths["pipeline_result"] else False,
        "warnings": [],
        "errors": [],
    }
    responsible_ai = {
        "enabled": bool(compliance_passport),
        "mode": compliance_passport.get("mode"),
        "passport_status": compliance_passport.get("overall_status"),
        "sgi_risk_level": compliance_passport.get("sgi_risk_level") or sgi_risk_report.get("sgi_likelihood"),
        "synthetic_voice_used": compliance_passport.get("synthetic_voice_used"),
        "speaker_reference_or_voice_cloning_used": compliance_passport.get("speaker_reference_or_voice_cloning_used"),
        "managed_tts_used": compliance_passport.get("managed_tts_used"),
        "speaker_consent_recorded": compliance_passport.get("speaker_consent_recorded"),
        "abuse_risk_status": compliance_passport.get("abuse_risk_status") or abuse_risk_report.get("status"),
        "visible_disclosure_applied": compliance_passport.get("visible_disclosure_applied"),
        "audio_disclosure_applied": compliance_passport.get("audio_disclosure_applied"),
        "provenance_manifest_created": compliance_passport.get("provenance_manifest_created") or bool(provenance_manifest),
        "c2pa_status": provenance_manifest.get("c2pa_status"),
        "hashes_generated": compliance_passport.get("hashes_generated"),
        "input_video_sha256": fingerprint_report.get("input_video_sha256"),
        "output_video_sha256": fingerprint_report.get("output_video_sha256"),
        "audit_ledger_created": compliance_passport.get("audit_ledger_created"),
        "safe_for_demo_export": compliance_passport.get("safe_for_demo_export"),
        "warnings_count": len(compliance_passport.get("warnings") or []),
        "errors_count": len(compliance_passport.get("errors") or []),
        "passport_path": str(paths["compliance_passport"]) if paths["compliance_passport"].is_file() else None,
        "provenance_path": str(paths["provenance_manifest"]) if paths["provenance_manifest"].is_file() else None,
        "limitations": compliance_passport.get("limitations") or [],
    }
    optional_reference_metrics = {
        "asr_wer": _asr_metrics(ground_truth_text, transcript_summary["text"])["wer"],
        "asr_cer": _asr_metrics(ground_truth_text, transcript_summary["text"])["cer"],
        "asr_accuracy": _asr_metrics(ground_truth_text, transcript_summary["text"])["accuracy"],
        "bleu": _translation_metrics(reference_translation_text, translation_summary_base["text"])["bleu"],
        "chrf": _translation_metrics(reference_translation_text, translation_summary_base["text"])["chrf"],
        **advanced_evaluator_status(
            human_mos_rating=loaded_human_rating,
            human_quality_notes=loaded_human_notes,
        ),
    }
    warnings = _warnings_from_report(audio, media, translation)
    validation["warnings"] = warnings

    report = {
        "schema_version": 1,
        "job_dir": str(job_dir),
        "operational": {
            **operational,
            "stage_timings": operational["per_stage_elapsed_sec"],
            "segment_count": transcript["asr_segment_count"],
            "translated_segment_count": translation["translated_segment_count"],
            "validation_passed": validation["audio_validation_passed"] and validation["media_validation_passed"],
        },
        "transcript": transcript,
        "translation": translation,
        "voice_audio": voice_audio,
        "prosody": prosody,
        "responsible_ai": responsible_ai,
        "media_output": media_output,
        "lipsync": lipsync,
        "reference_audio": analysis.get("reference_audio") if isinstance(analysis.get("reference_audio"), dict) else {},
        "validation": validation,
        "optional_reference_metrics": optional_reference_metrics,
        "warnings": warnings,
        "errors": [],
        "asr": _asr_metrics(ground_truth_text, transcript_summary["text"]),
        "audio": audio,
        "media": media,
        "speaker": speaker,
        "advanced": {
            "mos": optional_reference_metrics["mos"],
            "lse_c": optional_reference_metrics["lse_c"],
            "lse_d": optional_reference_metrics["lse_d"],
            "voice_similarity": optional_reference_metrics["voice_similarity"],
        },
        "inputs": {
            "ground_truth_transcript_provided": bool(ground_truth_text),
            "reference_translation_provided": bool(reference_translation_text),
            "human_mos_rating_provided": loaded_human_rating is not None,
        },
    }
    return report


def write_metrics_report(report: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
