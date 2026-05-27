"""Validate Wav2Lip runtime readiness without running generation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WAV2LIP_DIR = PROJECT_ROOT / "ml" / "Wav2Lip"
DEFAULT_CHECKPOINT = DEFAULT_WAV2LIP_DIR / "checkpoints" / "wav2lip_gan.pth"
REQUIRED_MODULES = ("numpy", "torch", "cv2", "scipy")


def _read_local_env_value(key: str) -> str:
    """Read only the requested key from local env files without exposing secrets."""
    for env_path in (PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"):
        if not env_path.is_file():
            continue
        try:
            for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                item_key, value = line.split("=", 1)
                if item_key.strip() == key:
                    return value.strip().strip('"').strip("'")
        except OSError:
            continue
    return ""


def _env_value(key: str) -> str:
    return os.environ.get(key, "").strip() or _read_local_env_value(key)


def _candidate_python_paths(explicit_python: str | None = None) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    if explicit_python:
        candidates.append(("argument", Path(explicit_python)))
    env_python = _env_value("VIDIOLINGUA_WAV2LIP_PYTHON")
    if env_python:
        candidates.append(("VIDIOLINGUA_WAV2LIP_PYTHON", Path(env_python)))
    candidates.append(("default .venv_lipsync", PROJECT_ROOT / ".venv_lipsync" / "Scripts" / "python.exe"))
    candidates.append(("default .venv_tts", PROJECT_ROOT / ".venv_tts" / "Scripts" / "python.exe"))

    seen: set[str] = set()
    unique: list[tuple[str, Path]] = []
    for source, path in candidates:
        normalized = str(path)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append((source, path))
    return unique


def _probe_imports(python_path: Path, timeout_sec: int = 120) -> dict[str, Any]:
    if not python_path.is_file():
        return {
            "python_exists": False,
            "ok": False,
            "errors": [f"Python executable not found: {python_path}"],
        }

    probe_code = r"""
import importlib
import json

modules = ["numpy", "torch", "cv2", "scipy"]
result = {
    "python_exists": True,
    "ok": True,
    "imports": {},
    "torch_version": None,
    "cuda_available": None,
    "errors": [],
}

for name in modules:
    try:
        module = importlib.import_module(name)
        result["imports"][name] = True
        if name == "torch":
            result["torch_version"] = str(getattr(module, "__version__", ""))
            try:
                result["cuda_available"] = bool(module.cuda.is_available())
            except Exception as exc:
                result["cuda_available"] = False
                result["errors"].append("torch cuda probe failed: " + str(exc))
    except Exception as exc:
        result["imports"][name] = False
        result["ok"] = False
        result["errors"].append(name + " import failed: " + str(exc))

print(json.dumps(result))
"""
    try:
        completed = subprocess.run(
            [str(python_path), "-c", probe_code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {
            "python_exists": True,
            "ok": False,
            "errors": [f"Import probe timed out after {timeout_sec}s: {python_path}"],
        }

    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip()
        return {
            "python_exists": True,
            "ok": False,
            "errors": [message or f"Import probe exited with {completed.returncode}"],
        }
    try:
        parsed = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return {
            "python_exists": True,
            "ok": False,
            "errors": [f"Import probe returned invalid JSON: {exc}"],
        }
    return parsed if isinstance(parsed, dict) else {"python_exists": True, "ok": False, "errors": ["Invalid probe payload"]}


def _resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def build_preflight_report(
    *,
    wav2lip_dir: str | Path | None = None,
    checkpoint: str | Path | None = None,
    explicit_python: str | None = None,
) -> dict[str, Any]:
    dir_value = str(wav2lip_dir) if wav2lip_dir else _env_value("VIDIOLINGUA_WAV2LIP_DIR")
    checkpoint_value = str(checkpoint) if checkpoint else _env_value("VIDIOLINGUA_WAV2LIP_CHECKPOINT")
    resolved_dir = _resolve_path(dir_value, DEFAULT_WAV2LIP_DIR)
    resolved_checkpoint = _resolve_path(checkpoint_value, resolved_dir / "checkpoints" / "wav2lip_gan.pth")

    errors: list[str] = []
    warnings: list[str] = []
    if not resolved_dir.is_dir():
        errors.append(f"Wav2Lip directory not found: {resolved_dir}")
    if not (resolved_dir / "inference.py").is_file():
        errors.append(f"Wav2Lip inference.py not found: {resolved_dir / 'inference.py'}")
    if not resolved_checkpoint.is_file():
        errors.append(f"Wav2Lip checkpoint not found: {resolved_checkpoint}")

    selected_python: str | None = None
    selected_source: str | None = None
    selected_probe: dict[str, Any] = {}
    candidate_reports: list[dict[str, Any]] = []
    for source, python_path in _candidate_python_paths(explicit_python):
        probe = _probe_imports(python_path)
        imports = probe.get("imports") if isinstance(probe.get("imports"), dict) else {}
        candidate_report = {
            "source": source,
            "python": str(python_path),
            "python_exists": bool(probe.get("python_exists")),
            "ok": bool(probe.get("ok")) and all(bool(imports.get(name)) for name in REQUIRED_MODULES),
            "imports": imports,
            "torch_version": probe.get("torch_version"),
            "cuda_available": probe.get("cuda_available"),
            "errors": probe.get("errors") or [],
        }
        candidate_reports.append(candidate_report)
        if candidate_report["ok"] and selected_python is None:
            selected_python = str(python_path)
            selected_source = source
            selected_probe = candidate_report

    if selected_python is None:
        errors.append(
            "No Wav2Lip Python passed preflight. Set VIDIOLINGUA_WAV2LIP_PYTHON "
            "or create .venv_lipsync; .venv_api is not used as a default."
        )

    imports = selected_probe.get("imports") if isinstance(selected_probe.get("imports"), dict) else {}
    report = {
        "ok": not errors and bool(selected_python),
        "selected_python": selected_python,
        "selected_python_source": selected_source,
        "wav2lip_dir": str(resolved_dir),
        "checkpoint_path": str(resolved_checkpoint),
        "checkpoint_exists": resolved_checkpoint.is_file(),
        "numpy_available": bool(imports.get("numpy")),
        "torch_available": bool(imports.get("torch")),
        "torch_version": selected_probe.get("torch_version"),
        "cuda_available": selected_probe.get("cuda_available"),
        "cv2_available": bool(imports.get("cv2")),
        "scipy_available": bool(imports.get("scipy")),
        "errors": errors,
        "warnings": warnings,
        "candidates": candidate_reports,
    }
    return report


def resolve_wav2lip_python(*, require_ok: bool = True) -> str | None:
    report = build_preflight_report()
    if require_ok and not report.get("ok"):
        raise RuntimeError("; ".join(report.get("errors") or ["Wav2Lip preflight failed"]))
    return report.get("selected_python") if isinstance(report.get("selected_python"), str) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Wav2Lip runtime readiness without generation.")
    parser.add_argument("--output", default=None, help="Path to write JSON report.")
    parser.add_argument("--wav2lip-dir", default=None, help="Override Wav2Lip directory.")
    parser.add_argument("--checkpoint", default=None, help="Override Wav2Lip checkpoint path.")
    parser.add_argument("--python", default=None, help="Explicit Python executable to probe first.")
    args = parser.parse_args(argv)

    report = build_preflight_report(
        wav2lip_dir=args.wav2lip_dir,
        checkpoint=args.checkpoint,
        explicit_python=args.python,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
