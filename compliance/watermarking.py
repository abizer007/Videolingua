"""Optional visible disclosure copy generation."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def apply_visible_disclosure(
    *,
    input_video_path: str | Path | None,
    output_video_path: str | Path,
    disclosure_text: str,
) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if not input_video_path:
        warnings.append("No input video path was provided for visible disclosure.")
        return False, warnings
    source = Path(input_video_path)
    target = Path(output_video_path)
    if not source.is_file():
        warnings.append(f"Visible disclosure source does not exist: {source}")
        return False, warnings
    target.parent.mkdir(parents=True, exist_ok=True)
    safe_text = disclosure_text.replace("'", "").replace(":", "\\:")
    drawtext = (
        "drawtext="
        f"text='{safe_text}'"
        ":x=24:y=24:fontsize=24:fontcolor=white:"
        "box=1:boxcolor=black@0.55:boxborderw=12"
    )
    command = ["ffmpeg", "-y", "-i", str(source), "-vf", drawtext, "-codec:a", "copy", str(target)]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        warnings.append(f"ffmpeg visible disclosure failed: {exc}")
        return False, warnings
    if result.returncode != 0 or not target.is_file():
        warnings.append("ffmpeg drawtext failed; created no disclosed copy.")
        warnings.append((result.stderr or result.stdout or "").strip()[:800])
        return False, warnings
    try:
        shutil.copystat(source, target)
    except OSError:
        pass
    return True, warnings
