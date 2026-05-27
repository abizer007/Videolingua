"""Lightweight VideoLingua runtime readiness checks.

This script avoids model downloads, model loads, long inference, server startup,
and frontend builds. It only checks filesystem layout, Python runtimes, imports,
configured model paths, and basic media tooling.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


_load_env_file(PROJECT_ROOT / ".env")
_load_env_file(PROJECT_ROOT / "backend" / ".env")


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    status: str = "ready"


@dataclass
class EnvReport:
    ok: bool
    checks: list[Check] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _run(cmd: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _python_from_env(env_var: str, default_venv: str) -> Path:
    configured = os.environ.get(env_var, "").strip()
    if configured:
        return Path(configured)
    return PROJECT_ROOT / default_venv / "Scripts" / "python.exe"


def _normalize_xtts_model_dir(path: Path) -> Path:
    path = Path(path)
    if path.name.lower() == "model.pth" or path.suffix.lower() == ".pth":
        return path.parent
    return path


def _find_xtts_checkpoint(root: Path) -> Path | None:
    exact = root / "model.pth"
    if exact.is_file():
        return exact
    for candidate in sorted(root.glob("*.pth")):
        name = candidate.name.lower()
        if name.startswith("speakers") or name == "speakers_xtts.pth":
            continue
        return candidate
    return None


def _check_python(name: str, env_var: str, default_venv: str, optional: bool = False) -> Check:
    py = _python_from_env(env_var, default_venv)
    if not py.is_file():
        return Check(name, optional, f"missing python: {py}", "optional" if optional else "blocked")
    r = _run([str(py), "--version"])
    if r.returncode != 0:
        return Check(name, False, (r.stderr or r.stdout).strip(), "broken")
    return Check(name, True, f"{py} | {(r.stdout or r.stderr).strip()}")


def _check_import(name: str, py: Path, module: str, import_code: str | None = None, timeout: int = 90) -> Check:
    if not py.is_file():
        return Check(name, False, f"missing python: {py}", "blocked")
    code = import_code or f"import {module}; print('ok')"
    try:
        r = _run([str(py), "-c", code], timeout=timeout)
    except subprocess.TimeoutExpired:
        return Check(name, False, f"import timed out after {timeout}s", "blocked")
    if r.returncode != 0:
        msg = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["import failed"]
        return Check(name, False, msg[0], "missing")
    return Check(name, True, (r.stdout or "ok").strip())


def _check_xtts_model() -> Check:
    model_path = (
        os.environ.get("VIDIOLINGUA_XTTS_MODEL_PATH")
        or os.environ.get("XTTS_MODEL_PATH")
        or os.environ.get("COQUI_XTTS_MODEL_PATH")
        or ""
    ).strip()
    if not model_path:
        default_root = PROJECT_ROOT / "models" / "xtts_v2"
        model_path = str(default_root) if default_root.exists() else ""
    if not model_path:
        return Check("XTTS model files", False, "VIDIOLINGUA_XTTS_MODEL_PATH is not set and models\\xtts_v2 was not found", "blocked")
    root = _normalize_xtts_model_dir(Path(model_path))
    if not root.is_dir():
        return Check("XTTS model files", False, f"directory not found: {root}", "blocked")
    config_path = root / "config.json"
    checkpoint_path = _find_xtts_checkpoint(root)
    vocab_path = root / "vocab.json"
    tokenizer_path = root / "tokenizer.json"
    speakers_path = root / "speakers_xtts.pth"
    missing: list[str] = []
    if not config_path.is_file():
        missing.append("config.json")
    if not checkpoint_path:
        missing.append("model.pth or another .pth checkpoint")
    if not (vocab_path.is_file() or tokenizer_path.is_file()):
        missing.append("vocab.json or tokenizer.json")
    if missing:
        return Check("XTTS model files", False, f"{root} missing: {', '.join(missing)}", "blocked")
    detail = {
        "model_dir": str(root),
        "config_path": str(config_path),
        "checkpoint_path": str(checkpoint_path),
        "vocab_path": str(vocab_path if vocab_path.is_file() else tokenizer_path),
        "speakers_path": str(speakers_path) if speakers_path.is_file() else "",
    }
    return Check("XTTS model files", True, json.dumps(detail, sort_keys=True))


def _check_video(video: str) -> Check:
    path = PROJECT_ROOT / video
    if not path.is_file():
        return Check("official video", False, f"missing: {path}", "blocked")
    r = _run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    if r.returncode != 0:
        return Check("official video", False, (r.stderr or r.stdout).strip(), "broken")
    return Check("official video", True, f"duration_s={r.stdout.strip()}")


def _check_frontend() -> list[Check]:
    pkg = PROJECT_ROOT / "frontend-next" / "package.json"
    old_pkg = PROJECT_ROOT / "frontend" / "package.json"
    checks = [Check("frontend-next package", pkg.is_file(), str(pkg), "ready" if pkg.is_file() else "blocked")]
    if old_pkg.is_file():
        checks.append(Check("legacy frontend", False, "frontend/ exists and is legacy/alternate; do not use for API parity", "legacy"))
    return checks


def _check_path_dir(name: str, env_var: str, required_file: str | None = None, optional: bool = True) -> Check:
    value = os.environ.get(env_var, "").strip()
    if not value:
        return Check(name, optional, f"{env_var} is not set", "optional" if optional else "blocked")
    root = Path(value)
    if not root.is_dir():
        return Check(name, False, f"directory not found: {root}", "blocked")
    if required_file and not (root / required_file).is_file():
        return Check(name, False, f"missing {required_file} in {root}", "blocked")
    return Check(name, True, str(root))


def build_report(video: str) -> EnvReport:
    checks: list[Check] = []
    warnings: list[str] = []
    blockers: list[str] = []

    checks.append(Check("ffmpeg", bool(shutil.which("ffmpeg")), shutil.which("ffmpeg") or "not on PATH"))
    checks.append(Check("ffprobe", bool(shutil.which("ffprobe")), shutil.which("ffprobe") or "not on PATH"))
    if checks[-1].ok:
        checks.append(_check_video(video))

    envs = {
        "API python": ("VIDIOLINGUA_API_PYTHON", ".venv_api"),
        "ASR python": ("VIDIOLINGUA_ASR_PYTHON", ".venv_asr"),
        "TTS python": ("VIDIOLINGUA_TTS_PYTHON", ".venv_tts"),
        "BGM python": ("VIDIOLINGUA_BGM_PYTHON", ".venv_bgm"),
        "MuseTalk python": ("VIDIOLINGUA_MUSETALK_PYTHON", ".venv_musetalk"),
        "GFPGAN python": ("VIDIOLINGUA_GFP_GAN_PYTHON", ".venv_gfpgan"),
    }
    for name, (env_var, default_venv) in envs.items():
        checks.append(_check_python(name, env_var, default_venv, optional=name in {"MuseTalk python", "GFPGAN python"}))

    api_py = _python_from_env("PYTHON_API", ".venv_api")
    asr_py = _python_from_env("VIDIOLINGUA_ASR_PYTHON", ".venv_asr")
    tts_py = _python_from_env("VIDIOLINGUA_TTS_PYTHON", ".venv_tts")
    bgm_py = _python_from_env("VIDIOLINGUA_BGM_PYTHON", ".venv_bgm")
    musetalk_py = _python_from_env("VIDIOLINGUA_MUSETALK_PYTHON", ".venv_musetalk")

    checks.extend(
        [
            _check_import("FastAPI import", api_py, "fastapi"),
            _check_import("Uvicorn import", api_py, "uvicorn"),
            _check_import("WhisperX import", asr_py, "whisperx"),
            _check_import("PyAnnote import", asr_py, "pyannote.audio", "import pyannote.audio; print('ok')", timeout=180),
            _check_import("Translation import", tts_py, "deep_translator", "from deep_translator import GoogleTranslator; print('ok')"),
            _check_import("Coqui TTS import", tts_py, "TTS.api", "from TTS.api import TTS; import torch; print('ok')", timeout=180),
            _check_import("Demucs import", bgm_py, "demucs", "import demucs; print('ok')"),
            _check_import(
                "TTS torch/CUDA status",
                tts_py,
                "torch",
                "import torch; print('torch=' + str(torch.__version__) + ' cuda=' + str(torch.cuda.is_available()) + ' cuda_version=' + str(torch.version.cuda) + ' gpu=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none'))",
                timeout=90,
            ),
        ]
    )

    musetalk_dir = os.environ.get("VIDIOLINGUA_MUSETALK_DIR", "").strip()
    if musetalk_dir:
        checks.append(_check_import("MuseTalk python core imports", musetalk_py, "cv2", "import cv2, numpy; print('ok')"))
    else:
        checks.append(Check("MuseTalk folder", True, "VIDIOLINGUA_MUSETALK_DIR is not set; practical mode will use ffmpeg mux fallback", "optional"))

    checks.append(_check_path_dir("GFPGAN folder", "VIDIOLINGUA_GFPGAN_DIR", "inference_gfpgan.py", optional=True))
    checks.append(_check_xtts_model())
    checks.extend(_check_frontend())

    if not os.environ.get("HUGGINGFACE_TOKEN", "").strip():
        warnings.append("HUGGINGFACE_TOKEN is not set; PyAnnote diarization will be skipped or fail if required.")

    for check in checks:
        if not check.ok and check.status == "blocked":
            blockers.append(f"{check.name}: {check.detail}")

    hard_failed = [c for c in checks if not c.ok and c.status not in {"optional", "legacy"}]
    return EnvReport(ok=not hard_failed, checks=checks, blockers=blockers, warnings=warnings)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check VideoLingua runtime readiness.")
    parser.add_argument("--video", default="Vidiolingua_Test_Official.mp4")
    parser.add_argument("--all", action="store_true", help="Accepted for the canonical full preflight command.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.video)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print("VideoLingua environment preflight")
        print(f"status: {'READY' if report.ok else 'BLOCKED'}")
        for check in report.checks:
            mark = "OK" if check.ok else check.status.upper()
            print(f"  [{mark}] {check.name}: {check.detail}")
        for warning in report.warnings:
            print(f"  warning: {warning}")
        for blocker in report.blockers:
            print(f"  blocker: {blocker}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
