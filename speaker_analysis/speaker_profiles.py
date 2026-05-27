"""Speaker profile summaries and safe reference-candidate extraction."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def build_speaker_profiles(
    mapping_payload: dict[str, Any],
    *,
    reference_candidates: dict[str, dict[str, Any]] | None = None,
    visual_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if mapping_payload.get("status") != "computed":
        return {
            "status": mapping_payload.get("status", "unavailable"),
            "speaker_count": None,
            "speakers": [],
            "warnings": ["Speaker profiles unavailable because speaker mapping was not computed."],
            "errors": list(mapping_payload.get("errors") or []),
        }

    grouped: dict[str, dict[str, Any]] = {}
    for segment in mapping_payload.get("segments") or []:
        if not isinstance(segment, dict):
            continue
        speaker_id = str(segment.get("speaker_id") or "unknown")
        if speaker_id == "unknown":
            continue
        entry = grouped.setdefault(
            speaker_id,
            {
                "speaker_id": speaker_id,
                "segment_count": 0,
                "total_speech_sec": 0.0,
                "reference_audio_path": None,
                "voice_profile_hint": "unknown",
                "voice_profile_confidence": "low",
                "voice_profile_method": "unknown",
                "confidence": "low",
                "hint_source": "unknown",
                "warnings": [],
            },
        )
        entry["segment_count"] += 1
        entry["total_speech_sec"] += max(0.0, float(segment.get("end", 0.0)) - float(segment.get("start", 0.0)))

    reference_candidates = reference_candidates or {}
    for speaker_id, entry in grouped.items():
        candidate = reference_candidates.get(speaker_id)
        if candidate:
            entry["reference_audio_path"] = candidate.get("path")
            entry["reference_candidate"] = candidate
        if visual_report and visual_report.get("status") not in {"computed", "face_presence_detected"}:
            entry["warnings"].append("No reliable visual voice-profile model available; profile hint remains unknown.")
        entry["total_speech_sec"] = round(float(entry["total_speech_sec"]), 3)

    return {
        "status": "computed",
        "speaker_count": len(grouped),
        "speakers": sorted(grouped.values(), key=lambda item: item["speaker_id"]),
        "warnings": [],
        "errors": [],
    }


def _run_ffmpeg_extract(source: Path, start: float, duration: float, output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for speaker reference extraction but was not found.")
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "22050",
        "-ac",
        "1",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def _concat_wavs(clips: list[Path], output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for speaker reference concatenation but was not found.")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
        list_path = Path(handle.name)
        for clip in clips:
            safe = str(clip.resolve()).replace("'", "'\\''")
            handle.write(f"file '{safe}'\n")
    try:
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
    finally:
        list_path.unlink(missing_ok=True)


def extract_reference_candidates(
    source_audio_or_video: str | Path,
    diarization_payload: dict[str, Any],
    output_dir: str | Path,
    *,
    min_total_sec: float = 5.0,
    max_total_sec: float = 20.0,
    min_turn_sec: float = 1.0,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if diarization_payload.get("status") != "computed":
        return {
            "status": diarization_payload.get("status", "unavailable"),
            "references": {},
            "warnings": ["Reference extraction unavailable because diarization was not computed."],
            "errors": list(diarization_payload.get("errors") or []),
        }

    source = Path(source_audio_or_video)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for turn in diarization_payload.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        start = float(turn.get("start", 0.0))
        end = float(turn.get("end", start))
        duration = max(0.0, end - start)
        if duration >= min_turn_sec:
            grouped.setdefault(str(turn.get("speaker_id")), []).append({"start": start, "end": end, "duration": duration})

    references: dict[str, Any] = {}
    warnings: list[str] = []
    for speaker_id, turns in grouped.items():
        selected: list[dict[str, Any]] = []
        total = 0.0
        for turn in sorted(turns, key=lambda item: item["duration"], reverse=True):
            if total >= max_total_sec:
                break
            remaining = max_total_sec - total
            duration = min(float(turn["duration"]), remaining)
            if duration <= 0:
                continue
            selected.append({"start": float(turn["start"]), "end": float(turn["start"]) + duration, "duration": duration})
            total += duration
        speaker_dir = output_dir / speaker_id
        speaker_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = output_dir / f"{speaker_id}_reference_candidate.wav"
        try:
            clips: list[Path] = []
            for index, turn in enumerate(selected):
                clip_path = speaker_dir / f"clip_{index:03d}.wav"
                _run_ffmpeg_extract(source, turn["start"], turn["duration"], clip_path)
                clips.append(clip_path)
            if clips:
                if len(clips) == 1:
                    shutil.copy2(clips[0], candidate_path)
                else:
                    _concat_wavs(clips, candidate_path)
            usable = total >= min_total_sec and candidate_path.is_file()
            if not usable:
                warnings.append(f"{speaker_id} has only {total:.2f}s of candidate speech; XTTS reference use is not recommended.")
            references[speaker_id] = {
                "speaker_id": speaker_id,
                "path": str(candidate_path) if candidate_path.is_file() else None,
                "duration_sec": round(total, 3),
                "source_time_ranges": [{"start": round(item["start"], 3), "end": round(item["end"], 3)} for item in selected],
                "quality_status": "usable" if usable else "too_short",
                "usable_for_xtts": usable,
                "usable_for_sarvam_profile": bool(candidate_path.is_file()),
            }
        except Exception as exc:
            references[speaker_id] = {
                "speaker_id": speaker_id,
                "path": None,
                "duration_sec": round(total, 3),
                "source_time_ranges": [{"start": round(item["start"], 3), "end": round(item["end"], 3)} for item in selected],
                "quality_status": "failed",
                "usable_for_xtts": False,
                "usable_for_sarvam_profile": False,
                "error": str(exc),
            }
            warnings.append(f"Reference candidate extraction failed for {speaker_id}: {exc}")

    report = {
        "status": "computed",
        "references": references,
        "warnings": warnings,
        "errors": [],
    }
    metadata_path = output_dir / "speaker_reference_candidates.json"
    metadata_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report
