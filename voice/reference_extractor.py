"""Backend-supported reference-audio extraction from source video."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from voice.audio_validation import (
    AudioValidationError,
    analyze_audio,
    validate_reference_audio,
)


class ReferenceExtractionError(RuntimeError):
    """Raised when automatic reference extraction cannot produce usable audio."""


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except (TypeError, ValueError):
        return 0.0


def _load_asr_segments(asr_json_paths: list[str | Path]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for raw_path in asr_json_paths:
        path = Path(raw_path)
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for segment in data.get("segments", []):
            if not isinstance(segment, dict):
                continue
            text = str(segment.get("text") or "").strip()
            try:
                start = float(segment.get("start", 0.0))
                end = float(segment.get("end", start))
            except (TypeError, ValueError):
                continue
            duration = end - start
            if text and duration >= 0.75:
                segments.append(
                    {
                        "start": max(0.0, start),
                        "end": max(start, end),
                        "duration": duration,
                        "text": text,
                    }
                )
    return sorted(segments, key=lambda item: item["start"])


def _choose_asr_window(segments: list[dict[str, Any]]) -> tuple[float, float, str]:
    if not segments:
        raise ReferenceExtractionError("No ASR speech segments are available for reference extraction.")

    best: tuple[float, float, float] | None = None
    for index, segment in enumerate(segments):
        start = float(segment["start"])
        end = float(segment["end"])
        total = max(0.0, end - start)
        last_end = end
        for next_segment in segments[index + 1 :]:
            gap = float(next_segment["start"]) - last_end
            if gap > 1.5:
                break
            end = float(next_segment["end"])
            total = end - start
            last_end = end
            if total >= 20.0:
                break
        score = min(total, 20.0)
        if total >= 6.0 and (best is None or score > best[2]):
            best = (start, min(total, 20.0), score)

    if best is not None:
        return best[0], best[1], "asr_segments"

    longest = max(segments, key=lambda item: item["duration"])
    start = max(0.0, float(longest["start"]) - 0.25)
    duration = min(12.0, max(6.0, float(longest["duration"]) + 0.5))
    return start, duration, "asr_longest_segment"


def _choose_fallback_window(video_path: Path) -> tuple[float, float, str]:
    duration = _probe_duration(video_path)
    if duration <= 0:
        return 0.0, 12.0, "fallback_start"
    clip_duration = min(12.0, max(6.0, duration * 0.4))
    start = max(0.0, min(duration * 0.25, duration - clip_duration))
    return start, clip_duration, "fallback_early_middle"


def _extract_wav(video_path: Path, output_path: Path, start_s: float, duration_s: float) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filters = [
        "highpass=f=70,lowpass=f=7600,loudnorm=I=-18:TP=-3:LRA=11",
        "highpass=f=70,lowpass=f=7600,volume=0.95",
    ]
    last_error = ""
    for audio_filter in filters:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{max(0.0, start_s):.3f}",
                "-i",
                str(video_path),
                "-t",
                f"{max(0.2, duration_s):.3f}",
                "-vn",
                "-af",
                audio_filter,
                "-acodec",
                "pcm_s16le",
                "-ar",
                "22050",
                "-ac",
                "1",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 2048:
            return
        last_error = (result.stderr or result.stdout or "").strip()
    raise ReferenceExtractionError(f"ffmpeg could not extract usable reference audio: {last_error}")


def extract_reference_audio(
    video_path: str | Path,
    output_dir: str | Path,
    *,
    asr_json_paths: list[str | Path] | None = None,
    min_duration_s: float = 6.0,
    max_duration_s: float = 30.0,
    output_filename: str = "auto_reference_candidate.wav",
) -> dict[str, Any]:
    """Extract a validated XTTS reference WAV into a job-local reference folder."""
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    if not video_path.is_file():
        raise ReferenceExtractionError(f"Source video does not exist: {video_path}")

    segments = _load_asr_segments(asr_json_paths or [])
    try:
        start_s, duration_s, source = _choose_asr_window(segments)
    except ReferenceExtractionError:
        start_s, duration_s, source = _choose_fallback_window(video_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / output_filename
    metadata_path = output_dir / "auto_reference_metadata.json"
    _extract_wav(video_path, wav_path, start_s, duration_s)

    validation_passed = False
    validation_error = ""
    try:
        stats = validate_reference_audio(
            wav_path,
            min_duration_s=min_duration_s,
            max_duration_s=max_duration_s,
        )
        validation_passed = True
    except AudioValidationError as exc:
        validation_error = str(exc)
        stats = analyze_audio(wav_path)

    metadata: dict[str, Any] = {
        "mode": "auto_extract",
        "path": str(wav_path),
        "metadata_path": str(metadata_path),
        "source": source,
        "start_sec": round(start_s, 3),
        "requested_duration_sec": round(duration_s, 3),
        "duration_sec": round(stats.duration_s, 3),
        "sample_rate": stats.sample_rate,
        "channels": stats.channels,
        "peak": round(stats.peak, 6),
        "rms": round(stats.rms, 6),
        "silence_ratio": round(stats.silence_ratio, 6),
        "clipping_ratio": round(stats.clipping_ratio, 6),
        "validation_passed": validation_passed,
        "validation_error": validation_error or None,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if not validation_passed:
        raise ReferenceExtractionError(
            "Automatic reference extraction failed validation. "
            "Upload a clean 6-30 second reference clip. "
            f"Validation error: {validation_error}"
        )

    return metadata
