"""
IndicF5 TTS service for Indian-language zero-shot voice cloning.

IndicF5 takes three inputs:
  1. target text,
  2. reference prompt audio,
  3. transcript of the reference prompt audio.

The pipeline writes reference transcripts beside speaker WAVs as `.txt` files,
so callers can keep passing only `speaker_wav` in the existing TTS contract.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import importlib.util
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_REPO = os.environ.get("VIDIOLINGUA_INDICF5_MODEL", "ai4bharat/IndicF5")
_MAX_CHARS = int(os.environ.get("VIDIOLINGUA_INDICF5_MAX_CHARS", "1200"))
_OUTPUT_SR = 22050
_MODEL_SR = 24000
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SUPPORTED_LANGS = {
    "as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te",
}


def supports_language(language_code: str) -> bool:
    return _lang_base(language_code) in SUPPORTED_LANGS


def _lang_base(language_code: str) -> str:
    code = (language_code or "hi").lower().replace("_", "-").split("-")[0]
    return "or" if code == "od" else code


def _get_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    try:
        import torch
        from huggingface_hub import snapshot_download
        from safetensors.torch import load_file
    except ImportError as exc:
        raise RuntimeError(
            "IndicF5 dependencies are not installed. Install requirements-indicf5.txt "
            "in the separate IndicF5 runtime, not in the known-good XTTS runtime."
        ) from exc

    _configure_runtime_paths()

    token = (
        os.environ.get("HUGGINGFACE_TOKEN")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    )

    try:
        snapshot_path = Path(
            snapshot_download(
                _MODEL_REPO,
                allow_patterns=[
                    "config.json",
                    "model.py",
                    "model.safetensors",
                    "checkpoints/vocab.txt",
                ],
                token=token,
                cache_dir=os.environ.get("HF_HOME") and str(Path(os.environ["HF_HOME"]) / "hub"),
            )
        )
    except Exception as exc:
        raise RuntimeError(
            "IndicF5 model load failed. The ai4bharat/IndicF5 Hugging Face model "
            "is gated, so accept its terms on Hugging Face and set HUGGINGFACE_TOKEN."
        ) from exc

    model_py = snapshot_path / "model.py"
    weights_path = snapshot_path / "model.safetensors"
    if not model_py.is_file() or not weights_path.is_file():
        raise RuntimeError(f"IndicF5 snapshot is incomplete at {snapshot_path}")

    # The published remote code wraps modules in torch.compile. On Windows CPU
    # this is very slow and also changes state-dict keys to include _orig_mod.
    # Disable it and normalize checkpoint keys after load.
    if os.environ.get("VIDIOLINGUA_INDICF5_TORCH_COMPILE", "").strip().lower() != "true":
        torch.compile = lambda model, *args, **kwargs: model

    spec = importlib.util.spec_from_file_location("vidiolingua_indicf5_remote_model", model_py)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import IndicF5 model.py from {model_py}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    try:
        config = module.INF5Config()
        config._name_or_path = _MODEL_REPO
        model = module.INF5Model(config)
        state_dict = load_file(str(weights_path), device="cpu")
        fixed_state_dict = {
            key.replace("._orig_mod.", "."): value
            for key, value in state_dict.items()
        }
        missing, unexpected = model.load_state_dict(fixed_state_dict, strict=False)
        if missing or unexpected:
            raise RuntimeError(
                f"IndicF5 checkpoint mismatch: missing={len(missing)}, "
                f"unexpected={len(unexpected)}"
            )
        model.eval()
    except Exception:
        _MODEL = None
        raise

    _MODEL = model
    return _MODEL


def _configure_runtime_paths() -> None:
    tmp_dir = Path(os.environ.get("VIDIOLINGUA_RUNTIME_TMP", _PROJECT_ROOT / ".runtime_tmp"))
    numba_dir = Path(os.environ.get("VIDIOLINGUA_NUMBA_CACHE_DIR", _PROJECT_ROOT / ".numba_cache"))
    hf_home = Path(os.environ.get("HF_HOME", _PROJECT_ROOT / ".hf_cache"))

    for directory in (tmp_dir, numba_dir, hf_home):
        directory.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("TMP", str(tmp_dir))
    os.environ.setdefault("TEMP", str(tmp_dir))
    os.environ.setdefault("NUMBA_CACHE_DIR", str(numba_dir))
    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def _read_reference_text(speaker_wav: str, ref_text: Optional[str] = None) -> str:
    if ref_text and ref_text.strip():
        return ref_text.strip()

    env_text = os.environ.get("VIDIOLINGUA_VOICE_SAMPLE_TEXT", "").strip()
    if env_text:
        return env_text

    sidecar = Path(speaker_wav).with_suffix(".txt")
    if sidecar.is_file():
        text = sidecar.read_text(encoding="utf-8").strip()
        if text:
            return text

    raise RuntimeError(
        "IndicF5 requires the transcript of the reference audio. Expected a "
        f"sidecar transcript at {sidecar}."
    )


def _split_text(text: str, max_chars: int = _MAX_CHARS) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    parts = re.split(r"(?<=[।.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if current and len(current) + 1 + len(part) > max_chars:
            chunks.extend(_hard_split(current, max_chars))
            current = part
        else:
            current = (current + " " + part).strip() if current else part
    if current:
        chunks.extend(_hard_split(current, max_chars))
    return chunks


def _hard_split(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    chunks: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            chunks.append(current)
            current = word
        else:
            current = (current + " " + word).strip() if current else word
    if current:
        chunks.append(current)
    return chunks


def _to_float_audio(audio):
    import numpy as np

    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    audio = np.array(audio)
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


def _write_model_audio(audio_parts: list, output_path: Path) -> None:
    import numpy as np
    import soundfile as sf

    if not audio_parts:
        raise RuntimeError("IndicF5 produced no audio")

    gap = np.zeros(int(0.03 * _MODEL_SR), dtype=np.float32)
    combined = audio_parts[0]
    for part in audio_parts[1:]:
        combined = np.concatenate([combined, gap, part])

    peak = float(np.abs(combined).max()) if combined.size else 0.0
    if peak > 0:
        combined = combined / peak * 0.95

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=output_path.parent) as tmp:
        tmp_path = Path(tmp.name)
    try:
        sf.write(str(tmp_path), combined.astype(np.float32), _MODEL_SR, subtype="PCM_16")
        r = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(tmp_path),
                "-acodec", "pcm_s16le", "-ar", str(_OUTPUT_SR), "-ac", "1",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {r.stderr or r.stdout}")
    finally:
        tmp_path.unlink(missing_ok=True)


def synthesize_to_wav(
    text: str,
    output_path: Path,
    voice_options: Optional[dict] = None,
    voice_id: Optional[str] = None,
    speaker_wav: Optional[str] = None,
    language_code: str = "hi",
    ref_text: Optional[str] = None,
) -> Path:
    if not supports_language(language_code):
        raise RuntimeError(f"IndicF5 does not support language '{language_code}'")
    if not speaker_wav or not Path(speaker_wav).is_file():
        raise RuntimeError("IndicF5 requires a valid speaker_wav reference")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = _split_text(text)
    if not chunks:
        raise RuntimeError("IndicF5 received empty text")

    prompt_text = _read_reference_text(speaker_wav, ref_text)
    model = _get_model()

    audio_parts = []
    for chunk in chunks:
        try:
            import torch

            with torch.inference_mode():
                audio = model(chunk, ref_audio_path=str(speaker_wav), ref_text=prompt_text)
        except ImportError:
            audio = model(chunk, ref_audio_path=str(speaker_wav), ref_text=prompt_text)
        audio_parts.append(_to_float_audio(audio))

    _write_model_audio(audio_parts, output_path)
    logger.info("IndicF5 output written: %s", output_path)
    return output_path
