"""End-to-end speaker analysis artifact builder."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from speaker_analysis.diarization import diarize_audio
from speaker_analysis.sarvam_voice_selection import build_sarvam_voice_plan
from speaker_analysis.speaker_mapping import apply_mapping_to_asr, load_json, map_speakers_to_asr_segments, write_json
from speaker_analysis.speaker_profiles import build_speaker_profiles, extract_reference_candidates
from speaker_analysis.visual_speaker_analysis import analyze_visual_speakers


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _speaker_summary(
    diarization: dict[str, Any],
    mapping: dict[str, Any],
    profiles: dict[str, Any],
    voice_plan: dict[str, Any],
    references: dict[str, Any],
    visual: dict[str, Any],
) -> dict[str, Any]:
    status = diarization.get("status")
    speaker_count = diarization.get("speaker_count") if status == "computed" else None
    plan_speakers = [
        {
            "speaker_id": speaker.get("speaker_id"),
            "voice_profile_hint": speaker.get("voice_profile_hint"),
            "confidence": speaker.get("confidence"),
            "hint_source": speaker.get("hint_source"),
            "selected_tts_voice": speaker.get("selected_tts_voice"),
            "selection_reason": speaker.get("selection_reason"),
        }
        for speaker in (voice_plan.get("speakers") or [])
        if isinstance(speaker, dict)
    ]
    return {
        "status": status,
        "speakers_detected": speaker_count,
        "speaker_count": speaker_count,
        "source": "pyannote" if status == "computed" else None,
        "reason": (
            "Pyannote diarization computed speaker turns and ASR segment mapping."
            if status == "computed"
            else "; ".join(diarization.get("errors") or diarization.get("warnings") or [])
            or diarization.get("recommended_fix")
            or "Speaker diarization did not run."
        ),
        "segment_count": mapping.get("segment_count"),
        "unknown_segment_count": mapping.get("unknown_segment_count"),
        "ambiguous_segment_count": mapping.get("ambiguous_segment_count"),
        "speaker_labels": [speaker.get("speaker_id") for speaker in profiles.get("speakers", []) if isinstance(speaker, dict)],
        "speaker_reference_count": len(
            [
                ref
                for ref in (references.get("references") or {}).values()
                if isinstance(ref, dict) and ref.get("path")
            ]
        ),
        "voice_assignment_status": voice_plan.get("status"),
        "visual_analysis_status": visual.get("status"),
        "sarvam_voice_plan_speakers": plan_speakers if voice_plan.get("voice_backend") == "sarvam" else [],
        "errors": diarization.get("errors") or [],
        "warnings": list(
            dict.fromkeys(
                [
                    *(diarization.get("warnings") or []),
                    *(mapping.get("warnings") or []),
                    *(profiles.get("warnings") or []),
                    *(voice_plan.get("warnings") or []),
                    *(references.get("warnings") or []),
                    *(visual.get("warnings") or []),
                ]
            )
        ),
        "recommended_fix": diarization.get("recommended_fix"),
    }


def run_speaker_analysis(
    *,
    audio: str | Path,
    asr_json: str | Path,
    output_dir: str | Path,
    target_language: str,
    voice_backend: str,
    enriched_asr_output: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    references_dir = output_dir / "references"

    diarization_path = output_dir / "speaker_diarization.json"
    mapping_path = output_dir / "speaker_segment_map.json"
    profiles_path = output_dir / "speaker_profiles.json"
    visual_path = output_dir / "visual_speaker_report.json"
    sarvam_plan_path = output_dir / "sarvam_voice_plan.json"
    voice_assignment_path = output_dir / "voice_assignment_plan.json"
    report_path = output_dir / "speaker_analysis_report.json"

    asr_payload = load_json(asr_json)
    diarization = diarize_audio(audio, diarization_path)
    mapping = map_speakers_to_asr_segments(asr_payload, diarization)
    write_json(mapping_path, mapping)
    if enriched_asr_output and mapping.get("status") == "computed":
        write_json(enriched_asr_output, apply_mapping_to_asr(asr_payload, mapping))

    visual = analyze_visual_speakers(audio, visual_path)
    if _env_bool("VIDIOLINGUA_AUTO_EXTRACT_SPEAKER_REFERENCES", True):
        references = extract_reference_candidates(audio, diarization, references_dir)
    else:
        references = {
            "status": "unavailable",
            "references": {},
            "warnings": ["Reference candidate extraction disabled by VIDIOLINGUA_AUTO_EXTRACT_SPEAKER_REFERENCES=false."],
            "errors": [],
        }
        write_json(references_dir / "speaker_reference_candidates.json", references)

    profiles = build_speaker_profiles(
        mapping,
        reference_candidates=references.get("references") if isinstance(references, dict) else {},
        visual_report=visual,
    )
    write_json(profiles_path, profiles)

    if voice_backend.lower() == "sarvam":
        voice_plan = build_sarvam_voice_plan(profiles, target_language=target_language, output_path=sarvam_plan_path)
    else:
        voice_plan = _build_xtts_voice_plan(
            profiles,
            target_language=target_language,
            output_path=voice_assignment_path,
        )
        write_json(sarvam_plan_path, {
            "status": "not_applicable",
            "target_language": target_language,
            "voice_backend": voice_backend,
            "speakers": [],
            "warnings": ["Sarvam voice plan is not applicable for this voice backend."],
            "errors": [],
        })

    if voice_backend.lower() == "sarvam":
        write_json(voice_assignment_path, voice_plan)

    report = {
        "status": diarization.get("status"),
        "target_language": target_language,
        "voice_backend": voice_backend,
        "summary": _speaker_summary(diarization, mapping, profiles, voice_plan, references, visual),
        "artifacts": {
            "speaker_diarization": str(diarization_path),
            "speaker_segment_map": str(mapping_path),
            "speaker_profiles": str(profiles_path),
            "visual_speaker_report": str(visual_path),
            "sarvam_voice_plan": str(sarvam_plan_path),
            "voice_assignment_plan": str(voice_assignment_path),
            "reference_candidates": str(references_dir / "speaker_reference_candidates.json"),
        },
        "warnings": _speaker_summary(diarization, mapping, profiles, voice_plan, references, visual).get("warnings", []),
        "errors": diarization.get("errors") or [],
    }
    write_json(report_path, report)
    return report


def _build_xtts_voice_plan(
    profiles: dict[str, Any],
    *,
    target_language: str,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    if profiles.get("status") != "computed":
        plan = {
            "status": profiles.get("status", "unavailable"),
            "target_language": target_language,
            "voice_backend": "xtts",
            "speakers": [],
            "warnings": ["XTTS voice plan unavailable because speaker profiles were not computed."],
            "errors": list(profiles.get("errors") or []),
        }
        if output_path:
            write_json(output_path, plan)
        return plan

    auto_use = _env_bool("VIDIOLINGUA_AUTO_USE_EXTRACTED_REFERENCES_FOR_XTTS", False)
    speakers: list[dict[str, Any]] = []
    missing_refs = 0
    for speaker in profiles.get("speakers") or []:
        if not isinstance(speaker, dict):
            continue
        candidate = speaker.get("reference_candidate") if isinstance(speaker.get("reference_candidate"), dict) else {}
        usable = bool(candidate.get("usable_for_xtts"))
        if not usable:
            missing_refs += 1
        speakers.append(
            {
                "speaker_id": speaker.get("speaker_id"),
                "segment_count": speaker.get("segment_count"),
                "total_speech_sec": speaker.get("total_speech_sec"),
                "reference_audio_path": candidate.get("path") if auto_use and usable else None,
                "reference_candidate_path": candidate.get("path"),
                "reference_candidate_usable": usable,
                "selected_tts_voice": "per-speaker-reference" if auto_use and usable else None,
                "selection_reason": (
                    "Extracted reference candidate selected because automatic XTTS reference use is enabled."
                    if auto_use and usable
                    else "Reference candidate recorded but not automatically used for XTTS."
                ),
                "override_supported": True,
            }
        )
    warnings = ["XTTS is speaker-reference voice, not guaranteed exact identity cloning."]
    if len(speakers) > 1 and missing_refs:
        warnings.append("Multiple speakers detected but per-speaker references are missing or not enabled for automatic XTTS use.")
    plan = {
        "status": "computed",
        "target_language": target_language,
        "voice_backend": "xtts",
        "speakers": speakers,
        "warnings": warnings,
        "errors": [],
    }
    if output_path:
        write_json(output_path, plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Build VideoLingua speaker-analysis artifacts.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--asr-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--voice-backend", default="sarvam")
    parser.add_argument("--enriched-asr-output")
    args = parser.parse_args()
    report = run_speaker_analysis(
        audio=args.audio,
        asr_json=args.asr_json,
        output_dir=args.output_dir,
        target_language=args.target_language,
        voice_backend=args.voice_backend,
        enriched_asr_output=args.enriched_asr_output,
    )
    if report.get("status") == "failed" and _env_bool("VIDIOLINGUA_FAIL_ON_DIARIZATION_ERROR"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
