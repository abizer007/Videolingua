"""Isolated IndicF5 worker."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_NAME = "ai4bharat/IndicF5"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models" / "indicf5" / "IndicF5"
MODEL_SAMPLE_RATE = 24000
OUTPUT_SAMPLE_RATE = 22050
DEFAULT_MAX_TEXT_CHARS = 120
DEFAULT_MAX_REF_SECONDS = 12.0


class IndicF5WorkerError(RuntimeError):
    """Clear worker error that can be serialized to the parent process."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one IndicF5 voice synthesis request.")
    parser.add_argument("--request", required=True, help="Path to request JSON.")
    parser.add_argument("--response", required=True, help="Path to response JSON.")
    parser.add_argument("--diagnose", action="store_true", help="Validate request/runtime without model load.")
    parser.add_argument("--load-only", action="store_true", help="Load model but do not generate audio.")
    parser.add_argument("--no-generate", action="store_true", help="Skip audio generation after model load.")
    return parser.parse_args()


def _write_response(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_request_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _workspace_path(value: str | Path, *, label: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        return path.resolve()
    except OSError as exc:
        raise IndicF5WorkerError(f"{label} could not be resolved: {path}") from exc


def _require_text(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise IndicF5WorkerError(f"IndicF5 request requires non-empty '{key}'")
    return value


def _payload_bool(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _coerce_device_string(device: Any) -> str:
    text = str(device or "cuda").strip().lower()
    if text.startswith("cuda"):
        return text
    if text == "cpu":
        return "cpu"
    raise IndicF5WorkerError(f"Unsupported IndicF5 device '{device}'. Use 'cuda' or 'cpu'.")


def _safe_int(value: Any, *, label: str, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise IndicF5WorkerError(f"Invalid {label}: {value}") from exc


def _safe_float(value: Any, *, label: str, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise IndicF5WorkerError(f"Invalid {label}: {value}") from exc


def _probe_audio_duration(path: Path) -> float:
    try:
        completed = subprocess.run(
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
            timeout=30,
        )
        if completed.returncode == 0 and (completed.stdout or "").strip():
            return float(completed.stdout.strip())
    except Exception:
        return 0.0
    return 0.0


def _configure_workspace_runtime() -> None:
    if not (
        os.environ.get("HUGGINGFACE_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    ):
        for token_path in (
            Path.home() / ".cache" / "huggingface" / "token",
            Path(os.environ.get("USERPROFILE", "")) / ".cache" / "huggingface" / "token",
        ):
            try:
                if token_path.is_file():
                    token = token_path.read_text(encoding="utf-8").strip()
                    if token:
                        os.environ["HF_TOKEN"] = token
                        break
            except Exception:
                pass

    runtime_root = PROJECT_ROOT / ".runtime_tmp" / "indicf5"
    hf_home = PROJECT_ROOT / ".hf_cache" / "indicf5"
    hf_hub = hf_home / "hub"
    modules_cache = hf_home / "modules"
    numba_cache = PROJECT_ROOT / ".numba_cache" / "indicf5"
    xdg_cache = PROJECT_ROOT / ".cache" / "indicf5"
    wandb_dir = PROJECT_ROOT / ".runtime_tmp" / "indicf5" / "wandb"

    for directory in (runtime_root, hf_home, hf_hub, modules_cache, numba_cache, xdg_cache, wandb_dir):
        directory.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HF_HUB_CACHE", str(hf_hub))
    os.environ.setdefault("HF_MODULES_CACHE", str(modules_cache))
    os.environ.setdefault("TMP", str(runtime_root))
    os.environ.setdefault("TEMP", str(runtime_root))
    os.environ.setdefault("NUMBA_CACHE_DIR", str(numba_cache))
    os.environ.setdefault("XDG_CACHE_HOME", str(xdg_cache))
    os.environ.setdefault("WANDB_DIR", str(wandb_dir))
    os.environ.setdefault("WANDB_CACHE_DIR", str(wandb_dir / "cache"))
    os.environ.setdefault("WANDB_CONFIG_DIR", str(wandb_dir / "config"))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def _validate_request(payload: dict[str, Any]) -> dict[str, Any]:
    text = _require_text(payload, "text")
    target_language = _require_text(payload, "target_language").lower()
    output_path = _workspace_path(_require_text(payload, "output_path"), label="output_path")
    reference_audio_path = _workspace_path(
        _require_text(payload, "reference_audio_path"),
        label="reference_audio_path",
    )
    reference_text = _require_text(payload, "reference_text")

    if not reference_audio_path.is_file():
        raise IndicF5WorkerError(f"IndicF5 reference audio does not exist: {reference_audio_path}")

    max_text_chars = _safe_int(
        payload.get("max_text_chars") or os.environ.get("VIDIOLINGUA_INDICF5_MAX_TEXT_CHARS"),
        label="max_text_chars",
        default=DEFAULT_MAX_TEXT_CHARS,
    )
    if len(text) > max_text_chars and not _payload_bool(payload, "allow_long_text", False):
        raise IndicF5WorkerError(
            f"IndicF5 smoke text is too long ({len(text)} chars > {max_text_chars}). "
            "Set allow_long_text=true only after small validation passes."
        )

    model_name = str(
        payload.get("model_name")
        or os.environ.get("VIDIOLINGUA_INDICF5_MODEL")
        or DEFAULT_MODEL_NAME
    ).strip()
    if not model_name:
        model_name = DEFAULT_MODEL_NAME

    device = _coerce_device_string(payload.get("device") or os.environ.get("VIDIOLINGUA_INDICF5_DEVICE") or "cuda")
    batch_size_raw = payload.get("batch_size") or os.environ.get("VIDIOLINGUA_INDICF5_BATCH_SIZE") or "1"
    batch_size = _safe_int(batch_size_raw, label="IndicF5 batch_size", default=1)
    if batch_size != 1:
        raise IndicF5WorkerError("IndicF5 fresh scaffold requires batch_size=1")

    model_dir_raw = payload.get("model_dir") or os.environ.get("VIDIOLINGUA_INDICF5_MODEL_DIR")
    model_dir = _workspace_path(model_dir_raw or DEFAULT_MODEL_DIR, label="model_dir")
    checkpoint_path_raw = (
        payload.get("checkpoint_path")
        or os.environ.get("VIDIOLINGUA_INDICF5_CKPT_PATH")
        or os.environ.get("VIDIOLINGUA_INDICF5_CHECKPOINT_PATH")
    )
    checkpoint_path = _workspace_path(
        checkpoint_path_raw or (model_dir / "model.safetensors"),
        label="checkpoint_path",
    )
    if not checkpoint_path.is_file():
        raise IndicF5WorkerError(f"IndicF5 checkpoint is missing: {checkpoint_path}")
    vocab_path_raw = payload.get("vocab_path") or os.environ.get("VIDIOLINGUA_INDICF5_VOCAB_PATH")
    vocab_path = _workspace_path(vocab_path_raw or (model_dir / "checkpoints" / "vocab.txt"), label="vocab_path")
    if not vocab_path.is_file():
        raise IndicF5WorkerError(f"IndicF5 vocab is missing: {vocab_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(prefix="indicf5_write_", suffix=".tmp", delete=False, dir=output_path.parent) as tmp:
            tmp_path = Path(tmp.name)
        tmp_path.unlink(missing_ok=True)
    except Exception as exc:
        raise IndicF5WorkerError(f"IndicF5 output path is not writable: {output_path.parent}") from exc

    max_ref_seconds = _safe_float(
        payload.get("max_ref_seconds") or os.environ.get("VIDIOLINGUA_INDICF5_MAX_REF_SECONDS"),
        label="max_ref_seconds",
        default=DEFAULT_MAX_REF_SECONDS,
    )
    reference_duration_sec = _probe_audio_duration(reference_audio_path)
    if (
        reference_duration_sec
        and reference_duration_sec > max_ref_seconds
        and not _payload_bool(payload, "allow_long_reference", False)
    ):
        raise IndicF5WorkerError(
            f"IndicF5 reference audio is too long for smoke validation "
            f"({reference_duration_sec:.2f}s > {max_ref_seconds:.2f}s)."
        )

    return {
        "text": text,
        "target_language": target_language,
        "output_path": output_path,
        "reference_audio_path": reference_audio_path,
        "reference_text": reference_text,
        "model_name": model_name,
        "model_dir": model_dir,
        "checkpoint_path": checkpoint_path,
        "vocab_path": vocab_path,
        "device": device,
        "dtype": str(payload.get("dtype") or os.environ.get("VIDIOLINGUA_INDICF5_DTYPE") or ("float16" if device.startswith("cuda") else "float32")),
        "batch_size": batch_size,
        "max_text_chars": max_text_chars,
        "max_ref_seconds": max_ref_seconds,
        "reference_duration_sec": reference_duration_sec,
        "diagnose_only": _payload_bool(payload, "diagnose_only", False),
        "load_only": _payload_bool(payload, "load_only", False),
        "generate": _payload_bool(payload, "generate", True),
    }


def _ensure_runtime(request: dict[str, Any]):
    try:
        import torch  # type: ignore
    except ImportError as exc:
        raise IndicF5WorkerError(
            "IndicF5 dependencies are not installed in .venv_indicf5 yet. "
            "After approval, run scripts\\setup_indicf5_env.ps1 -Run, then download/validate the model."
        ) from exc

    if request["device"] == "cuda" and not torch.cuda.is_available():
        raise IndicF5WorkerError("IndicF5 was asked to use CUDA, but torch.cuda.is_available() is false")

    return torch


def _memory_snapshot(torch=None) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    try:
        import psutil  # type: ignore

        mem = psutil.virtual_memory()
        snapshot["system_available_mb"] = round(mem.available / (1024 * 1024), 1)
        snapshot["system_total_mb"] = round(mem.total / (1024 * 1024), 1)
    except Exception:
        pass
    if torch is not None:
        try:
            snapshot["cuda_available"] = bool(torch.cuda.is_available())
            if torch.cuda.is_available():
                snapshot["cuda_allocated_mb"] = round(torch.cuda.memory_allocated() / (1024 * 1024), 1)
                snapshot["cuda_reserved_mb"] = round(torch.cuda.memory_reserved() / (1024 * 1024), 1)
        except Exception:
            pass
    return snapshot


def _download_model_files(request: dict[str, Any]) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise IndicF5WorkerError("huggingface_hub is required for IndicF5 model download") from exc

    model_dir = Path(request["model_dir"])
    model_dir.mkdir(parents=True, exist_ok=True)
    token = (
        os.environ.get("HUGGINGFACE_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    )
    try:
        snapshot_download(
            request["model_name"],
            allow_patterns=[
                "config.json",
                "model.py",
                "model.safetensors",
                "checkpoints/vocab.txt",
            ],
            local_dir=str(model_dir),
            cache_dir=str(PROJECT_ROOT / ".hf_cache" / "indicf5" / "hub"),
            token=token,
        )
    except Exception as exc:
        raise IndicF5WorkerError(
            "IndicF5 model download/load failed. If ai4bharat/IndicF5 is gated, "
            "accept the model terms on Hugging Face and authenticate non-interactively before retrying. "
            f"Original error: {exc}"
        ) from exc

    required = [
        model_dir / "config.json",
        model_dir / "model.py",
        model_dir / "model.safetensors",
        model_dir / "checkpoints" / "vocab.txt",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise IndicF5WorkerError("IndicF5 model snapshot is incomplete. Missing: " + ", ".join(missing))
    return model_dir


def _load_model(request: dict[str, Any], torch):
    try:
        from safetensors.torch import load_file
    except ImportError as exc:
        raise IndicF5WorkerError("safetensors is required to load IndicF5 weights") from exc

    model_dir = _download_model_files(request)
    model_py = model_dir / "model.py"
    weights_path = Path(request["checkpoint_path"])

    if os.environ.get("VIDIOLINGUA_INDICF5_TORCH_COMPILE", "").strip().lower() != "true":
        torch.compile = lambda model, *args, **kwargs: model

    sys.path.insert(0, str(model_dir))
    spec = importlib.util.spec_from_file_location("vidiolingua_fresh_indicf5_model", model_py)
    if spec is None or spec.loader is None:
        raise IndicF5WorkerError(f"Cannot import IndicF5 model.py from {model_py}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise IndicF5WorkerError(f"IndicF5 model.py import failed: {exc}") from exc

    hf_cache_dir = str(PROJECT_ROOT / ".hf_cache" / "indicf5" / "hub")
    original_hf_hub_download = module.hf_hub_download

    def _workspace_hf_hub_download(*args, **kwargs):
        kwargs.setdefault("cache_dir", hf_cache_dir)
        return original_hf_hub_download(*args, **kwargs)

    original_load_vocoder = module.load_vocoder

    def _workspace_load_vocoder(*args, **kwargs):
        kwargs.setdefault("hf_cache_dir", hf_cache_dir)
        return original_load_vocoder(*args, **kwargs)

    module.hf_hub_download = _workspace_hf_hub_download
    module.load_vocoder = _workspace_load_vocoder
    original_load_model = module.load_model

    load_model_signature = inspect.signature(original_load_model)
    load_model_needs_ckpt = (
        "ckpt_path" in load_model_signature.parameters
        and load_model_signature.parameters["ckpt_path"].default is inspect.Parameter.empty
    )

    def _workspace_load_model(*args, **kwargs):
        if load_model_needs_ckpt and "ckpt_path" not in kwargs:
            if len(args) < 3:
                args = (*args, str(weights_path))
        if "device" in kwargs:
            kwargs["device"] = _coerce_device_string(kwargs["device"])
        else:
            parameter_names = list(load_model_signature.parameters)
            if "device" in parameter_names:
                device_index = parameter_names.index("device")
                if len(args) > device_index:
                    args = list(args)
                    args[device_index] = _coerce_device_string(args[device_index])
                    args = tuple(args)
        return original_load_model(*args, **kwargs)

    module.load_model = _workspace_load_model

    try:
        config = module.INF5Config()
        config.name_or_path = request["model_name"]
        config._name_or_path = request["model_name"]
        config.vocab_path = str(request["vocab_path"])
        config.ckpt_path = str(weights_path)
        model = module.INF5Model(config)
        if not load_model_needs_ckpt:
            state_dict = load_file(str(weights_path), device="cpu")
            fixed_state_dict = {key.replace("._orig_mod.", "."): value for key, value in state_dict.items()}
            missing, unexpected = model.load_state_dict(fixed_state_dict, strict=False)
            if missing or unexpected:
                raise IndicF5WorkerError(
                    f"IndicF5 checkpoint mismatch: missing={len(missing)}, unexpected={len(unexpected)}"
                )
        model.eval()
        if request["device"] == "cuda":
            model.to("cuda")
        return model
    except IndicF5WorkerError:
        raise
    except Exception as exc:
        raise IndicF5WorkerError(f"IndicF5 model load failed: {exc}") from exc


def _to_float_audio(audio):
    import numpy as np

    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    audio = np.asarray(audio)
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    else:
        audio = audio.astype(np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=0 if audio.shape[0] < audio.shape[-1] else 1)
    max_val = float(np.abs(audio).max()) if audio.size else 0.0
    if max_val > 1.0:
        audio = audio / max_val
    return audio


def _write_audio(audio, output_path: Path) -> None:
    import numpy as np
    import soundfile as sf

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio = _to_float_audio(audio)
    if audio.size == 0:
        raise IndicF5WorkerError("IndicF5 produced no audio samples")
    peak = float(np.abs(audio).max())
    if peak > 0:
        audio = audio / peak * 0.95

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=output_path.parent) as tmp:
        tmp_path = Path(tmp.name)
    try:
        sf.write(str(tmp_path), audio.astype(np.float32), MODEL_SAMPLE_RATE, subtype="PCM_16")
        completed = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(tmp_path),
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(OUTPUT_SAMPLE_RATE),
                "-ac",
                "1",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise IndicF5WorkerError(f"ffmpeg conversion failed: {completed.stderr or completed.stdout}")
    finally:
        tmp_path.unlink(missing_ok=True)


def _run_synthesis(request: dict[str, Any]) -> None:
    torch = _ensure_runtime(request)
    model = _load_model(request, torch)
    if request["load_only"] or not request["generate"]:
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return
    try:
        with torch.inference_mode():
            audio = model(
                request["text"],
                ref_audio_path=str(request["reference_audio_path"]),
                ref_text=request["reference_text"],
            )
        _write_audio(audio, Path(request["output_path"]))
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def main() -> int:
    args = parse_args()
    request_path = Path(args.request)
    response_path = Path(args.response)
    try:
        payload = _read_request_json(request_path)
        if args.diagnose:
            payload["diagnose_only"] = True
        if args.load_only:
            payload["load_only"] = True
            payload["generate"] = False
        if args.no_generate:
            payload["generate"] = False
        _configure_workspace_runtime()
        request = _validate_request(payload)
        torch = None
        try:
            torch = _ensure_runtime(request)
        except Exception:
            if not request["diagnose_only"]:
                raise
        if request["diagnose_only"]:
            _write_response(
                response_path,
                {
                    "ok": True,
                    "engine": "indicf5",
                    "mode": "diagnose_only",
                    "model_name": request["model_name"],
                    "model_dir": str(request["model_dir"]),
                    "checkpoint_path": str(request["checkpoint_path"]),
                    "vocab_path": str(request["vocab_path"]),
                    "device": request["device"],
                    "dtype": request["dtype"],
                    "cuda_available": bool(torch and torch.cuda.is_available()),
                    "reference_duration_sec": request["reference_duration_sec"],
                    "memory": _memory_snapshot(torch),
                    "model_loaded": False,
                    "generated": False,
                    "fallback_used": False,
                },
            )
            return 0
        _run_synthesis(request)
        _write_response(
            response_path,
            {
                "ok": True,
                "engine": "indicf5",
                "mode": "load_only" if request["load_only"] or not request["generate"] else "generate",
                "output_path": str(request["output_path"]),
                "model_name": request["model_name"],
                "model_dir": str(request["model_dir"]),
                "checkpoint_path": str(request["checkpoint_path"]),
                "vocab_path": str(request["vocab_path"]),
                "device": request["device"],
                "dtype": request["dtype"],
                "used_reference_audio": True,
                "used_reference_text": True,
                "memory": _memory_snapshot(torch),
                "model_loaded": True,
                "generated": bool(request["generate"] and not request["load_only"]),
                "fallback_used": False,
            },
        )
        return 0
    except Exception as exc:
        model_name = ""
        device = ""
        try:
            payload = _read_request_json(request_path)
            model_name = str(payload.get("model_name") or os.environ.get("VIDIOLINGUA_INDICF5_MODEL") or DEFAULT_MODEL_NAME)
            device = str(payload.get("device") or os.environ.get("VIDIOLINGUA_INDICF5_DEVICE") or "cuda")
        except Exception:
            pass
        _write_response(
            response_path,
            {
                "ok": False,
                "engine": "indicf5",
                "error": str(exc),
                "model_name": model_name,
                "device": device,
                "memory": _memory_snapshot(),
                "fallback_used": False,
            },
        )
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
