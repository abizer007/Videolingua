"""Strict Coqui XTTS speaker cloning."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .audio_validation import (
    AudioStats,
    AudioValidationError,
    analyze_audio,
    file_sha256,
    read_audio_mono,
    validate_generated_audio,
    validate_reference_audio,
)
from .reference_audio import ReferenceAudioError, prepare_reference_audio

logger = logging.getLogger(__name__)

XTTS_V2_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
PREPROCESSING_VERSION = "xtts-reference-v1"
DEFAULT_XTTS_TEMPERATURE = 0.52
DEFAULT_XTTS_REPETITION_PENALTY = 8.5
DEFAULT_XTTS_MAX_CHARS = 180
DEFAULT_XTTS_CROSSFADE_MS = 25.0
DEFAULT_AUDIO_LOUDNESS_NORMALIZE = False
DEFAULT_AUDIO_TARGET_LUFS = -16.0
XTTS_SUPPORTED_LANGS = {
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "pl",
    "tr",
    "ru",
    "nl",
    "cs",
    "ar",
    "zh",
    "hu",
    "ko",
    "ja",
}

_MODEL_CACHE: dict[tuple[str, bool], Any] = {}


class VoiceCloningError(RuntimeError):
    """Raised when XTTS voice cloning cannot be completed correctly."""


class VoiceClonePreflightError(VoiceCloningError):
    """Raised when XTTS cannot be run safely with the local runtime/config."""


@dataclass
class VoiceCloneConfig:
    model_name: str = XTTS_V2_MODEL
    model_path: Path | None = None
    language: str = "en"
    voice_cloning_required: bool = True
    allow_generic_tts_fallback: bool = False
    temperature: float = DEFAULT_XTTS_TEMPERATURE
    repetition_penalty: float = DEFAULT_XTTS_REPETITION_PENALTY
    max_chars: int = DEFAULT_XTTS_MAX_CHARS
    sample_rate: int = 24000
    crossfade_ms: float = DEFAULT_XTTS_CROSSFADE_MS
    loudness_normalize: bool = DEFAULT_AUDIO_LOUDNESS_NORMALIZE
    target_lufs: float = DEFAULT_AUDIO_TARGET_LUFS
    intermediate_dir: Path = Path("outputs/intermediate")
    force_regenerate: bool = False
    preprocessing_version: str = PREPROCESSING_VERSION
    model_load_timeout_seconds: int = 600
    generation_timeout_seconds: int = 300
    device: str = "auto"


@dataclass
class ModelFiles:
    model_dir: str
    config_path: str
    checkpoint_path: str
    vocab_path: str
    speakers_path: str | None = None


@dataclass
class VoiceClonePreflightResult:
    ok: bool
    model_name: str
    model_files: ModelFiles | None
    reference_stats: AudioStats | None
    output_dir: str
    intermediate_dir: str
    device: str
    cuda_available: bool
    torch_version: str | None
    tts_importable: bool
    warnings: list[str] = field(default_factory=list)

    def to_report(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VoiceCloneResult:
    output_path: str
    reference_audio_path: str
    cleaned_reference_path: str
    raw_xtts_path: str
    clean_xtts_path: str
    model_name: str
    language: str
    speaker_wav_used: bool
    fallback_attempted: bool
    reference_stats: AudioStats
    generated_stats: AudioStats
    cache_key: str
    chunks: int
    warnings: list[str] = field(default_factory=list)

    def to_report(self) -> dict[str, Any]:
        data = asdict(self)
        data["reference_stats"] = asdict(self.reference_stats)
        data["generated_stats"] = asdict(self.generated_stats)
        return data


@contextmanager
def _timed_stage(name: str):
    start = time.monotonic()
    logger.info("XTTS stage start: %s", name)
    try:
        yield
    finally:
        logger.info("XTTS stage end: %s elapsed=%.2fs", name, time.monotonic() - start)


def _lang_base(language: str) -> str:
    return (language or "en").lower().replace("_", "-").split("-")[0]


def normalize_xtts_language(language: str) -> str:
    lang = _lang_base(language)
    if lang not in XTTS_SUPPORTED_LANGS:
        raise VoiceCloningError(
            f"XTTS v2 does not support language '{language}'. Supported languages: "
            f"{', '.join(sorted(XTTS_SUPPORTED_LANGS))}"
        )
    return lang


def _xtts_cache_dir_name() -> str:
    return "tts_models--multilingual--multi-dataset--xtts_v2"


def _normalize_model_dir_candidate(candidate: Path) -> Path:
    """Return the XTTS model directory even if caller passed model.pth.

    Coqui TTS expects `TTS(model_path=...)` to receive either the model directory
    or a model identifier. In this project we use a local directory. Passing
    `models/xtts_v2/model.pth` causes Coqui's XTTS loader to append another
    `model.pth`, producing the invalid path `model.pth/model.pth`.
    """
    candidate = Path(candidate)

    # Most important fix: if config/env passes the checkpoint file, use its parent folder.
    if candidate.name.lower() == "model.pth" or candidate.suffix.lower() == ".pth":
        return candidate.parent

    return candidate


def _candidate_model_dirs(config: VoiceCloneConfig) -> list[Path]:
    candidates: list[Path] = []
    for value in (
        config.model_path,
        os.environ.get("VIDIOLINGUA_XTTS_MODEL_PATH"),
        os.environ.get("XTTS_MODEL_PATH"),
        os.environ.get("COQUI_XTTS_MODEL_PATH"),
    ):
        if value:
            candidates.append(_normalize_model_dir_candidate(Path(value)))

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "tts" / _xtts_cache_dir_name())
        candidates.append(Path(local_appdata) / "tts" / "tts_models" / "multilingual" / "multi-dataset" / "xtts_v2")
    home = Path.home()
    candidates.extend(
        [
            home / ".local" / "share" / "tts" / _xtts_cache_dir_name(),
            home / ".cache" / "tts" / _xtts_cache_dir_name(),
            home / ".local" / "share" / "tts" / "tts_models" / "multilingual" / "multi-dataset" / "xtts_v2",
        ]
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        candidate = _normalize_model_dir_candidate(candidate)
        try:
            key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        except OSError as exc:
            logger.warning("Skipping inaccessible XTTS model candidate %s: %s", candidate, exc)
            continue
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _find_first(patterns: list[str], model_dir: Path) -> Path | None:
    for pattern in patterns:
        matches = sorted(model_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def _find_checkpoint(model_dir: Path) -> Path | None:
    """Find the actual XTTS model checkpoint, avoiding speaker metadata files."""
    exact = model_dir / "model.pth"
    if exact.is_file():
        return exact

    for match in sorted(model_dir.glob("*.pth")):
        name = match.name.lower()
        if name.startswith("speakers") or name == "speakers_xtts.pth":
            continue
        return match

    return None


def resolve_xtts_model_files(config: VoiceCloneConfig) -> ModelFiles:
    if config.model_name != XTTS_V2_MODEL:
        raise VoiceClonePreflightError(
            f"Wrong XTTS model configured: '{config.model_name}'. Required: '{XTTS_V2_MODEL}'"
        )

    checked: list[str] = []
    for raw_model_dir in _candidate_model_dirs(config):
        model_dir = _normalize_model_dir_candidate(raw_model_dir)
        checked.append(str(model_dir))
        try:
            if not model_dir.is_dir():
                continue
            config_path = model_dir / "config.json"
            checkpoint_path = _find_checkpoint(model_dir)
            vocab_path = _find_first(["vocab.json", "tokenizer.json"], model_dir)
            speakers_path = _find_first(["speakers_xtts.pth", "speakers*.pth"], model_dir)
        except OSError:
            continue
        missing = []
        if not config_path.is_file():
            missing.append("config.json")
        if not checkpoint_path or not checkpoint_path.is_file():
            missing.append("model.pth or model checkpoint *.pth")
        if not vocab_path or not vocab_path.is_file():
            missing.append("vocab.json or tokenizer.json")
        if missing:
            raise VoiceClonePreflightError(
                f"XTTS model directory '{model_dir}' is incomplete; missing: {', '.join(missing)}"
            )
        return ModelFiles(
            model_dir=str(model_dir),
            config_path=str(config_path),
            checkpoint_path=str(checkpoint_path),
            vocab_path=str(vocab_path),
            speakers_path=str(speakers_path) if speakers_path else None,
        )

    raise VoiceClonePreflightError(
        "Local XTTS v2 model files were not found. Set VIDIOLINGUA_XTTS_MODEL_PATH "
        "to a directory containing config.json, model.pth, and vocab.json. "
        f"Checked: {', '.join(checked)}"
    )


def _runtime_device(config: VoiceCloneConfig, cuda_available: bool) -> str:
    requested = (config.device or "auto").lower()
    if requested == "auto":
        return "cuda" if cuda_available else "cpu"
    if requested in {"cuda", "gpu"}:
        if not cuda_available:
            raise VoiceClonePreflightError("XTTS device is cuda, but torch.cuda.is_available() is false")
        return "cuda"
    if requested == "cpu":
        return "cpu"
    raise VoiceClonePreflightError(f"Unsupported XTTS_DEVICE '{config.device}'")


def preflight_xtts_voice_cloning(
    *,
    reference_audio_path: str | Path,
    output_path: str | Path,
    language: str = "en",
    config: VoiceCloneConfig | None = None,
) -> VoiceClonePreflightResult:
    config = config or VoiceCloneConfig()
    warnings: list[str] = []

    lang = normalize_xtts_language(language or config.language)
    output_path = Path(output_path)
    intermediate_dir = Path(config.intermediate_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    try:
        probe = output_path.parent / ".xtts_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise VoiceClonePreflightError(f"Output directory is not writable: {output_path.parent}") from exc

    try:
        reference_stats = validate_reference_audio(reference_audio_path)
    except AudioValidationError as exc:
        raise VoiceClonePreflightError(f"Reference audio failed preflight validation: {exc}") from exc

    model_files = resolve_xtts_model_files(config)

    try:
        import torch
        from TTS.api import TTS  # noqa: F401

        torch_version = getattr(torch, "__version__", None)
        cuda_available = bool(torch.cuda.is_available())
        tts_importable = True
    except ImportError as exc:
        raise VoiceClonePreflightError("Coqui TTS and torch must be importable before XTTS validation") from exc

    device = _runtime_device(config, cuda_available)
    if device == "cpu" and config.generation_timeout_seconds <= 300:
        warnings.append(
            "CPU XTTS generation can exceed 300s on first real run; set XTTS_GENERATION_TIMEOUT_SECONDS higher if needed."
        )

    logger.info("XTTS preflight ok: model=%s language=%s device=%s", config.model_name, lang, device)
    logger.info("XTTS model dir: %s", model_files.model_dir)
    logger.info("XTTS config path: %s", model_files.config_path)
    logger.info("XTTS checkpoint path: %s", model_files.checkpoint_path)
    logger.info("XTTS vocab path: %s", model_files.vocab_path)
    if model_files.speakers_path:
        logger.info("XTTS speakers path: %s", model_files.speakers_path)
    logger.info("XTTS torch version: %s", torch_version)
    logger.info("XTTS cuda available: %s", cuda_available)
    logger.info("XTTS reference duration: %.2fs", reference_stats.duration_s)
    logger.info("XTTS output dir: %s", output_path.parent)
    logger.info("XTTS intermediate dir: %s", intermediate_dir)

    return VoiceClonePreflightResult(
        ok=True,
        model_name=config.model_name,
        model_files=model_files,
        reference_stats=reference_stats,
        output_dir=str(output_path.parent),
        intermediate_dir=str(intermediate_dir),
        device=device,
        cuda_available=cuda_available,
        torch_version=torch_version,
        tts_importable=tts_importable,
        warnings=warnings,
    )


def _load_xtts_model(config: VoiceCloneConfig):
    model_name = config.model_name
    if model_name != XTTS_V2_MODEL:
        raise VoiceCloningError(
            f"Wrong XTTS model configured: '{model_name}'. Required: '{XTTS_V2_MODEL}'"
        )
    try:
        import torch
        from TTS.api import TTS
    except ImportError as exc:
        raise VoiceCloningError(
            "Coqui TTS / torch are not installed. Install the TTS environment before cloning."
        ) from exc

    cuda_available = bool(torch.cuda.is_available())
    device = _runtime_device(config, cuda_available)
    use_gpu = device == "cuda"
    model_files = resolve_xtts_model_files(config)
    model_dir = _normalize_model_dir_candidate(Path(model_files.model_dir))
    config_path = Path(model_files.config_path)
    checkpoint_path = Path(model_files.checkpoint_path)
    vocab_path = Path(model_files.vocab_path)
    if not os.environ.get("TTS_HOME") and not os.environ.get("XDG_DATA_HOME"):
        tts_home = Path(config.intermediate_dir) / "coqui_tts_home"
        tts_home.mkdir(parents=True, exist_ok=True)
        os.environ["TTS_HOME"] = str(tts_home)
        logger.info("XTTS TTS_HOME fallback: %s", tts_home)

    missing = [
        str(path)
        for path in (model_dir, config_path, checkpoint_path, vocab_path)
        if not path.exists()
    ]
    if missing:
        raise VoiceCloningError("XTTS model folder is incomplete. Missing: " + ", ".join(missing))

    # Cache by model directory and GPU/CPU mode. Do not key on checkpoint path.
    key = (str(model_dir), use_gpu)
    if key not in _MODEL_CACHE:
        logger.info(
            "Loading Coqui XTTS model=%s model_dir=%s checkpoint=%s device=%s load_timeout=%ss",
            model_name,
            model_dir,
            checkpoint_path,
            device,
            config.model_load_timeout_seconds,
        )
        if device == "cpu":
            logger.warning(
                "XTTS is running on CPU. Model load or generation may be slow; adjust XTTS_*_TIMEOUT_SECONDS if needed."
            )
        start = time.monotonic()
        try:
            # IMPORTANT:
            # Pass the XTTS directory here, not model.pth. Coqui's TTS API resolves
            # the checkpoint from this directory internally. Passing model.pth causes
            # an invalid path like models/xtts_v2/model.pth/model.pth.
            _MODEL_CACHE[key] = TTS(
                model_path=str(model_dir),
                config_path=str(config_path),
                gpu=use_gpu,
            )
        except Exception as exc:
            raise VoiceCloningError(f"XTTS model failed to load: {model_name}") from exc
        elapsed = time.monotonic() - start
        logger.info("XTTS model load completed elapsed=%.2fs", elapsed)
        if elapsed > config.model_load_timeout_seconds:
            raise VoiceCloningError(
                f"XTTS model load exceeded configured timeout: {elapsed:.2f}s > {config.model_load_timeout_seconds}s"
            )
        if use_gpu:
            torch.cuda.empty_cache()
    return _MODEL_CACHE[key]


def split_text_for_xtts(text: str, max_chars: int = 200) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?;:])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip() if current else sentence

        if len(current) > max_chars:
            pieces = _split_long_sentence(current, max_chars)
            chunks.extend(pieces[:-1])
            current = pieces[-1] if pieces else ""

    if current:
        chunks.append(current)
    final: list[str] = []
    for chunk in chunks:
        if len(chunk) > max_chars:
            final.extend(_split_words(chunk, max_chars))
        else:
            final.append(chunk)
    return _merge_tiny_chunks([chunk for chunk in final if chunk.strip()], max_chars)


def _merge_tiny_chunks(chunks: list[str], max_chars: int, min_chars: int = 32) -> list[str]:
    if len(chunks) <= 1:
        return chunks
    merged: list[str] = []
    for chunk in chunks:
        if (
            merged
            and len(chunk) < min_chars
            and len(merged[-1]) + 1 + len(chunk) <= max_chars
        ):
            merged[-1] = f"{merged[-1]} {chunk}".strip()
        else:
            merged.append(chunk)
    return merged


def _split_long_sentence(text: str, max_chars: int) -> list[str]:
    pieces = re.split(r"(?<=[,])\s+", text)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + 1 + len(piece) > max_chars:
            chunks.append(current)
            current = piece
        else:
            current = f"{current} {piece}".strip() if current else piece
    if current:
        chunks.append(current)
    return chunks


def _split_words(text: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > max_chars:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip() if current else word
    if current:
        chunks.append(current)
    return chunks


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.asarray(samples, dtype=np.float32)
    try:
        import soundfile as sf

        sf.write(str(path), samples, sample_rate, subtype="PCM_16")
        return
    except ImportError:
        pass

    import wave

    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _resample_linear(samples: np.ndarray, from_sr: int, to_sr: int) -> np.ndarray:
    if from_sr == to_sr:
        return samples.astype(np.float32, copy=False)
    if len(samples) == 0:
        return samples.astype(np.float32, copy=False)
    out_len = max(1, int(round(len(samples) * to_sr / from_sr)))
    x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=True)
    x_new = np.linspace(0.0, 1.0, num=out_len, endpoint=True)
    return np.interp(x_new, x_old, samples).astype(np.float32)


def _append_with_crossfade(parts: list[np.ndarray], sample_rate: int, crossfade_ms: float) -> np.ndarray:
    if not parts:
        return np.array([], dtype=np.float32)
    crossfade = max(0, int(sample_rate * crossfade_ms / 1000.0))
    combined = parts[0].astype(np.float32, copy=False)
    for part in parts[1:]:
        part = part.astype(np.float32, copy=False)
        if crossfade > 0 and len(combined) > crossfade and len(part) > crossfade:
            fade_out = np.linspace(1.0, 0.0, crossfade, dtype=np.float32)
            fade_in = np.linspace(0.0, 1.0, crossfade, dtype=np.float32)
            joined = combined[-crossfade:] * fade_out + part[:crossfade] * fade_in
            combined = np.concatenate([combined[:-crossfade], joined, part[crossfade:]])
        else:
            gap = np.zeros(int(sample_rate * 0.04), dtype=np.float32)
            combined = np.concatenate([combined, gap, part])
    return combined


def _clean_generated(samples: np.ndarray) -> np.ndarray:
    if samples.size == 0:
        return samples
    samples = np.nan_to_num(samples.astype(np.float32, copy=False))
    peak = float(np.abs(samples).max(initial=0.0))
    if peak > 0.98:
        samples = samples / peak * 0.98
    samples = np.clip(samples, -0.98, 0.98)
    return samples.astype(np.float32, copy=False)


def _apply_loudness_normalization(
    input_path: Path,
    output_path: Path,
    *,
    target_lufs: float,
    sample_rate: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-af",
        f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        str(output_path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not output_path.is_file():
        raise AudioValidationError(
            f"ffmpeg loudness normalization failed: {result.stderr or result.stdout}"
        )


def _validate_raw_xtts_before_clean(path: Path, *, min_duration_s: float) -> AudioStats:
    """Validate raw XTTS enough to clean it, but do not fail on fixable clipping."""
    stats = analyze_audio(path)
    errors: list[str] = []

    if stats.duration_s < min_duration_s:
        errors.append(
            f"duration {stats.duration_s:.2f}s is below required {min_duration_s:.2f}s"
        )
    if stats.sample_rate < 16000:
        errors.append(f"sample rate {stats.sample_rate} Hz is too low")
    if stats.peak <= 0.005 or stats.rms <= 0.001:
        errors.append("generated audio is empty or nearly silent")
    if stats.silence_ratio > 0.85:
        errors.append(f"generated audio is mostly silence ({stats.silence_ratio:.1%} silent frames)")
    if stats.dropout_ratio > 0.90:
        errors.append(f"generated audio has excessive dropouts ({stats.dropout_ratio:.1%} near-zero frames)")

    if errors:
        raise AudioValidationError(
            f"Invalid raw XTTS generated audio '{stats.path}': " + "; ".join(errors)
        )

    if stats.clipping_ratio > 0.001 or stats.peak >= 0.999:
        logger.warning(
            "Raw XTTS output is clipped/near-clipped before cleanup: path=%s peak=%.3f clipped=%.3f%%",
            path,
            stats.peak,
            stats.clipping_ratio * 100.0,
        )
    return stats


def build_voice_cache_key(
    *,
    text: str,
    reference_audio_path: str | Path,
    model_name: str,
    language: str,
    voice_settings: dict[str, Any] | None = None,
    preprocessing_version: str = PREPROCESSING_VERSION,
) -> str:
    payload = {
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "reference_sha256": file_sha256(reference_audio_path),
        "model_name": model_name,
        "language": language,
        "voice_settings": voice_settings or {},
        "preprocessing_version": preprocessing_version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def clone_voice(
    text: str,
    reference_audio_path: str,
    output_path: str | Path,
    language: str = "en",
    config: VoiceCloneConfig | None = None,
) -> VoiceCloneResult:
    config = config or VoiceCloneConfig()
    output_path = Path(output_path)
    intermediate_dir = Path(config.intermediate_dir)
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    if not config.voice_cloning_required:
        raise VoiceCloningError("XTTS clone_voice called with voice_cloning_required=false")
    if config.allow_generic_tts_fallback:
        raise VoiceCloningError("Generic TTS fallback is forbidden for XTTS voice cloning")
    if not reference_audio_path:
        raise VoiceCloningError("XTTS voice cloning requires speaker_wav reference audio")
    if not (text or "").strip():
        raise VoiceCloningError("XTTS voice cloning requires non-empty text")

    lang = normalize_xtts_language(language or config.language)
    logger.info("XTTS clone requested: model=%s language=%s", config.model_name, lang)
    logger.info("XTTS reference input: %s", reference_audio_path)
    logger.info(
        "XTTS effective settings: temperature=%s repetition_penalty=%s max_chars=%s sample_rate=%s crossfade_ms=%s device=%s",
        config.temperature,
        config.repetition_penalty,
        config.max_chars,
        config.sample_rate,
        config.crossfade_ms,
        config.device,
    )
    logger.info(
        "XTTS post-processing settings: loudness_normalize=%s target_lufs=%s",
        config.loudness_normalize,
        config.target_lufs,
    )
    logger.info("XTTS model_load_timeout_seconds=%s", config.model_load_timeout_seconds)
    logger.info("XTTS generation_timeout_seconds=%s", config.generation_timeout_seconds)

    with _timed_stage("preflight"):
        preflight_xtts_voice_cloning(
            reference_audio_path=reference_audio_path,
            output_path=output_path,
            language=lang,
            config=config,
        )

    with _timed_stage("reference normalization/prep"):
        try:
            cleaned_reference, reference_stats = prepare_reference_audio(
                reference_audio_path,
                intermediate_dir=intermediate_dir,
                sample_rate=config.sample_rate,
            )
        except (ReferenceAudioError, AudioValidationError) as exc:
            raise VoiceCloningError(f"Speaker reference validation failed: {exc}") from exc

    cache_key = build_voice_cache_key(
        text=text,
        reference_audio_path=cleaned_reference,
        model_name=config.model_name,
        language=lang,
        voice_settings={
            "temperature": config.temperature,
            "repetition_penalty": config.repetition_penalty,
            "max_chars": config.max_chars,
            "sample_rate": config.sample_rate,
            "crossfade_ms": config.crossfade_ms,
            "loudness_normalize": config.loudness_normalize,
            "target_lufs": config.target_lufs,
        },
        preprocessing_version=config.preprocessing_version,
    )

    with _timed_stage("model load"):
        tts = _load_xtts_model(config)
    chunks = split_text_for_xtts(text, config.max_chars)
    if not chunks:
        raise VoiceCloningError("XTTS text chunking produced no chunks")

    generated_parts: list[np.ndarray] = []
    with tempfile.TemporaryDirectory(dir=intermediate_dir) as tmpdir:
        tmp = Path(tmpdir)
        for index, chunk in enumerate(chunks):
            chunk_path = tmp / f"xtts_chunk_{index:04d}.wav"
            logger.info(
                "XTTS chunk %d/%d speaker_wav=%s language=%s chars=%d",
                index + 1,
                len(chunks),
                cleaned_reference,
                lang,
                len(chunk),
            )
            generation_start = time.monotonic()
            with _timed_stage(f"speaker conditioning/generation chunk {index + 1}"):
                try:
                    tts.tts_to_file(
                        text=chunk,
                        speaker_wav=str(cleaned_reference),
                        language=lang,
                        file_path=str(chunk_path),
                        temperature=config.temperature,
                        repetition_penalty=config.repetition_penalty,
                    )
                except Exception as exc:
                    raise VoiceCloningError(
                        f"XTTS speaker conditioning or synthesis failed for chunk {index + 1}"
                    ) from exc
            generation_elapsed = time.monotonic() - generation_start
            if generation_elapsed > config.generation_timeout_seconds:
                raise VoiceCloningError(
                    f"XTTS generation exceeded configured timeout for chunk {index + 1}: "
                    f"{generation_elapsed:.2f}s > {config.generation_timeout_seconds}s"
                )
            if not chunk_path.is_file():
                raise VoiceCloningError(f"XTTS did not create chunk output: {chunk_path}")
            try:
                samples, sr = read_audio_mono(chunk_path)
            except AudioValidationError as exc:
                raise VoiceCloningError(f"XTTS chunk output is not decodable: {exc}") from exc
            chunk_duration = len(samples) / float(sr) if sr else 0.0
            chunk_peak = float(np.abs(samples).max(initial=0.0)) if samples.size else 0.0
            chunk_rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
            logger.info(
                "XTTS chunk %d/%d stats: chars=%d duration=%.2fs sample_rate=%s peak=%.4f rms=%.5f path=%s",
                index + 1,
                len(chunks),
                len(chunk),
                chunk_duration,
                sr,
                chunk_peak,
                chunk_rms,
                chunk_path,
            )
            generated_parts.append(_resample_linear(samples, sr, config.sample_rate))

    with _timed_stage("output write/validation"):
        combined_raw = _append_with_crossfade(
            generated_parts,
            config.sample_rate,
            config.crossfade_ms,
        )
        raw_path = intermediate_dir / "xtts_raw.wav"
        clean_path = intermediate_dir / "xtts_clean.wav"
        _write_wav(raw_path, combined_raw, config.sample_rate)

        min_duration = max(0.2, min(4.0, len((text or "").split()) * 0.08))
        try:
            raw_stats = _validate_raw_xtts_before_clean(raw_path, min_duration_s=min_duration)
        except AudioValidationError as exc:
            raise VoiceCloningError(f"Raw XTTS output failed pre-clean validation: {exc}") from exc

        raw_peak = float(np.abs(combined_raw).max(initial=0.0)) if combined_raw.size else 0.0
        peak_normalized = raw_peak > 0.98

        combined_clean = _clean_generated(combined_raw)
        _write_wav(clean_path, combined_clean, config.sample_rate)
        validation_path = clean_path

        if config.loudness_normalize:
            loudness_path = intermediate_dir / "xtts_loudness_normalized.wav"
            try:
                _apply_loudness_normalization(
                    clean_path,
                    loudness_path,
                    target_lufs=config.target_lufs,
                    sample_rate=config.sample_rate,
                )
            except AudioValidationError as exc:
                raise VoiceCloningError(f"XTTS loudness normalization failed: {exc}") from exc
            validation_path = loudness_path

        try:
            generated_stats = validate_generated_audio(validation_path, min_duration_s=min_duration)
        except AudioValidationError as exc:
            raise VoiceCloningError(f"Clean XTTS output failed validation: {exc}") from exc

        logger.info(
            "XTTS output stats: language=%s chunks=%d raw_duration=%.2fs raw_peak=%.3f "
            "clean_duration=%.2fs clean_peak=%.3f clean_rms=%.5f peak_normalized=%s loudness_normalized=%s",
            lang,
            len(chunks),
            raw_stats.duration_s,
            raw_stats.peak,
            generated_stats.duration_s,
            generated_stats.peak,
            generated_stats.rms,
            peak_normalized,
            config.loudness_normalize,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(validation_path, output_path)

    logger.info("XTTS model: %s", config.model_name)
    logger.info("XTTS language: %s", lang)
    logger.info("XTTS speaker_wav used: true")
    logger.info("XTTS fallback attempted: false")
    logger.info("XTTS reference duration: %.2fs", reference_stats.duration_s)
    logger.info("XTTS generated duration: %.2fs", generated_stats.duration_s)
    logger.info("XTTS output: %s", output_path)

    return VoiceCloneResult(
        output_path=str(output_path),
        reference_audio_path=str(Path(reference_audio_path)),
        cleaned_reference_path=str(cleaned_reference),
        raw_xtts_path=str(raw_path),
        clean_xtts_path=str(validation_path),
        model_name=config.model_name,
        language=lang,
        speaker_wav_used=True,
        fallback_attempted=False,
        reference_stats=reference_stats,
        generated_stats=generated_stats,
        cache_key=cache_key,
        chunks=len(chunks),
    )


def config_from_env(language: str = "en") -> VoiceCloneConfig:
    def env_bool(name: str, default: bool) -> bool:
        value = os.environ.get(name, "").strip().lower()
        if not value:
            return default
        return value in {"1", "true", "yes", "on"}

    model = (
        os.environ.get("XTTS_MODEL")
        or os.environ.get("VIDIOLINGUA_XTTS_MODEL")
        or XTTS_V2_MODEL
    )
    intermediate = os.environ.get("VIDIOLINGUA_VOICE_INTERMEDIATE_DIR", "").strip()
    model_path = (
        os.environ.get("VIDIOLINGUA_XTTS_MODEL_PATH")
        or os.environ.get("XTTS_MODEL_PATH")
        or os.environ.get("COQUI_XTTS_MODEL_PATH")
        or ""
    ).strip()
    return VoiceCloneConfig(
        model_name=model,
        model_path=_normalize_model_dir_candidate(Path(model_path)) if model_path else None,
        language=os.environ.get("XTTS_LANGUAGE", language),
        voice_cloning_required=env_bool("VOICE_CLONING_REQUIRED", True)
        or env_bool("VIDIOLINGUA_REQUIRE_VOICE_CLONE", False),
        allow_generic_tts_fallback=env_bool("ALLOW_GENERIC_TTS_FALLBACK", False),
        temperature=float(os.environ.get("VIDIOLINGUA_XTTS_TEMP", str(DEFAULT_XTTS_TEMPERATURE))),
        repetition_penalty=float(
            os.environ.get("VIDIOLINGUA_XTTS_REPETITION_PENALTY", str(DEFAULT_XTTS_REPETITION_PENALTY))
        ),
        max_chars=int(os.environ.get("VIDIOLINGUA_XTTS_MAX_CHARS", str(DEFAULT_XTTS_MAX_CHARS))),
        sample_rate=int(os.environ.get("VIDIOLINGUA_XTTS_SAMPLE_RATE", "24000")),
        crossfade_ms=float(os.environ.get("VIDIOLINGUA_XTTS_CROSSFADE_MS", str(DEFAULT_XTTS_CROSSFADE_MS))),
        loudness_normalize=env_bool("VIDIOLINGUA_AUDIO_LOUDNESS_NORMALIZE", DEFAULT_AUDIO_LOUDNESS_NORMALIZE),
        target_lufs=float(os.environ.get("VIDIOLINGUA_AUDIO_TARGET_LUFS", str(DEFAULT_AUDIO_TARGET_LUFS))),
        intermediate_dir=Path(intermediate) if intermediate else Path("outputs/intermediate"),
        force_regenerate=env_bool("VIDIOLINGUA_FORCE_VOICE_REGENERATE", False),
        model_load_timeout_seconds=int(os.environ.get("XTTS_MODEL_LOAD_TIMEOUT_SECONDS", "600")),
        generation_timeout_seconds=int(os.environ.get("XTTS_GENERATION_TIMEOUT_SECONDS", "300")),
        device=os.environ.get("XTTS_DEVICE", "auto"),
    )
