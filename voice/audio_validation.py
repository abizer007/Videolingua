"""Strict audio validation helpers for generated and reference speech."""

from __future__ import annotations

import json
import math
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

try:
    import numpy as np
except ImportError:  # API env can validate simple WAVs without the ML stack.
    np = None


class AudioValidationError(RuntimeError):
    """Raised when an audio file is not safe to use for voice cloning."""


@dataclass
class AudioStats:
    path: str
    duration_s: float
    sample_rate: int
    channels: int
    peak: float
    rms: float
    silence_ratio: float
    clipping_ratio: float
    dropout_ratio: float
    codec_name: str = ""
    format_name: str = ""
    warnings: list[str] = field(default_factory=list)


def _run_ffprobe(path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise AudioValidationError(
            f"ffprobe could not decode audio file '{path}': {result.stderr or result.stdout}"
        )
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise AudioValidationError(f"ffprobe returned invalid metadata for '{path}'") from exc


def _probe_stream(path: Path) -> tuple[float, int, int, str, str]:
    metadata = _run_ffprobe(path)
    streams = [s for s in metadata.get("streams", []) if s.get("codec_type") == "audio"]
    if not streams:
        raise AudioValidationError(f"Audio file '{path}' has no audio stream")
    stream = streams[0]
    fmt = metadata.get("format", {})
    duration_raw = stream.get("duration") or fmt.get("duration") or 0
    try:
        duration_s = float(duration_raw)
    except (TypeError, ValueError):
        duration_s = 0.0
    try:
        sample_rate = int(stream.get("sample_rate") or 0)
    except (TypeError, ValueError):
        sample_rate = 0
    try:
        channels = int(stream.get("channels") or 0)
    except (TypeError, ValueError):
        channels = 0
    return (
        duration_s,
        sample_rate,
        channels,
        str(stream.get("codec_name") or ""),
        str(fmt.get("format_name") or ""),
    )


def _read_wav_mono_without_numpy(path: Path) -> tuple[list[float], int]:
    try:
        with wave.open(str(path), "rb") as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
    except wave.Error as exc:
        raise AudioValidationError(f"WAV file '{path}' is corrupted or unreadable") from exc

    if not frames:
        raise AudioValidationError(f"Audio file '{path}' contains no samples")
    if width != 2:
        raise AudioValidationError(
            f"WAV file '{path}' has unsupported sample width {width}; use PCM 16-bit WAV"
        )

    import array

    values = array.array("h")
    values.frombytes(frames)
    if values.itemsize != 2:
        values.byteswap()
    if channels > 1:
        samples = [
            sum(values[index : index + channels]) / (channels * 32768.0)
            for index in range(0, len(values), channels)
        ]
    else:
        samples = [value / 32768.0 for value in values]
    return samples, int(sample_rate)


def read_audio_mono(path: Path):
    """Decode an audio file to mono float32 samples in [-1, 1]."""
    path = Path(path)
    try:
        import soundfile as sf

        data, sample_rate = sf.read(str(path), always_2d=True, dtype="float32")
        if data.size == 0:
            raise AudioValidationError(f"Audio file '{path}' contains no samples")
        mono = data.mean(axis=1)
        if np is not None:
            return mono.astype(np.float32, copy=False), int(sample_rate)
        return [float(value) for value in mono], int(sample_rate)
    except ImportError:
        pass
    except Exception as exc:
        if path.suffix.lower() != ".wav":
            raise AudioValidationError(f"Could not decode '{path}' with soundfile") from exc

    if path.suffix.lower() != ".wav":
        raise AudioValidationError(
            f"Audio file '{path}' is not WAV and soundfile is unavailable for decoding"
        )

    try:
        with wave.open(str(path), "rb") as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
    except wave.Error as exc:
        raise AudioValidationError(f"WAV file '{path}' is corrupted or unreadable") from exc

    if not frames:
        raise AudioValidationError(f"Audio file '{path}' contains no samples")
    if width != 2:
        raise AudioValidationError(
            f"WAV file '{path}' has unsupported sample width {width}; use PCM 16-bit WAV"
        )
    if np is None:
        return _read_wav_mono_without_numpy(path)
    data = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data.astype(np.float32, copy=False), int(sample_rate)


def _window_rms(samples, sample_rate: int, window_ms: float = 30.0):
    window = max(1, int(sample_rate * window_ms / 1000.0))
    usable = len(samples) - (len(samples) % window)
    if usable <= 0:
        return np.array([], dtype=np.float32) if np is not None else []
    if np is not None:
        framed = samples[:usable].reshape(-1, window)
        return np.sqrt(np.mean(np.square(framed), axis=1))
    return [
        math.sqrt(sum(value * value for value in samples[index : index + window]) / window)
        for index in range(0, usable, window)
    ]


def _all_finite(samples: Sequence[float]) -> bool:
    if np is not None:
        return bool(np.all(np.isfinite(samples)))
    return all(math.isfinite(float(value)) for value in samples)


def _mean_below(values, threshold: float) -> float:
    if len(values) == 0:
        return 1.0
    if np is not None:
        return float(np.mean(values < threshold))
    return sum(1 for value in values if value < threshold) / float(len(values))


def _sample_metrics(samples) -> tuple[float, float, float]:
    if len(samples) == 0:
        return 0.0, 0.0, 0.0
    if np is not None:
        abs_samples = np.abs(samples)
        peak = float(abs_samples.max(initial=0.0))
        rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
        clipping_ratio = float(np.mean(abs_samples >= 0.995)) if abs_samples.size else 0.0
        return peak, rms, clipping_ratio
    abs_samples = [abs(float(value)) for value in samples]
    peak = max(abs_samples, default=0.0)
    rms = math.sqrt(sum(float(value) * float(value) for value in samples) / len(samples))
    clipping_ratio = sum(1 for value in abs_samples if value >= 0.995) / float(len(abs_samples))
    return peak, rms, clipping_ratio


def analyze_audio(path: str | Path) -> AudioStats:
    path = Path(path)
    if not path.is_file():
        raise AudioValidationError(f"Audio file is missing: {path}")
    if path.stat().st_size <= 44:
        raise AudioValidationError(f"Audio file is empty or header-only: {path}")

    duration_s, probed_sr, channels, codec, fmt = _probe_stream(path)
    samples, decoded_sr = read_audio_mono(path)
    sample_rate = decoded_sr or probed_sr
    if sample_rate <= 0:
        raise AudioValidationError(f"Audio file '{path}' has invalid sample rate")
    if duration_s <= 0:
        duration_s = len(samples) / float(sample_rate)
    if duration_s <= 0 or not math.isfinite(duration_s):
        raise AudioValidationError(f"Audio file '{path}' has invalid duration")
    if not _all_finite(samples):
        raise AudioValidationError(f"Audio file '{path}' contains NaN or infinite samples")

    frame_rms = _window_rms(samples, sample_rate)
    peak, rms, clipping_ratio = _sample_metrics(samples)
    frame_count = int(frame_rms.size) if np is not None else len(frame_rms)
    silence_ratio = _mean_below(frame_rms, 0.006) if frame_count else 1.0
    dropout_ratio = _mean_below(frame_rms, 0.0008) if frame_count else 1.0

    return AudioStats(
        path=str(path),
        duration_s=float(duration_s),
        sample_rate=int(sample_rate),
        channels=int(channels or 1),
        peak=peak,
        rms=rms,
        silence_ratio=silence_ratio,
        clipping_ratio=clipping_ratio,
        dropout_ratio=dropout_ratio,
        codec_name=codec,
        format_name=fmt,
    )


def validate_reference_audio(
    path: str | Path,
    *,
    min_duration_s: float = 6.0,
    max_duration_s: float = 60.0,
    max_silence_ratio: float = 0.65,
    max_clipping_ratio: float = 0.001,
) -> AudioStats:
    stats = analyze_audio(path)
    errors: list[str] = []

    if stats.duration_s < min_duration_s:
        errors.append(
            f"duration {stats.duration_s:.2f}s is below required {min_duration_s:.2f}s"
        )
    if stats.duration_s > max_duration_s:
        errors.append(
            f"duration {stats.duration_s:.2f}s exceeds allowed {max_duration_s:.2f}s"
        )
    if stats.sample_rate < 16000:
        errors.append(f"sample rate {stats.sample_rate} Hz is too low for XTTS cloning")
    if stats.peak <= 0.005 or stats.rms <= 0.001:
        errors.append("audio appears empty or nearly silent")
    if stats.silence_ratio > max_silence_ratio:
        errors.append(
            f"audio is mostly silence ({stats.silence_ratio:.1%} silent frames)"
        )
    if stats.clipping_ratio > max_clipping_ratio or stats.peak >= 0.999:
        errors.append(
            f"audio is clipped (peak={stats.peak:.3f}, clipped={stats.clipping_ratio:.3%})"
        )

    if errors:
        raise AudioValidationError(
            f"Invalid XTTS reference audio '{stats.path}': " + "; ".join(errors)
        )
    return stats


def validate_generated_audio(
    path: str | Path,
    *,
    min_duration_s: float = 0.2,
    max_silence_ratio: float = 0.85,
    max_clipping_ratio: float = 0.001,
) -> AudioStats:
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
    if stats.silence_ratio > max_silence_ratio:
        errors.append(
            f"generated audio is mostly silence ({stats.silence_ratio:.1%} silent frames)"
        )
    if stats.dropout_ratio > 0.90:
        errors.append(
            f"generated audio has excessive dropouts ({stats.dropout_ratio:.1%} near-zero frames)"
        )
    if stats.clipping_ratio > max_clipping_ratio or stats.peak >= 0.999:
        errors.append(
            f"generated audio is clipped (peak={stats.peak:.3f}, clipped={stats.clipping_ratio:.3%})"
        )

    if errors:
        raise AudioValidationError(
            f"Invalid generated audio '{stats.path}': " + "; ".join(errors)
        )
    return stats


def normalize_pcm16_wav_peak(
    input_path: str | Path,
    output_path: str | Path,
    *,
    target_peak: float = 0.95,
) -> AudioStats:
    """Write a PCM16 WAV with peak safely attenuated to target_peak."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not 0.0 < target_peak < 1.0:
        raise AudioValidationError(f"target_peak must be between 0 and 1, got {target_peak}")

    try:
        with wave.open(str(input_path), "rb") as src:
            params = src.getparams()
            frames = src.readframes(src.getnframes())
    except wave.Error as exc:
        raise AudioValidationError(f"WAV file '{input_path}' is corrupted or unreadable") from exc

    if not frames:
        raise AudioValidationError(f"Audio file '{input_path}' contains no samples")
    if params.sampwidth != 2:
        raise AudioValidationError(
            f"WAV file '{input_path}' has unsupported sample width {params.sampwidth}; use PCM 16-bit WAV"
        )

    import array
    import sys

    values = array.array("h")
    values.frombytes(frames)
    if sys.byteorder != "little":
        values.byteswap()

    max_abs = max((abs(value) for value in values), default=0)
    if max_abs <= 0:
        raise AudioValidationError(f"Audio file '{input_path}' contains no non-zero samples")

    target_abs = max(1, int(round(32767 * target_peak)))
    scale = min(1.0, target_abs / float(max_abs))
    if scale < 1.0:
        values = array.array(
            "h",
            (
                max(-32768, min(32767, int(round(value * scale))))
                for value in values
            ),
        )

    if sys.byteorder != "little":
        values.byteswap()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as dst:
        dst.setparams(params)
        dst.writeframes(values.tobytes())

    return analyze_audio(output_path)


def file_sha256(path: str | Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
