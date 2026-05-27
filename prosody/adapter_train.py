"""Train a lightweight HuBERT prosody calibration adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prosody.adapter_model import FEATURE_NAMES, baseline_score, cosine_similarity, save_adapter
from voice.hubert_prosody import DEFAULT_MODEL, extract_hubert_features
from voice.prosody_analysis import analyze_source_prosody
from voice.speech_rate import rate_similarity


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _first(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.is_file()), None)


def _discover_job(job_dir: Path) -> dict[str, Path | None]:
    return {
        "source_video": _first([job_dir / "results" / "input_video.mp4", *sorted((job_dir / "asr" / "input").glob("*.mp4"))]),
        "asr_json": _first(sorted((job_dir / "asr" / "output").glob("*.json"))),
        "tts_wav": _first(sorted((job_dir / "tts" / "output").glob("*.wav"))),
    }


def _duration_similarity(source_duration: float | None, target_duration: float | None) -> float | None:
    if not source_duration or not target_duration or source_duration <= 0 or target_duration <= 0:
        return None
    return min(source_duration, target_duration) / max(source_duration, target_duration)


def _scalar_similarity(source: float | None, target: float | None) -> float | None:
    if source is None or target is None:
        return None
    source = abs(float(source))
    target = abs(float(target))
    if source <= 0 and target <= 0:
        return 1.0
    if source <= 0 or target <= 0:
        return 0.0
    return min(source, target) / max(source, target)


def _profile_for_audio(path: Path, asr_json: Path | None, output: Path) -> dict[str, Any]:
    try:
        return analyze_source_prosody(path, asr_json_path=asr_json, output_path=output)
    except Exception:
        return _read_json(output)


def _load_embedding(path: str | Path | None):
    import numpy as np

    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    return np.load(p)


def build_training_example(job_dir: str | Path, work_dir: str | Path, *, model_name: str = DEFAULT_MODEL) -> dict[str, Any]:
    job = Path(job_dir)
    work = Path(work_dir) / job.name
    work.mkdir(parents=True, exist_ok=True)
    paths = _discover_job(job)
    source_video = paths["source_video"]
    asr_json = paths["asr_json"]
    tts_wav = paths["tts_wav"]
    if not source_video or not asr_json or not tts_wav:
        return {"status": "skipped", "job_dir": str(job), "reason": "Missing source video, ASR JSON, or TTS WAV."}
    source_profile = _profile_for_audio(source_video, asr_json, work / "source_prosody_profile.json")
    dub_profile = _profile_for_audio(tts_wav, asr_json, work / "dub_prosody_profile.json")
    source_features = extract_hubert_features(
        audio_path=source_video,
        segments=source_profile.get("segments") if isinstance(source_profile.get("segments"), list) else [],
        output_dir=work / "source_hubert",
        model_name=model_name,
    )
    dub_features = extract_hubert_features(
        audio_path=tts_wav,
        segments=dub_profile.get("segments") if isinstance(dub_profile.get("segments"), list) else [],
        output_dir=work / "dub_hubert",
        model_name=model_name,
    )
    if source_features.get("status") != "computed" or dub_features.get("status") != "computed":
        return {
            "status": "skipped",
            "job_dir": str(job),
            "reason": "HuBERT features were not computed.",
            "source_hubert_status": source_features.get("status"),
            "dub_hubert_status": dub_features.get("status"),
            "errors": [*(source_features.get("errors") or []), *(dub_features.get("errors") or [])],
        }
    source_emb = _load_embedding(source_features.get("global_embedding_path"))
    dub_emb = _load_embedding(dub_features.get("global_embedding_path"))
    if source_emb is None or dub_emb is None:
        return {"status": "skipped", "job_dir": str(job), "reason": "Missing saved HuBERT embedding."}
    source_global = source_profile.get("global") if isinstance(source_profile.get("global"), dict) else {}
    dub_global = dub_profile.get("global") if isinstance(dub_profile.get("global"), dict) else {}
    features = {
        "embedding_cosine": cosine_similarity(source_emb, dub_emb),
        "duration_similarity": _duration_similarity(source_global.get("speech_duration_sec"), dub_global.get("speech_duration_sec")),
        "speech_rate_similarity": rate_similarity(source_global.get("speech_rate_wpm"), dub_global.get("speech_rate_wpm")),
        "energy_similarity": _scalar_similarity(source_global.get("average_energy_rms"), dub_global.get("average_energy_rms")),
        "pause_similarity": _scalar_similarity(source_global.get("pause_count"), dub_global.get("pause_count")),
    }
    target = baseline_score(features)
    return {
        "status": "ready",
        "job_dir": str(job),
        "features": features,
        "target_score_0_1": target,
        "source_hubert": source_features,
        "dub_hubert": dub_features,
    }


def train_adapter(training_jobs: list[str | Path], output_dir: str | Path, *, model_name: str = DEFAULT_MODEL) -> dict[str, Any]:
    import numpy as np

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    work_dir = output / "training_features"
    examples = [build_training_example(job, work_dir, model_name=model_name) for job in training_jobs]
    ready = [item for item in examples if item.get("status") == "ready"]
    limitations = [
        "HuBERT is used as a frozen pretrained feature extractor; it is not trained here.",
        "Targets are calibration heuristics from available project artifacts, not human MOS labels.",
        "Small project datasets produce low confidence until more paired source/dub examples are added.",
    ]
    status = "insufficient_data"
    confidence = "low"
    model_type = "baseline"
    weights = np.asarray([0.38, 0.22, 0.18, 0.12, 0.10], dtype="float32")
    bias = 0.0
    if len(ready) >= 2:
        from prosody.adapter_model import feature_vector

        x = np.stack([feature_vector(item["features"]) for item in ready])
        y = np.asarray([float(item["target_score_0_1"]) for item in ready], dtype="float32")
        x_aug = np.concatenate([x, np.ones((x.shape[0], 1), dtype="float32")], axis=1)
        ridge = 0.1
        identity = np.eye(x_aug.shape[1], dtype="float32")
        identity[-1, -1] = 0.0
        solution = np.linalg.solve(x_aug.T @ x_aug + ridge * identity, x_aug.T @ y)
        weights = solution[:-1].astype("float32")
        bias = float(solution[-1])
        status = "trained"
        model_type = "ridge"
    config = {
        "adapter_name": "HuBERT-guided Prosody Adapter",
        "adapter_status": status if status == "trained" else "baseline",
        "hubert_model": model_name,
        "model_type": model_type,
        "features": FEATURE_NAMES,
        "confidence": confidence,
        "note": "Lightweight calibration layer on top of pretrained HuBERT embeddings; HuBERT was not trained from scratch.",
    }
    save_adapter(output, weights, bias, config)
    report = {
        "status": status,
        "training_examples": len(ready),
        "attempted_jobs": len(training_jobs),
        "model_type": model_type,
        "features": FEATURE_NAMES,
        "validation_method": "leave-in project calibration report; no held-out set because data is small",
        "confidence": confidence,
        "limitations": limitations,
        "examples": examples,
        "artifact_dir": str(output),
    }
    (output / "training_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
