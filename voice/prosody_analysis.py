"""Source prosody analysis for Vidiolingua jobs."""

from __future__ import annotations

import audioop
import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from voice.pause_detection import detect_pauses_from_segments, pause_summary
from voice.prosody_profile import SegmentProsody, base_profile
from voice.speech_rate import classify_rate, count_words, segment_duration, words_per_minute


def _run_ffmpeg_extract(input_path: Path, wav_path: Path, sample_rate: int = 16000) -> None:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            str(wav_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr or result.stdout}")


def _read_wav_pcm(path: Path) -> tuple[bytes, int, int]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if channels > 1:
        frames = audioop.tomono(frames, sample_width, 0.5, 0.5)
    return frames, sample_rate, sample_width


def _slice_audio(frames: bytes, sample_rate: int, sample_width: int, start_sec: float, end_sec: float) -> bytes:
    start = max(0, int(start_sec * sample_rate) * sample_width)
    end = max(start, int(end_sec * sample_rate) * sample_width)
    return frames[start:min(end, len(frames))]


def _rms_normalized(chunk: bytes, sample_width: int) -> float | None:
    if not chunk:
        return None
    rms = audioop.rms(chunk, sample_width)
    max_value = float(2 ** (8 * sample_width - 1))
    return rms / max_value if max_value else None


def _energy_class(value: float | None, low: float, high: float) -> str:
    if value is None:
        return "unknown"
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "medium"


