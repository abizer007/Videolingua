"""Safe HuBERT prosody subprocess wrapper."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "facebook/hubert-base-ls960"


def prosody_python() -> Path | None:
    configured = os.environ.get("VIDIOLINGUA_PROSODY_PYTHON", "").strip()
    if configured and Path(configured).is_file():
        return Path(configured)
    candidate = PROJECT_ROOT / ".venv_prosody" / "Scripts" / "python.exe"
    if candidate.is_file():
        return candidate
    return None


def extract_hubert_features(
    *,
    audio_path: str | Path,
    segments: list[dict[str, Any]] | None = None,
    output_dir: str | Path,
    model_name: str = DEFAULT_MODEL,
    device: str = "auto",
    timeout_sec: int | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    request = {
        "audio_path": str(audio_path),
        "segments": segments or [],
        "model_name": model_name,
        "device": device,
        "output_dir": str(output),
    }
    request_path = output / "hubert_request.json"
    response_path = output / "hubert_features.json"
    request_path.write_text(json.dumps(request, indent=2, ensure_ascii=False), encoding="utf-8")
    python = prosody_python()
    if python is None:
        response = {
            "status": "unavailable",
            "model": model_name,
            "embedding_dim": None,
            "segment_embeddings": [],
            "global_embedding_path": None,
            "warnings": [".venv_prosody is not available; HuBERT extraction was skipped."],
            "errors": [],
        }
        response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")
        return response
    cmd = [
        str(python),
        str(PROJECT_ROOT / "workers" / "hubert_prosody_worker.py"),
        "--request",
        str(request_path),
        "--response",
        str(response_path),
    ]
    if timeout_sec is None:
        raw_timeout = os.environ.get("VIDIOLINGUA_HUBERT_TIMEOUT_SEC", "90").strip()
        try:
            timeout_sec = max(5, int(float(raw_timeout)))
        except ValueError:
            timeout_sec = 90
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        response = {
            "status": "unavailable",
            "model": model_name,
            "embedding_dim": None,
            "segment_embeddings": [],
            "global_embedding_path": None,
            "warnings": [f"HuBERT extraction exceeded {timeout_sec}s and was skipped for this run."],
            "errors": [],
        }
        response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")
        return response
    if result.returncode != 0:
        if response_path.is_file():
            try:
                return json.loads(response_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        response = {
            "status": "failed",
            "model": model_name,
            "embedding_dim": None,
            "segment_embeddings": [],
            "global_embedding_path": None,
            "warnings": [],
            "errors": [(result.stderr or result.stdout or f"exit code {result.returncode}").strip()],
        }
        response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")
        return response
    if response_path.is_file():
        return json.loads(response_path.read_text(encoding="utf-8"))
    return {
        "status": "failed",
        "model": model_name,
        "embedding_dim": None,
        "segment_embeddings": [],
        "global_embedding_path": None,
        "warnings": [],
        "errors": ["HuBERT worker completed without writing a response."],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Extract HuBERT prosody features via isolated worker.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--segments-json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    segments: list[dict[str, Any]] = []
    if args.segments_json:
        data = json.loads(Path(args.segments_json).read_text(encoding="utf-8"))
        raw = data.get("segments") if isinstance(data, dict) else data
        if isinstance(raw, list):
            segments = [item for item in raw if isinstance(item, dict)]
    response = extract_hubert_features(
        audio_path=args.audio,
        segments=segments,
        output_dir=args.output_dir,
        model_name=args.model_name,
        device=args.device,
    )
    print(json.dumps(response, indent=2, ensure_ascii=False))
    return 0 if response.get("status") in {"computed", "partial", "unavailable"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
