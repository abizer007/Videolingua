"""Shared helpers for compliance sidecar reports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import uuid
from typing import Any


DISCLOSURE_TEXT = "AI-generated dubbed audio / synthetic localization"
AUDIO_DISCLOSURE_TEXT = "This audio is synthetically generated."


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def env_true(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def compliance_mode(default: str = "report_only") -> str:
    mode = os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", default).strip().lower()
    return "strict" if mode == "strict" else "report_only"


def responsible_ai_enabled() -> bool:
    return env_true("VIDIOLINGUA_ENABLE_RESPONSIBLE_AI", True)


def ensure_compliance_dir(job_dir: str | Path, output_dir: str | Path | None = None) -> Path:
    base = Path(output_dir) if output_dir else Path(job_dir)
    compliance_dir = base / "compliance"
    compliance_dir.mkdir(parents=True, exist_ok=True)
    return compliance_dir


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def read_json(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        target = Path(path)
        if not target.is_file():
            return None
        data = json.loads(target.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def relpath(path: str | Path | None, base: str | Path | None = None) -> str | None:
    if not path:
        return None
    p = Path(path)
    if base:
        try:
            return str(p.resolve().relative_to(Path(base).resolve()))
        except (OSError, ValueError):
            pass
    return str(p)


def parse_boolish(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return None


def find_first(paths: list[Path]) -> Path | None:
    for path in paths:
        if path and path.is_file():
            return path
    return None


def probe_duration(path: str | Path | None) -> float | None:
    if not path:
        return None
    target = Path(path)
    if not target.is_file():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(target),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return round(float((result.stdout or "").strip()), 3)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def delete_after_iso(retention_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=max(0, retention_days))).isoformat()


def collect_text_from_json(path: str | Path | None, keys: tuple[str, ...] = ("text", "translated_text", "translation")) -> str:
    data = read_json(path)
    if not data:
        return ""
    pieces: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in keys and isinstance(item, str):
                    pieces.append(item)
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    return " ".join(piece.strip() for piece in pieces if piece and piece.strip())
