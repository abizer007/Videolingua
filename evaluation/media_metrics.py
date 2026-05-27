"""Media metrics from ffprobe."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _fps(value: str | None) -> float | None:
    if not value:
        return None
    if "/" not in value:
        try:
            return round(float(value), 3)
        except ValueError:
            return None
    numerator, denominator = value.split("/", 1)
    try:
        denominator_f = float(denominator)
        if denominator_f == 0:
            return None
        return round(float(numerator) / denominator_f, 3)
    except ValueError:
        return None


def probe_media(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {"status": "missing_artifact", "mp4_exists": False, "reason": "No MP4 path was found."}
    path = Path(path)
    if not path.is_file():
        return {"status": "missing_artifact", "mp4_exists": False, "reason": f"MP4 does not exist: {path}"}

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return {
            "status": "error",
            "mp4_exists": True,
            "path": str(path),
            "reason": (result.stderr or result.stdout or "").strip(),
        }
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"status": "error", "mp4_exists": True, "path": str(path), "reason": str(exc)}

    streams = data.get("streams") or []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    fmt = data.get("format") or {}

    report: dict[str, Any] = {
        "status": "computed",
        "path": str(path),
        "mp4_exists": True,
        "video_stream_exists": bool(video_stream),
        "audio_stream_exists": bool(audio_stream),
        "size_bytes": path.stat().st_size,
        "validation_passed": bool(video_stream and audio_stream),
    }
    try:
        report["duration_sec"] = round(float(fmt.get("duration")), 3)
    except (TypeError, ValueError):
        pass
    try:
        report["size_bytes"] = int(fmt.get("size") or report["size_bytes"])
    except (TypeError, ValueError):
        pass
    if video_stream:
        report["video_codec"] = video_stream.get("codec_name")
        width = video_stream.get("width")
        height = video_stream.get("height")
        if width and height:
            report["resolution"] = f"{width}x{height}"
        fps = _fps(str(video_stream.get("avg_frame_rate") or ""))
        if fps is not None:
            report["fps"] = fps
    if audio_stream:
        report["audio_codec"] = audio_stream.get("codec_name")
        try:
            report["audio_sample_rate"] = int(audio_stream.get("sample_rate") or 0)
        except (TypeError, ValueError):
            report["audio_sample_rate"] = audio_stream.get("sample_rate")
        report["audio_channels"] = audio_stream.get("channels")
    return report