def _punctuation_style(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.endswith("?"):
        return "question"
    if stripped.endswith("!"):
        return "exclamation"
    if stripped.endswith((",", ";", ":")):
        return "continuation"
    return "statement"


def _emphasis_hints(text: str, rate_class: str, energy_class: str) -> list[str]:
    hints: list[str] = []
    if _punctuation_style(text) == "question":
        hints.append("rising_question_delivery")
    if _punctuation_style(text) == "exclamation":
        hints.append("heightened_punctuation")
    if rate_class in {"fast", "rushed"}:
        hints.append("protect_intelligibility")
    if energy_class == "high":
        hints.append("source_energy_peak")
    return hints


def _energy_contour(frames: bytes, sample_rate: int, sample_width: int, frame_ms: int = 250) -> dict[str, Any]:
    bytes_per_frame = max(sample_width, int(sample_rate * frame_ms / 1000.0) * sample_width)
    values: list[float] = []
    for offset in range(0, len(frames), bytes_per_frame):
        value = _rms_normalized(frames[offset:offset + bytes_per_frame], sample_width)
        if value is not None:
            values.append(value)
    if not values:
        return {"status": "unavailable", "values": [], "average_rms": None, "peak_rms": None}
    compact = [round(value, 6) for value in values[:: max(1, math.ceil(len(values) / 80))]]
    return {
        "status": "computed",
        "frame_ms": frame_ms,
        "values": compact,
        "average_rms": round(sum(values) / len(values), 6),
        "peak_rms": round(max(values), 6),
    }


def analyze_source_prosody(
    source_audio_or_video: str | Path,
    *,
    asr_json_path: str | Path | None = None,
    output_path: str | Path | None = None,
    keep_extracted_wav: bool = False,
) -> dict[str, Any]:
    source = Path(source_audio_or_video)
    asr_path = Path(asr_json_path) if asr_json_path else None
    profile = base_profile(source_audio_path=str(source), asr_json_path=str(asr_path) if asr_path else None)
    segments: list[dict[str, Any]] = []
    if asr_path and asr_path.is_file():
        data = json.loads(asr_path.read_text(encoding="utf-8"))
        raw_segments = data.get("segments")
        if isinstance(raw_segments, list):
            segments = [item for item in raw_segments if isinstance(item, dict)]
        profile["source_language"] = data.get("language")
    else:
        profile["warnings"].append("No ASR JSON supplied; segment-level rate and pause analysis is limited.")

    output = Path(output_path) if output_path else None
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir_obj: tempfile.TemporaryDirectory[str] | None = None
    try:
        if source.suffix.lower() == ".wav":
            wav_path = source
        else:
            temp_dir_obj = tempfile.TemporaryDirectory(dir=str(output.parent if output else None))
            wav_path = Path(temp_dir_obj.name) / "source_for_prosody.wav"
            _run_ffmpeg_extract(source, wav_path)
        frames, sample_rate, sample_width = _read_wav_pcm(wav_path)
        profile["analysis_audio"] = {
            "path": str(wav_path if keep_extracted_wav else source),
            "sample_rate": sample_rate,
            "sample_width_bytes": sample_width,
            "duration_sec": round((len(frames) / sample_width) / sample_rate, 3) if sample_rate and sample_width else None,
        }
        energy = _energy_contour(frames, sample_rate, sample_width)
        profile["energy_profile"] = energy
        global_avg = energy.get("average_rms") if isinstance(energy, dict) else None
        global_peak = energy.get("peak_rms") if isinstance(energy, dict) else None
        low_threshold = float(global_avg or 0.0) * 0.65
        high_threshold = float(global_avg or 0.0) * 1.4

        segment_profiles: list[SegmentProsody] = []
        total_words = 0
        total_speech_duration = 0.0
        for index, segment in enumerate(segments):
            start = float(segment.get("start", 0.0) or 0.0)
            end = float(segment.get("end", start) or start)
            duration = segment_duration(segment)
            text = str(segment.get("text") or "").strip()
            words = count_words(text)
            total_words += words
            total_speech_duration += duration
            wpm = words_per_minute(words, duration)
            rate_class = classify_rate(wpm)
            chunk = _slice_audio(frames, sample_rate, sample_width, start, end)
            segment_rms = _rms_normalized(chunk, sample_width)
            energy_class = _energy_class(segment_rms, low_threshold, high_threshold)
            segment_profiles.append(
                SegmentProsody(
                    segment_id=str(segment.get("id") or segment.get("segment_id") or index),
                    index=index,
                    start_sec=start,
                    end_sec=end,
                    duration_sec=duration,
                    text=text,
                    word_count=words,
                    speech_rate_wpm=wpm,
                    rate_class=rate_class,
                    energy_class=energy_class,
                    average_rms=segment_rms,
                    peak_rms=segment_rms,
                    emphasis_hints=_emphasis_hints(text, rate_class, energy_class),
                    punctuation_style=_punctuation_style(text),
                )
            )
        pauses = detect_pauses_from_segments(segments)
        pause_stats = pause_summary(pauses)
        global_wpm = words_per_minute(total_words, total_speech_duration)
        profile["global"] = {
            "segment_count": len(segment_profiles),
            "speech_duration_sec": round(total_speech_duration, 3),
            "word_count": total_words,
            "speech_rate_wpm": round(global_wpm, 3) if global_wpm is not None else None,
            "speech_rate_class": classify_rate(global_wpm),
            "pause_count": pause_stats["pause_count"],
            "average_pause_sec": pause_stats["average_pause_sec"],
            "total_pause_sec": pause_stats["total_pause_sec"],
            "average_energy_rms": global_avg,
            "peak_energy_rms": global_peak,
        }
        profile["pauses"] = pauses
        profile["segments"] = [item.to_dict() for item in segment_profiles]
        profile["intonation_proxy"] = {
            "status": "computed" if segment_profiles else "unavailable",
            "question_segments": sum(1 for item in segment_profiles if item.punctuation_style == "question"),
            "exclamation_segments": sum(1 for item in segment_profiles if item.punctuation_style == "exclamation"),
            "continuation_segments": sum(1 for item in segment_profiles if item.punctuation_style == "continuation"),
        }
        profile["summary"] = {
            "status": "computed",
            "speech_rate_class": profile["global"]["speech_rate_class"],
            "pause_count": pause_stats["pause_count"],
            "average_pause_sec": pause_stats["average_pause_sec"],
            "energy_status": energy.get("status"),
            "pitch_status": profile["pitch_profile"]["status"],
        }
    except Exception as exc:
        profile["summary"] = {"status": "failed"}
        profile["errors"].append(str(exc))
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
        raise
    finally:
        if temp_dir_obj is not None and not keep_extracted_wav:
            temp_dir_obj.cleanup()

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    return profile
