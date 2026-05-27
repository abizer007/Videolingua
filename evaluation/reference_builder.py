"""Discover pipeline artifacts and reference material for automatic evaluation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from evaluation.text_metrics import join_segment_text, normalize_text


def read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_text(path: Path | None) -> str:
    if not path or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def first_file(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.is_file()), None)


def discover_artifacts(job_dir: str | Path) -> dict[str, Any]:
    job_dir = Path(job_dir)
    asr_jsons = sorted((job_dir / "asr" / "output").glob("*.json"))
    translation_jsons = sorted((job_dir / "translation" / "output").glob("*.json"))
    tts_wavs = sorted((job_dir / "tts" / "output").glob("*.wav"))
    final_mp4s = sorted((job_dir / "results").glob("*_dubbed_*.mp4"))
    if not final_mp4s:
        final_mp4s = sorted(path for path in (job_dir / "results").glob("*.mp4") if path.name != "input_video.mp4")
    input_videos = sorted((job_dir / "asr" / "input").glob("*.mp4"))
    if (job_dir / "results" / "input_video.mp4").is_file():
        input_videos.insert(0, job_dir / "results" / "input_video.mp4")
    if (job_dir / "input_video.mp4").is_file():
        input_videos.insert(0, job_dir / "input_video.mp4")

    reference_audio_candidates = [
        job_dir / "voice_sample.wav",
        job_dir / "outputs" / "intermediate" / "reference_clean.wav",
        job_dir / "outputs" / "intermediate" / "best_voice_segment.wav",
    ]
    reference_audio_candidates.extend(sorted((job_dir / "evaluation").glob("*reference*.wav")))

    return {
        "job_dir": job_dir,
        "pipeline_result": job_dir / "pipeline_result.json",
        "asr_jsons": asr_jsons,
        "asr_json": first_file(asr_jsons),
        "translation_jsons": translation_jsons,
        "translation_json": first_file(translation_jsons),
        "tts_wavs": tts_wavs,
        "tts_wav": first_file(tts_wavs),
        "final_mp4s": final_mp4s,
        "final_mp4": first_file(final_mp4s),
        "input_video": first_file(input_videos),
        "ground_truth_transcript": job_dir / "evaluation" / "ground_truth_transcript.txt",
        "reference_translation": job_dir / "evaluation" / "reference_translation.txt",
        "human_quality": job_dir / "evaluation" / "human_quality.json",
        "reference_audio": first_file(reference_audio_candidates),
    }


_TIMECODE_RE = re.compile(
    r"^\s*(?:\d+\s*)?(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3}\s+-->\s+(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3}"
)


def clean_subtitle_text(raw: str) -> str:
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.upper() == "WEBVTT":
            continue
        if stripped.isdigit() or _TIMECODE_RE.match(stripped):
            continue
        if stripped.startswith(("NOTE", "STYLE", "REGION")):
            continue
        lines.append(re.sub(r"<[^>]+>", "", stripped))
    return normalize_text(" ".join(lines))


def _sidecar_transcript(job_dir: Path, input_video: Path | None) -> tuple[str, str | None]:
    candidates: list[Path] = []
    if input_video:
        for suffix in (".srt", ".vtt", ".txt"):
            candidates.append(input_video.with_suffix(suffix))
    candidates.extend(sorted((job_dir / "evaluation").glob("*transcript*.srt")))
    candidates.extend(sorted((job_dir / "evaluation").glob("*transcript*.vtt")))
    candidates.extend(path for path in sorted((job_dir / "evaluation").glob("*transcript*.txt")) if path.name != "ground_truth_transcript.txt")
    for path in candidates:
        raw = read_text(path)
        if raw:
            return (clean_subtitle_text(raw) if path.suffix.lower() in {".srt", ".vtt"} else raw, str(path))
    return "", None


def _avg_word_confidence(data: dict[str, Any]) -> float | None:
    scores: list[float] = []
    for segment in data.get("segments") or []:
        if not isinstance(segment, dict):
            continue
        for word in segment.get("words") or []:
            if not isinstance(word, dict):
                continue
            try:
                scores.append(float(word.get("score")))
            except (TypeError, ValueError):
                continue
    if not scores:
        return None
    return sum(scores) / len(scores)


def build_reference_context(artifacts: dict[str, Any]) -> dict[str, Any]:
    job_dir = artifacts["job_dir"]
    asr_jsons: list[Path] = artifacts.get("asr_jsons") or []
    translation_jsons: list[Path] = artifacts.get("translation_jsons") or []
    primary_asr = read_json(artifacts.get("asr_json"))
    primary_translation = read_json(artifacts.get("translation_json"))

    true_transcript = read_text(artifacts.get("ground_truth_transcript"))
    true_transcript_source = str(artifacts.get("ground_truth_transcript")) if true_transcript else None
    if not true_transcript:
        true_transcript, true_transcript_source = _sidecar_transcript(job_dir, artifacts.get("input_video"))

    asr_candidates: list[dict[str, Any]] = []
    for path in asr_jsons:
        data = read_json(path)
        text = join_segment_text(data.get("segments") or [])
        if text:
            asr_candidates.append(
                {
                    "path": str(path),
                    "text": text,
                    "normalized": normalize_text(text),
                    "avg_word_confidence": _avg_word_confidence(data),
                }
            )
    unique_asr = {candidate["normalized"]: candidate for candidate in asr_candidates}
    auto_consensus = None
    if len(unique_asr) >= 2:
        auto_consensus = max(
            unique_asr.values(),
            key=lambda item: item["avg_word_confidence"] if item["avg_word_confidence"] is not None else 0.0,
        )

    auto_translation = None
    for path in translation_jsons:
        data = read_json(path)
        for key in ("auto_reference_translation", "evaluator_translation", "independent_translation"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                auto_translation = {"text": value.strip(), "path": str(path), "field": key}
                break
        if auto_translation:
            break

    return {
        "asr_data": primary_asr,
        "translation_data": primary_translation,
        "true_transcript": true_transcript,
        "true_transcript_source": true_transcript_source,
        "auto_consensus_transcript": auto_consensus,
        "reference_translation": read_text(artifacts.get("reference_translation")),
        "reference_translation_source": str(artifacts.get("reference_translation")) if read_text(artifacts.get("reference_translation")) else None,
        "auto_reference_translation": auto_translation,
    }
