"""Generate small XTTS voice-cloning A/B WAV samples from existing translations.

This is intentionally TTS-only: it does not run ASR, translation, lipsync, muxing,
or the full pipeline. It reuses the existing strict XTTS clone_voice path.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from voice.audio_validation import analyze_audio, read_audio_mono
from voice.xtts_cloner import (
    VoiceCloneConfig,
    clone_voice,
    split_text_for_xtts,
    _resample_linear,
    _write_wav,
)


PRESETS: dict[str, dict[str, float | int]] = {
    "A": {
        "temperature": 0.65,
        "repetition_penalty": 10.0,
        "max_chars": 200,
        "crossfade_ms": 12.0,
    },
    "B": {
        "temperature": 0.45,
        "repetition_penalty": 8.0,
        "max_chars": 180,
        "crossfade_ms": 25.0,
    },
    "C": {
        "temperature": 0.50,
        "repetition_penalty": 7.0,
        "max_chars": 160,
        "crossfade_ms": 30.0,
    },
    "D": {
        "temperature": 0.55,
        "repetition_penalty": 8.5,
        "max_chars": 240,
        "crossfade_ms": 35.0,
    },
    "E": {
        "temperature": 0.35,
        "repetition_penalty": 6.5,
        "max_chars": 140,
        "crossfade_ms": 40.0,
    },
}


def _load_translation(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _segment_text(segment: dict[str, Any]) -> str:
    for key in ("text", "translation", "translated_text", "target_text"):
        value = segment.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _select_representative_segments(data: dict[str, Any], max_segments: int) -> list[dict[str, Any]]:
    source_segments = data.get("segments") or []
    candidates: list[dict[str, Any]] = []
    for index, segment in enumerate(source_segments):
        if not isinstance(segment, dict):
            continue
        text = _segment_text(segment)
        if not text:
            continue
        item = dict(segment)
        item["_source_index"] = index
        item["_text"] = text
        item["_chars"] = len(text)
        candidates.append(item)

    if not candidates or max_segments <= 0:
        return []
    if len(candidates) <= max_segments:
        return candidates

    selected: list[dict[str, Any]] = []

    def add(item: dict[str, Any]) -> None:
        if item not in selected and len(selected) < max_segments:
            selected.append(item)

    add(min(candidates, key=lambda item: item["_chars"]))
    sorted_by_len = sorted(candidates, key=lambda item: item["_chars"])
    add(sorted_by_len[len(sorted_by_len) // 2])
    add(max(candidates, key=lambda item: item["_chars"]))
    punctuated = [
        item
        for item in candidates
        if any(mark in item["_text"] for mark in (".", ",", "?", "!", ";", ":"))
    ]
    if punctuated:
        add(max(punctuated, key=lambda item: item["_text"].count(",") + item["_text"].count(".")))

    for item in candidates:
        add(item)
        if len(selected) >= max_segments:
            break

    return sorted(selected, key=lambda item: item["_source_index"])


def _concat_for_listening(wav_paths: list[Path], output_path: Path, sample_rate: int) -> None:
    parts: list[np.ndarray] = []
    gap = np.zeros(int(sample_rate * 0.35), dtype=np.float32)
    for index, wav_path in enumerate(wav_paths):
        samples, sr = read_audio_mono(wav_path)
        if sr != sample_rate:
            samples = _resample_linear(samples, sr, sample_rate)
        if index:
            parts.append(gap)
        parts.append(samples.astype(np.float32, copy=False))
    combined = np.concatenate(parts) if parts else np.zeros(int(sample_rate * 0.1), dtype=np.float32)
    _write_wav(output_path, combined, sample_rate)


def _edge_silence(samples: np.ndarray, sample_rate: int, threshold: float = 0.006) -> tuple[float, float]:
    if samples.size == 0:
        return 0.0, 0.0
    active = np.flatnonzero(np.abs(samples) >= threshold)
    if active.size == 0:
        duration = len(samples) / float(sample_rate)
        return duration, duration
    leading = float(active[0]) / float(sample_rate)
    trailing = float(len(samples) - active[-1] - 1) / float(sample_rate)
    return leading, trailing


def _audio_report(path: Path) -> dict[str, Any]:
    stats = analyze_audio(path)
    samples, sr = read_audio_mono(path)
    leading_s, trailing_s = _edge_silence(samples, sr)
    rms_dbfs = 20.0 * math.log10(max(stats.rms, 1e-12))
    return {
        **asdict(stats),
        "rms_dbfs_approx": rms_dbfs,
        "leading_silence_s": leading_s,
        "trailing_silence_s": trailing_s,
        "clipping_warning": bool(stats.clipping_ratio > 0.001 or stats.peak >= 0.999),
    }


def _effective_device(requested: str) -> str:
    if requested == "auto":
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "auto"
    return requested


def _run_preset(
    *,
    preset_name: str,
    settings: dict[str, float | int],
    selected_segments: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    language_dir = Path(args.output_dir) / args.language
    preset_dir = language_dir / f"preset_{preset_name}"
    chunks_dir = preset_dir / "chunks"
    combined_path = preset_dir / "combined.wav"
    report_path = preset_dir / "report.json"

    if combined_path.exists() or report_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing A/B output for preset {preset_name}: {preset_dir}"
        )

    chunks_dir.mkdir(parents=True, exist_ok=True)
    intermediate_dir = preset_dir / "intermediate"

    config = VoiceCloneConfig(
        model_path=Path(args.model_path),
        language=args.language,
        temperature=float(settings["temperature"]),
        repetition_penalty=float(settings["repetition_penalty"]),
        max_chars=int(settings["max_chars"]),
        crossfade_ms=float(settings["crossfade_ms"]),
        intermediate_dir=intermediate_dir,
        device=args.device,
    )

    started = time.monotonic()
    chunk_paths: list[Path] = []
    chunk_reports: list[dict[str, Any]] = []
    total_internal_chunks = 0

    for output_index, segment in enumerate(selected_segments, start=1):
        source_index = int(segment["_source_index"])
        text = str(segment["_text"])
        chunk_path = chunks_dir / f"segment_{output_index:02d}_source_{source_index:04d}.wav"
        text_chunks = split_text_for_xtts(text, config.max_chars)
        total_internal_chunks += len(text_chunks)
        segment_started = time.monotonic()
        result = clone_voice(
            text=text,
            reference_audio_path=str(args.reference),
            output_path=chunk_path,
            language=args.language,
            config=config,
        )
        segment_stats = _audio_report(chunk_path)
        chunk_paths.append(chunk_path)
        chunk_reports.append(
            {
                "source_index": source_index,
                "text": text,
                "text_chars": len(text),
                "internal_text_chunks": text_chunks,
                "generation_time_s": time.monotonic() - segment_started,
                "output_path": str(chunk_path),
                "clone_result": result.to_report(),
                "audio": segment_stats,
            }
        )

    _concat_for_listening(chunk_paths, combined_path, config.sample_rate)
    combined_audio = _audio_report(combined_path)
    generation_time = time.monotonic() - started

    report = {
        "preset_name": f"preset_{preset_name}",
        "language": args.language,
        "translation_json": str(args.translation_json),
        "reference_audio_path": str(args.reference),
        "model_path": str(args.model_path),
        "device_requested": args.device,
        "device_used": _effective_device(args.device),
        "temperature": config.temperature,
        "repetition_penalty": config.repetition_penalty,
        "max_chars": config.max_chars,
        "crossfade_ms": config.crossfade_ms,
        "sample_rate": config.sample_rate,
        "selected_segment_texts": [str(item["_text"]) for item in selected_segments],
        "selected_segments": [
            {
                "source_index": int(item["_source_index"]),
                "start": item.get("start"),
                "end": item.get("end"),
                "text": str(item["_text"]),
                "text_chars": int(item["_chars"]),
            }
            for item in selected_segments
        ],
        "chunk_count": len(chunk_paths),
        "internal_text_chunk_count": total_internal_chunks,
        "generated_duration": combined_audio["duration_s"],
        "peak_amplitude": combined_audio["peak"],
        "rms": combined_audio["rms"],
        "rms_dbfs_approx": combined_audio["rms_dbfs_approx"],
        "clipping_warning": combined_audio["clipping_warning"],
        "silence_ratio": combined_audio["silence_ratio"],
        "generation_time": generation_time,
        "output_wav_path": str(combined_path),
        "chunks_dir": str(chunks_dir),
        "chunks": chunk_reports,
        "combined_audio": combined_audio,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translation-json", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    parser.add_argument("--max-segments", type=int, default=5)
    parser.add_argument(
        "--preset",
        default="all",
        help="Preset letter A-E, a comma-separated list, or all.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    translation = _load_translation(args.translation_json)
    selected_segments = _select_representative_segments(translation, args.max_segments)
    if not selected_segments:
        raise SystemExit("No non-empty translated segments found.")

    preset_arg = args.preset.strip().upper()
    if preset_arg == "ALL":
        preset_names = list(PRESETS)
    else:
        preset_names = [name.strip() for name in preset_arg.split(",") if name.strip()]

    unknown = [name for name in preset_names if name not in PRESETS]
    if unknown:
        raise SystemExit(f"Unknown preset(s): {', '.join(unknown)}")

    summary: list[dict[str, Any]] = []
    for preset_name in preset_names:
        print(f"[AB] Generating preset {preset_name}")
        report = _run_preset(
            preset_name=preset_name,
            settings=PRESETS[preset_name],
            selected_segments=selected_segments,
            args=args,
        )
        summary.append(
            {
                "preset": report["preset_name"],
                "combined": report["output_wav_path"],
                "duration_s": report["generated_duration"],
                "peak": report["peak_amplitude"],
                "rms": report["rms"],
                "silence_ratio": report["silence_ratio"],
                "generation_time_s": report["generation_time"],
            }
        )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
