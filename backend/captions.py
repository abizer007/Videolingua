"""Generate source-language caption sidecars from ASR JSON.

This module only formats the original ASR transcript into WebVTT/SRT. It does
not translate, score, or alter the transcript.
"""

from __future__ import annotations

from dataclasses import dataclass
import html
import json
from pathlib import Path
import textwrap
from typing import Any


@dataclass
class CaptionArtifact:
    format: str
    path: Path


@dataclass
class CaptionGenerationResult:
    requested: bool
    generated: bool
    language_code: str | None
    cue_count: int
    artifacts: list[CaptionArtifact]
    warnings: list[str]


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _format_timestamp(seconds: float, *, separator: str) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{ms:03d}"


def _readable_lines(text: str) -> list[str]:
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return []
    return textwrap.wrap(normalized, width=42, break_long_words=False, break_on_hyphens=False) or [normalized]


def _webvtt_text(text: str) -> str:
    return "\n".join(html.escape(line.replace("-->", "->"), quote=False) for line in _readable_lines(text))


def _srt_text(text: str) -> str:
    return "\n".join(_readable_lines(text))


def _iter_valid_cues(payload: dict[str, Any], warnings: list[str]) -> list[dict[str, Any]]:
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        warnings.append("ASR JSON does not contain a segments array.")
        return []

    cues: list[dict[str, Any]] = []
    for index, segment in enumerate(raw_segments, start=1):
        if not isinstance(segment, dict):
            warnings.append(f"Skipped segment {index}: segment is not an object.")
            continue
        start = _as_float(segment.get("start"))
        end = _as_float(segment.get("end"))
        text = str(segment.get("text") or "").strip()
        if start is None or end is None or end <= start:
            warnings.append(f"Skipped segment {index}: missing or invalid timestamps.")
            continue
        if not text:
            continue
        cues.append({"start": start, "end": end, "text": text})
    return cues


def generate_source_captions_from_asr(
    asr_json_path: str | Path | None,
    output_dir: str | Path,
    *,
    basename: str = "source_original",
) -> CaptionGenerationResult:
    """Create WebVTT and SRT captions from source-language ASR segments."""
    warnings: list[str] = []
    if not asr_json_path:
        return CaptionGenerationResult(False, False, None, 0, [], ["ASR JSON path was not provided."])

    source = Path(asr_json_path)
    if not source.is_file():
        return CaptionGenerationResult(False, False, None, 0, [], [f"ASR JSON not found: {source}"])

    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        return CaptionGenerationResult(False, False, None, 0, [], [f"Could not read ASR JSON: {exc}"])
    if not isinstance(payload, dict):
        return CaptionGenerationResult(False, False, None, 0, [], ["ASR JSON root is not an object."])

    cues = _iter_valid_cues(payload, warnings)
    if not cues:
        warnings.append("No non-empty ASR segments with valid timestamps were available for captions.")

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    vtt_path = target / f"{basename}.vtt"
    srt_path = target / f"{basename}.srt"

    vtt_blocks = ["WEBVTT", ""]
    srt_blocks: list[str] = []
    for cue_number, cue in enumerate(cues, start=1):
        vtt_blocks.extend(
            [
                f"{_format_timestamp(cue['start'], separator='.')} --> {_format_timestamp(cue['end'], separator='.')}",
                _webvtt_text(cue["text"]),
                "",
            ]
        )
        srt_blocks.extend(
            [
                str(cue_number),
                f"{_format_timestamp(cue['start'], separator=',')} --> {_format_timestamp(cue['end'], separator=',')}",
                _srt_text(cue["text"]),
                "",
            ]
        )

    vtt_path.write_text("\n".join(vtt_blocks).rstrip() + "\n", encoding="utf-8")
    srt_path.write_text("\n".join(srt_blocks).rstrip() + ("\n" if srt_blocks else ""), encoding="utf-8")
    return CaptionGenerationResult(
        requested=True,
        generated=bool(cues),
        language_code=str(payload.get("language") or "").strip() or None,
        cue_count=len(cues),
        artifacts=[
            CaptionArtifact(format="vtt", path=vtt_path),
            CaptionArtifact(format="srt", path=srt_path),
        ],
        warnings=warnings,
    )
