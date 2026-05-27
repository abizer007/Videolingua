"""IndicTrans2 engine adapter.

This adapter intentionally shells out to a worker so IndicTrans2 dependencies do
not collide with the known-good XTTS environment.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from translation.base import TranslationRequest, TranslationResult, TranslationError, indictrans2_supports_pair, normalize_language_code


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class IndicTrans2Engine:
    name = "indictrans2"
    model_name = os.environ.get("VIDIOLINGUA_INDICTRANS2_MODEL", "ai4bharat/indictrans2-en-indic-dist-200M")

    def _python(self) -> str:
        configured = os.environ.get("VIDIOLINGUA_INDICTRANS2_PYTHON", "").strip()
        if configured:
            return configured
        candidate = Path("D:/Vidiolingua/.venv_indictrans2/Scripts/python.exe")
        return str(candidate)

    def translate(self, request: TranslationRequest) -> TranslationResult:
        source = normalize_language_code(request.source_language)
        target = normalize_language_code(request.target_language)
        if not indictrans2_supports_pair(source, target):
            raise TranslationError(f"IndicTrans2 unsupported language pair: {source}->{target}")

        python_exe = Path(self._python())
        if not python_exe.is_file():
            raise TranslationError(
                "IndicTrans2 worker Python is not configured or does not exist. "
                "Set VIDIOLINGUA_INDICTRANS2_PYTHON after creating .venv_indictrans2."
            )

        timeout_s = int(
            os.environ.get("VIDIOLINGUA_INDICTRANS2_TIMEOUT_SEC")
            or os.environ.get("VIDIOLINGUA_INDICTRANS2_TIMEOUT_SECONDS")
            or "300"
        )
        job_id = os.environ.get("VIDIOLINGUA_JOB_ID", "").strip()
        job_dir_value = os.environ.get("VIDIOLINGUA_JOB_DIR", "").strip()
        if job_dir_value:
            temp_root = Path(job_dir_value) / "tmp" / "indictrans2_worker"
        elif job_id:
            temp_root = PROJECT_ROOT / "jobs" / job_id / "tmp" / "indictrans2_worker"
        else:
            temp_root = PROJECT_ROOT / "outputs" / "validation" / "indictrans2_worker_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        keep_tmp_on_failure = os.environ.get("VIDIOLINGUA_KEEP_WORKER_TMP_ON_FAILURE", "false").strip().lower() in {"1", "true", "yes", "on"}
        hf_home = Path(os.environ.get("HF_HOME", PROJECT_ROOT / ".hf_cache"))
        hf_modules_cache = Path(os.environ.get("HF_MODULES_CACHE", hf_home / "modules"))
        hf_home.mkdir(parents=True, exist_ok=True)
        hf_modules_cache.mkdir(parents=True, exist_ok=True)
        worker_env = os.environ.copy()
        worker_env.setdefault("HF_HOME", str(hf_home))
        worker_env.setdefault("HF_MODULES_CACHE", str(hf_modules_cache))
        worker_env.setdefault("TRANSFORMERS_CACHE", str(hf_home / "transformers"))
        tmp = Path(tempfile.mkdtemp(prefix="request_", dir=str(temp_root)))
        payload: dict = {}
        try:
            request_path = tmp / "request.json"
            response_path = tmp / "response.json"
            request_path.write_text(
                json.dumps(
                    {
                        "source_text": request.source_text,
                        "source_language": source,
                        "target_language": target,
                        "segment_id": request.segment_id,
                        "model_name": self.model_name,
                        "batch_size": int(os.environ.get("VIDIOLINGUA_INDICTRANS2_BATCH_SIZE", "1")),
                        "device": os.environ.get("VIDIOLINGUA_INDICTRANS2_DEVICE", "auto"),
                        "attention": os.environ.get("VIDIOLINGUA_INDICTRANS2_ATTENTION", "default"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            cmd = [
                str(python_exe),
                "-m",
                "workers.indictrans2_worker",
                "--request",
                str(request_path),
                "--response",
                str(response_path),
            ]
            started = time.time()
            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=worker_env,
            )
            killed = False
            try:
                stdout, stderr = process.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                process.terminate()
                killed = True
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate(timeout=5)
                response_exists = response_path.is_file()
                detail = self._timeout_detail(
                    timeout_s=timeout_s,
                    cmd=cmd,
                    request_path=request_path,
                    response_path=response_path,
                    response_exists=response_exists,
                    killed=killed,
                    stdout=stdout,
                    stderr=stderr,
                    elapsed=time.time() - started,
                )
                self._preserve_or_clean_worker_tmp(tmp, job_dir_value, keep_tmp_on_failure, failed=True)
                raise TranslationError(detail)
            if process.returncode != 0:
                detail = stderr or stdout or f"exit code {process.returncode}"
                response_detail = ""
                if response_path.is_file():
                    try:
                        response_detail = json.loads(response_path.read_text(encoding="utf-8")).get("error") or ""
                    except Exception:
                        response_detail = response_path.read_text(encoding="utf-8", errors="replace")[:1000]
                self._preserve_or_clean_worker_tmp(tmp, job_dir_value, keep_tmp_on_failure, failed=True)
                raise TranslationError(
                    "IndicTrans2 worker failed: "
                    f"{(response_detail or detail).strip()}\n"
                    f"worker_command={' '.join(cmd)}\n"
                    f"request_path={request_path}\n"
                    f"response_path={response_path}\n"
                    f"stdout_tail={self._tail(stdout)}\n"
                    f"stderr_tail={self._tail(stderr)}"
                )
            if not response_path.is_file():
                self._preserve_or_clean_worker_tmp(tmp, job_dir_value, keep_tmp_on_failure, failed=True)
                raise TranslationError("IndicTrans2 worker produced no response JSON")
            payload = json.loads(response_path.read_text(encoding="utf-8"))
            self._preserve_or_clean_worker_tmp(tmp, job_dir_value, keep_tmp_on_failure, failed=False)
        except Exception:
            if tmp.exists():
                self._preserve_or_clean_worker_tmp(tmp, job_dir_value, keep_tmp_on_failure, failed=True)
            raise
        translated = (payload.get("translated_text") or "").strip()
        if not translated:
            raise TranslationError("IndicTrans2 worker returned empty translation")
        return TranslationResult(
            engine=self.name,
            source_language=source,
            target_language=target,
            source_text=request.source_text,
            translated_text=translated,
            used_indictrans2=True,
            used_llm=False,
            used_deep_translator=False,
            fallback_used=False,
            metadata={
                "model_name": payload.get("model_name", self.model_name),
                "model_path": payload.get("model_path"),
                "source_flores_code": payload.get("source_flores_code"),
                "target_flores_code": payload.get("target_flores_code"),
                "device": payload.get("device"),
                "dtype": payload.get("dtype"),
                "batch_size": payload.get("batch_size"),
                "worker": str(python_exe),
                "segment_id": request.segment_id,
            },
        )

    @staticmethod
    def _tail(value: str | None, limit: int = 1200) -> str:
        text = value or ""
        return text[-limit:]

    def _timeout_detail(
        self,
        *,
        timeout_s: int,
        cmd: list[str],
        request_path: Path,
        response_path: Path,
        response_exists: bool,
        killed: bool,
        stdout: str | None,
        stderr: str | None,
        elapsed: float,
    ) -> str:
        return (
            "IndicTrans2 worker timed out during translation. "
            f"stage=translation; engine=IndicTrans2; timeout_sec={timeout_s}; "
            f"elapsed_sec={elapsed:.1f}; worker_command={' '.join(cmd)}; "
            f"request_path={request_path}; response_path={response_path}; "
            f"process_killed={killed}; response_json_existed={response_exists}; "
            f"stdout_tail={self._tail(stdout)!r}; stderr_tail={self._tail(stderr)!r}; "
            "suggested_next_action=retry a fresh run after checking worker runtime/model load health."
        )

    def _preserve_or_clean_worker_tmp(self, tmp: Path, job_dir_value: str, keep_tmp_on_failure: bool, *, failed: bool) -> None:
        if failed and keep_tmp_on_failure:
            return
        if failed and job_dir_value:
            error_dir = Path(job_dir_value) / "errors" / "indictrans2_worker"
            error_dir.mkdir(parents=True, exist_ok=True)
            for name in ("request.json", "response.json"):
                source = tmp / name
                if source.is_file():
                    try:
                        shutil.copy2(source, error_dir / name)
                    except OSError:
                        pass
        shutil.rmtree(tmp, ignore_errors=True)
