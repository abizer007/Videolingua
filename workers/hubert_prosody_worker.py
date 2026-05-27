"""Isolated HuBERT feature extraction worker.

Run this only from .venv_prosody. It loads pretrained HuBERT as a frozen
feature extractor and writes embeddings to job-local output folders.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _extract_wav(input_path: Path, wav_path: Path, sample_rate: int = 16000) -> None:
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


def _load_audio(audio_path: Path):
    import soundfile as sf

    audio, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=False)
    if getattr(audio, "ndim", 1) > 1:
        audio = audio.mean(axis=1)
    return audio, int(sample_rate)


def _segment_audio(audio, sample_rate: int, start_sec: float, end_sec: float):
    start = max(0, int(start_sec * sample_rate))
    end = min(len(audio), max(start + 1, int(end_sec * sample_rate)))
    return audio[start:end]


def _embed(model, processor, torch, audio, sample_rate: int, device: str):
    inputs = processor(audio, sampling_rate=sample_rate, return_tensors="pt", padding=True)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.no_grad():
        hidden = model(**inputs).last_hidden_state
        embedding = hidden.mean(dim=1).squeeze(0).detach().cpu().numpy()
    return embedding


def compute(request: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    import torch
    from transformers import AutoFeatureExtractor, HubertModel

    output_dir = Path(request["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    model_name = request.get("model_name") or "facebook/hubert-base-ls960"
    requested_device = str(request.get("device") or "auto").lower()
    device = "cuda" if requested_device in {"auto", "cuda"} and torch.cuda.is_available() else "cpu"
    warnings: list[str] = []
    if requested_device == "cuda" and device == "cpu":
        warnings.append("CUDA was requested but is unavailable; HuBERT ran on CPU.")

    source_audio = Path(request["audio_path"])
    temp_dir = tempfile.TemporaryDirectory(dir=str(output_dir))
    try:
        wav_path = Path(temp_dir.name) / "hubert_input.wav"
        _extract_wav(source_audio, wav_path)
        audio, sample_rate = _load_audio(wav_path)
        if sample_rate != 16000:
            raise RuntimeError(f"Expected 16 kHz audio after extraction, got {sample_rate}.")

        processor = AutoFeatureExtractor.from_pretrained(model_name)
        model = HubertModel.from_pretrained(model_name)
        model.to(device)
        model.eval()

        global_embedding = _embed(model, processor, torch, audio, sample_rate, device)
        global_path = output_dir / "hubert_global_embedding.npy"
        np.save(global_path, global_embedding)
        segment_results: list[dict[str, Any]] = []
        for index, segment in enumerate(request.get("segments") or []):
            if not isinstance(segment, dict):
                continue
            try:
                start = float(segment.get("start", 0.0))
                end = float(segment.get("end", start))
            except (TypeError, ValueError):
                continue
            if end <= start:
                continue
            clip = _segment_audio(audio, sample_rate, start, end)
            if len(clip) < int(sample_rate * 0.2):
                warnings.append(f"Segment {index} is too short for a stable HuBERT embedding.")
                continue
            embedding = _embed(model, processor, torch, clip, sample_rate, device)
            seg_id = str(segment.get("id") or segment.get("segment_id") or index)
            seg_path = output_dir / f"hubert_segment_{index:04d}.npy"
            np.save(seg_path, embedding)
            segment_results.append(
                {
                    "segment_id": seg_id,
                    "index": index,
                    "embedding_path": str(seg_path),
                    "duration_sec": round(end - start, 3),
                    "start_sec": round(start, 3),
                    "end_sec": round(end, 3),
                }
            )
        return {
            "status": "computed",
            "model": model_name,
            "device": device,
            "embedding_dim": int(global_embedding.shape[0]),
            "segment_embeddings": segment_results,
            "global_embedding_path": str(global_path),
            "warnings": warnings,
            "errors": [],
            "note": "Pretrained HuBERT was used as a frozen feature extractor.",
        }
    finally:
        temp_dir.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    response_path = Path(args.response)
    try:
        response = compute(request)
    except Exception as exc:
        response = {
            "status": "failed",
            "model": request.get("model_name") or "facebook/hubert-base-ls960",
            "embedding_dim": None,
            "segment_embeddings": [],
            "global_embedding_path": None,
            "warnings": [],
            "errors": [str(exc)],
        }
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text(json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if response.get("status") == "computed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
