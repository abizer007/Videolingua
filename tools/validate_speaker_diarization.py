"""Validate diarization without running the full pipeline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _asr_python() -> str:
    configured = os.environ.get("VIDIOLINGUA_ASR_PYTHON", "").strip()
    if configured and Path(configured).is_file():
        return configured
    candidate = PROJECT_ROOT / ".venv_asr" / "Scripts" / "python.exe"
    return str(candidate) if candidate.is_file() else sys.executable


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pyannote diarization validation.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    _load_env_file(PROJECT_ROOT / ".env")
    _load_env_file(PROJECT_ROOT / "backend" / ".env")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _asr_python(),
        "-m",
        "speaker_analysis.diarization",
        "--audio",
        str(Path(args.audio)),
        "--output",
        str(output),
    ]
    env = os.environ.copy()
    env.setdefault("PYANNOTE_METRICS_ENABLED", "0")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, text=True, encoding="utf-8", errors="replace")
    if output.is_file():
        payload = json.loads(output.read_text(encoding="utf-8"))
        print(
            "[validate_speaker_diarization] "
            f"status={payload.get('status')} speaker_count={payload.get('speaker_count')} "
            f"turns={len(payload.get('turns') or [])} output={output}"
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
