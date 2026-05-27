"""IndicF5 voice engine adapter backed by an isolated worker subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from voice.base import VoiceSynthesisError, VoiceSynthesisRequest, VoiceSynthesisResult, normalize_voice_language


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDICF5_PYTHON = PROJECT_ROOT / ".venv_indicf5" / "Scripts" / "python.exe"
DEFAULT_MODEL_NAME = "ai4bharat/IndicF5"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models" / "indicf5" / "IndicF5"
DEFAULT_CHECKPOINT_PATH = DEFAULT_MODEL_DIR / "model.safetensors"


class IndicF5Engine:
    name = "indicf5"
    model_name = DEFAULT_MODEL_NAME

    def _python_path(self) -> Path:
        configured = os.environ.get("VIDIOLINGUA_INDICF5_PYTHON", "").strip()
        path = Path(configured) if configured else DEFAULT_INDICF5_PYTHON
        if not path.is_file():
            raise VoiceSynthesisError(
                "IndicF5 runtime is not installed. Expected Python at "
                f"{path}. Run scripts\\setup_indicf5_env.ps1 -Run only after approval."
            )
        return path

    def synthesize(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        worker = PROJECT_ROOT / "workers" / "indicf5_worker.py"
        if not worker.is_file():
            raise VoiceSynthesisError(f"IndicF5 worker not found: {worker}")

        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        model_name = os.environ.get("VIDIOLINGUA_INDICF5_MODEL", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME
        model_dir = os.environ.get("VIDIOLINGUA_INDICF5_MODEL_DIR", str(DEFAULT_MODEL_DIR)).strip() or str(DEFAULT_MODEL_DIR)
        checkpoint_path = os.environ.get(
            "VIDIOLINGUA_INDICF5_CKPT_PATH",
            "",
        ).strip() or os.environ.get(
            "VIDIOLINGUA_INDICF5_CHECKPOINT_PATH",
            str(DEFAULT_CHECKPOINT_PATH),
        ).strip() or str(DEFAULT_CHECKPOINT_PATH)
        device = os.environ.get("VIDIOLINGUA_INDICF5_DEVICE", "cuda").strip() or "cuda"
        timeout = int(os.environ.get("VIDIOLINGUA_INDICF5_TIMEOUT_SECONDS", "600"))

        payload = {
            "text": request.text,
            "target_language": normalize_voice_language(request.target_language),
            "output_path": str(request.output_path),
            "reference_audio_path": str(request.reference_audio_path) if request.reference_audio_path else "",
            "reference_text": request.reference_text or "",
            "model_name": model_name,
            "model_dir": model_dir,
            "checkpoint_path": checkpoint_path,
            "device": device,
            "dtype": os.environ.get("VIDIOLINGUA_INDICF5_DTYPE", "float16" if device.startswith("cuda") else "float32"),
            "batch_size": 1,
            "max_text_chars": int(os.environ.get("VIDIOLINGUA_INDICF5_MAX_TEXT_CHARS", "120")),
            "max_ref_seconds": float(os.environ.get("VIDIOLINGUA_INDICF5_MAX_REF_SECONDS", "12")),
            "segment_id": request.segment_id,
        }

        tmp_root = PROJECT_ROOT / ".runtime_tmp" / "indicf5_requests"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="indicf5_", dir=tmp_root) as tmp_dir:
            request_json = Path(tmp_dir) / "request.json"
            response_json = Path(tmp_dir) / "response.json"
            request_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            cmd = [
                str(self._python_path()),
                str(worker),
                "--request",
                str(request_json),
                "--response",
                str(response_json),
            ]
            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._kill_worker(process.pid)
                stdout, stderr = process.communicate()
                timeout_response = {
                    "ok": False,
                    "engine": "indicf5",
                    "error": f"IndicF5 worker timed out after {timeout} seconds and was killed.",
                    "model_name": model_name,
                    "model_dir": model_dir,
                    "checkpoint_path": checkpoint_path,
                    "device": device,
                    "fallback_used": False,
                }
                response_json.write_text(json.dumps(timeout_response, ensure_ascii=False, indent=2), encoding="utf-8")
                raise VoiceSynthesisError(timeout_response["error"])

            completed = subprocess.CompletedProcess(
                [
                    *cmd,
                ],
                process.returncode,
                stdout,
                stderr,
            )

            response = {}
            if response_json.is_file():
                response = json.loads(response_json.read_text(encoding="utf-8"))
            if completed.returncode != 0 or not response.get("ok"):
                detail = response.get("error") or completed.stderr or completed.stdout or "unknown IndicF5 worker failure"
                raise VoiceSynthesisError(f"IndicF5 worker failed: {detail}")

        from voice.audio_validation import analyze_audio

        stats = analyze_audio(request.output_path)
        return VoiceSynthesisResult(
            engine=self.name,
            output_path=request.output_path,
            sample_rate=stats.sample_rate,
            duration_sec=stats.duration_s,
            used_reference_audio=True,
            used_reference_text=True,
            fallback_used=False,
            cache_hit=False,
            metadata={
                "model_name": response.get("model_name", model_name),
                "device": response.get("device", device),
                "segment_id": request.segment_id,
                "worker": str(worker),
            },
        )

    @staticmethod
    def _kill_worker(pid: int) -> None:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except Exception:
            pass
