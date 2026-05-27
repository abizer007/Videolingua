"""
VideoLingua Backend API - FastAPI app.
"""

import argparse
import json
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from backend import job_store
from app.routers.tts_router import router as tts_router

# Base directory for job workspaces (relative to project root when running uvicorn from root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
JOBS_DIR = Path(os.environ.get("JOBS_DIR", str(PROJECT_ROOT / "jobs")))
MULTILINGUAL_EXPORTS_DIR = PROJECT_ROOT / "outputs" / "multilingual_exports"
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

REFERENCE_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
    ".webm",
}
REFERENCE_AUDIO_CONTENT_TYPE_EXTENSIONS = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/webm": ".webm",
}

app = FastAPI(title="VideoLingua API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tts_router)

JOBS_DIR.mkdir(parents=True, exist_ok=True)
MULTILINGUAL_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


class MultilingualExportTrack(BaseModel):
    language: str
    audioPath: str


class MultilingualExportRequest(BaseModel):
    sourceVideo: str
    tracks: list[MultilingualExportTrack]
    exportId: str | None = None
    createHls: bool = True
    createMp4: bool = True


@app.get("/api/health")
def health():
    return {"status": "ok"}


def _json_no_cache(data: dict, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content=data, status_code=status_code, headers=NO_CACHE_HEADERS)


def _reference_audio_suffix(upload: UploadFile) -> str:
    filename_suffix = Path(upload.filename or "").suffix.lower()
    if filename_suffix in REFERENCE_AUDIO_EXTENSIONS:
        return filename_suffix
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    return REFERENCE_AUDIO_CONTENT_TYPE_EXTENSIONS.get(content_type, ".wav")


@app.get("/")
def root():
    return {"status": "ok"}


def _safe_project_path(raw_path: str, *, allowed_roots: list[Path], allowed_suffixes: set[str]) -> Path:
    if not raw_path or "\x00" in raw_path:
        raise HTTPException(400, "Invalid path")
    candidate = Path(raw_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (PROJECT_ROOT / candidate).resolve()
    suffix = resolved.suffix.lower()
    if allowed_suffixes and suffix not in allowed_suffixes:
        raise HTTPException(400, f"Unsupported file type: {suffix or 'none'}")
    resolved_roots = [root.resolve() for root in allowed_roots]
    if not any(resolved == root or str(resolved).startswith(str(root) + os.sep) for root in resolved_roots):
        raise HTTPException(400, "Path is outside allowed media roots")
    if not resolved.is_file():
        raise HTTPException(404, f"File not found: {raw_path}")
    return resolved


def _safe_export_id(value: str | None) -> str:
    export_id = (value or f"export_{uuid.uuid4().hex[:12]}").strip()
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if not export_id or any(char not in allowed for char in export_id) or export_id in {".", ".."}:
        raise HTTPException(400, "Invalid exportId")
    return export_id


@app.get("/api/health/deps")
def health_deps():
    """Check that required tools and packages are available for the pipeline."""
    out = {
        "ffmpeg": False,
        "ffprobe": False,
        "stage_pythons": {},
        "fastapi": True,
        "uvicorn": False,
        "deep_translator": False,
        "xtts_model_path": False,
        "musetalk": False,
        "gfpgan": False,
        "wav2lip": False,
        "wav2lip_preflight": {},
        "ready": False,
    }
    out["ffmpeg"] = bool(shutil.which("ffmpeg"))
    out["ffprobe"] = bool(shutil.which("ffprobe"))
    for key, default in {
        "VIDIOLINGUA_API_PYTHON": ".venv_api/Scripts/python.exe",
        "VIDIOLINGUA_ASR_PYTHON": ".venv_asr/Scripts/python.exe",
        "VIDIOLINGUA_TTS_PYTHON": ".venv_tts/Scripts/python.exe",
        "VIDIOLINGUA_BGM_PYTHON": ".venv_bgm/Scripts/python.exe",
        "VIDIOLINGUA_MUSETALK_PYTHON": ".venv_musetalk/Scripts/python.exe",
        "VIDIOLINGUA_GFP_GAN_PYTHON": ".venv_gfpgan/Scripts/python.exe",
    }.items():
        configured = os.environ.get(key, "").strip()
        candidate = Path(configured) if configured else PROJECT_ROOT / default
        out["stage_pythons"][key] = str(candidate)
    try:
        __import__("uvicorn")
        out["uvicorn"] = True
    except ImportError:
        pass
    try:
        __import__("deep_translator")
        out["deep_translator"] = True
    except ImportError:
        pass
    xtts_dir = os.environ.get("VIDIOLINGUA_XTTS_MODEL_PATH", "").strip()
    if xtts_dir:
        p = Path(xtts_dir)
        out["xtts_model_path"] = (
            (p / "config.json").is_file()
            and any(p.glob("*.pth"))
            and ((p / "vocab.json").is_file() or (p / "tokenizer.json").is_file())
        )
    musetalk_dir = os.environ.get("VIDIOLINGUA_MUSETALK_DIR", "").strip()
    if musetalk_dir:
        out["musetalk"] = Path(musetalk_dir).is_dir()
    gfpgan_dir = os.environ.get("VIDIOLINGUA_GFPGAN_DIR", "").strip()
    if gfpgan_dir:
        out["gfpgan"] = (Path(gfpgan_dir) / "inference_gfpgan.py").is_file()
    wav2lip_dir = os.environ.get("VIDIOLINGUA_WAV2LIP_DIR", "").strip()
    wav2lip_checkpoint = os.environ.get("VIDIOLINGUA_WAV2LIP_CHECKPOINT", "")
    if wav2lip_dir:
        wav2lip_path = Path(wav2lip_dir) / "inference.py"
        out["wav2lip"] = wav2lip_path.exists() and (not wav2lip_checkpoint or Path(wav2lip_checkpoint).exists())
    try:
        from tools.validate_wav2lip_runtime import build_preflight_report

        preflight = build_preflight_report(wav2lip_dir=wav2lip_dir or None, checkpoint=wav2lip_checkpoint or None)
        out["wav2lip_preflight"] = {
            "ok": bool(preflight.get("ok")),
            "selected_python": preflight.get("selected_python"),
            "checkpoint_exists": bool(preflight.get("checkpoint_exists")),
            "numpy_available": bool(preflight.get("numpy_available")),
            "torch_available": bool(preflight.get("torch_available")),
            "cv2_available": bool(preflight.get("cv2_available")),
            "cuda_available": bool(preflight.get("cuda_available")),
            "warnings": preflight.get("warnings") if isinstance(preflight.get("warnings"), list) else [],
            "errors": preflight.get("errors") if isinstance(preflight.get("errors"), list) else [],
        }
    except Exception as exc:
        out["wav2lip_preflight"] = {"ok": False, "errors": [str(exc)], "warnings": []}
    out["ready"] = out["ffmpeg"] and out["ffprobe"] and out["uvicorn"]
    return out


@app.post("/api/upload")
async def upload(
    video: UploadFile = File(...),
    languages: str = Form("[]"),
    targetLanguage: str = Form(""),
    voiceOptions: str = Form("{}"),
    sourceLanguage: str = Form(""),
    includeCaptions: bool = Form(False),
    autoReference: str = Form("false"),
    referenceMode: str = Form(""),
    voiceSample: UploadFile | None = File(None),
    ground_truth_transcript_file: UploadFile | None = File(None),
    ground_truth_transcript_text: str = Form(""),
    reference_translation_file: UploadFile | None = File(None),
    reference_translation_text: str = Form(""),
    human_mos_rating: str = Form(""),
    human_quality_notes: str = Form(""),
    responsibleAIConsent: str = Form("{}"),
):
    """Accept video upload, create job, save file, return jobId. Start pipeline in background."""
    import json
    from backend.pipeline_runner import run_pipeline_background

    # Validate video type
    if not video.filename or not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(400, "A video file is required")

    xtts_supported = {"ar", "cs", "de", "en", "es", "fr", "hu", "it", "ja", "ko", "nl", "pl", "pt", "ru", "tr", "zh"}
    sarvam_supported = {"hi", "ta", "bn", "te", "kn", "ml", "mr", "gu", "pa", "or", "od"}
    supported = xtts_supported | sarvam_supported
    code_map = {
        "Arabic": "ar",
        "Czech": "cs",
        "Dutch": "nl",
        "English": "en",
        "German": "de",
        "Hungarian": "hu",
        "Italian": "it",
        "Japanese": "ja",
        "Korean": "ko",
        "Polish": "pl",
        "Portuguese": "pt",
        "Russian": "ru",
        "Turkish": "tr",
        "Chinese": "zh",
        "Hindi": "hi",
        "Tamil": "ta",
        "Bengali": "bn",
        "Telugu": "te",
        "Kannada": "kn",
        "Malayalam": "ml",
        "Marathi": "mr",
        "Gujarati": "gu",
        "Punjabi": "pa",
        "Odia": "or",
        "Odia alias": "od",
        "Spanish": "es",
        "French": "fr",
        "ar": "ar",
        "cs": "cs",
        "en": "en",
        "hu": "hu",
        "it": "it",
        "ko": "ko",
        "nl": "nl",
        "pl": "pl",
        "ru": "ru",
        "tr": "tr",
        "ta": "ta",
        "bn": "bn",
        "te": "te",
        "kn": "kn",
        "ml": "ml",
        "mr": "mr",
        "gu": "gu",
        "pa": "pa",
        "or": "or",
        "od": "od",
        "hi": "hi",
        "es": "es",
        "fr": "fr",
        "de": "de",
        "ja": "ja",
        "zh": "zh",
        "pt": "pt",
    }

    def _normalize_language(raw: object) -> str | None:
        if not isinstance(raw, str):
            return None
        value = raw.strip()
        if not value:
            return None
        code = code_map.get(value, value.lower())
        return code if code in supported else None

    try:
        lang_list = json.loads(languages)
    except json.JSONDecodeError:
        lang_list = []
    if isinstance(lang_list, str):
        lang_list = [lang_list]
    if not isinstance(lang_list, list):
        lang_list = []

    lang_codes = [code for code in (_normalize_language(item) for item in lang_list) if code]
    target_language_code = _normalize_language(targetLanguage)
    if target_language_code and target_language_code not in lang_codes:
        lang_codes.append(target_language_code)
    if not lang_codes:
        lang_codes = ["fr"]

    # Parse voice options
    try:
        voice_opts = json.loads(voiceOptions)
    except json.JSONDecodeError:
        voice_opts = {}
    if not isinstance(voice_opts, dict):
        voice_opts = {}
    captions_requested = bool(includeCaptions)
    if not captions_requested:
        captions_requested = str(
            voice_opts.get("includeCaptions")
            or voice_opts.get("captionsRequested")
            or voice_opts.get("include_captions")
            or ""
        ).strip().lower() in {"1", "true", "yes", "on"}
    voice_opts["includeCaptions"] = captions_requested
    voice_opts["captionsRequested"] = captions_requested
    try:
        responsible_ai_consent = json.loads(responsibleAIConsent)
    except json.JSONDecodeError:
        responsible_ai_consent = {}
    if not isinstance(responsible_ai_consent, dict):
        responsible_ai_consent = {}
    voice_opts["responsibleAIConsent"] = responsible_ai_consent

    def _normalize_reference_mode(raw: object) -> str:
        value = str(raw or "").strip().lower().replace("-", "_")
        aliases = {
            "auto": "auto_extract",
            "auto_reference": "auto_extract",
            "auto_extracted": "auto_extract",
            "not_required": "none",
            "missing": "none",
            "": "",
        }
        return aliases.get(value, value if value in {"uploaded", "auto_extract", "none"} else "")

    requested_reference_mode = _normalize_reference_mode(
        voice_opts.get("referenceMode")
        or voice_opts.get("reference_mode")
        or referenceMode
    )
    auto_reference = requested_reference_mode == "auto_extract" or str(
        voice_opts.get("autoReference")
        or voice_opts.get("auto_reference")
        or autoReference
        or ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    if not requested_reference_mode:
        requested_reference_mode = "uploaded" if voiceSample is not None else "auto_extract" if auto_reference else "none"
    if voiceSample is not None:
        requested_reference_mode = "uploaded"
    elif requested_reference_mode == "uploaded":
        requested_reference_mode = "none"
    auto_reference = requested_reference_mode == "auto_extract"
    voice_opts["autoReference"] = auto_reference
    voice_opts["auto_reference"] = auto_reference
    voice_opts["referenceMode"] = requested_reference_mode
    voice_opts["reference_mode"] = requested_reference_mode

    source_lang = sourceLanguage.strip().lower()
    if source_lang == "auto" or not source_lang:
        source_lang = ""

    xtts_targets = {lang for lang in lang_codes if lang in xtts_supported}
    if xtts_targets and voiceSample is None and not auto_reference:
        raise HTTPException(
            400,
            "XTTS speaker-reference dubbing needs either a reference audio file or auto-extract from the uploaded video.",
        )

    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded video with a stable name (e.g. input.mp4)
    video_path = job_dir / "input_video.mp4"
    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)

    voice_sample_path = None
    if voiceSample is not None and voiceSample.filename:
        sample_path = job_dir / f"voice_sample{_reference_audio_suffix(voiceSample)}"
        with open(sample_path, "wb") as f:
            content = await voiceSample.read()
            f.write(content)
        voice_sample_path = str(sample_path)

    evaluation_dir = job_dir / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    if ground_truth_transcript_file is not None and ground_truth_transcript_file.filename:
        content = await ground_truth_transcript_file.read()
        (evaluation_dir / "ground_truth_transcript.txt").write_bytes(content)
    elif ground_truth_transcript_text.strip():
        (evaluation_dir / "ground_truth_transcript.txt").write_text(
            ground_truth_transcript_text.strip(),
            encoding="utf-8",
        )
    if reference_translation_file is not None and reference_translation_file.filename:
        content = await reference_translation_file.read()
        (evaluation_dir / "reference_translation.txt").write_bytes(content)
    elif reference_translation_text.strip():
        (evaluation_dir / "reference_translation.txt").write_text(
            reference_translation_text.strip(),
            encoding="utf-8",
        )
    quality_payload = {}
    if human_mos_rating.strip():
        try:
            rating = float(human_mos_rating.strip())
        except ValueError:
            raise HTTPException(400, "human_mos_rating must be numeric when provided")
        if rating < 1.0 or rating > 5.0:
            raise HTTPException(400, "human_mos_rating must be between 1 and 5")
        quality_payload["human_mos_rating"] = rating
    if human_quality_notes.strip():
        quality_payload["human_quality_notes"] = human_quality_notes.strip()
    if quality_payload:
        (evaluation_dir / "human_quality.json").write_text(
            json.dumps(quality_payload, indent=2),
            encoding="utf-8",
        )

    job_store.create_job(
        job_id,
        str(video_path),
        lang_codes,
        source_language=source_lang or None,
        voice_options=voice_opts,
        voice_sample_path=voice_sample_path,
        captions_requested=captions_requested,
        responsible_ai={
            "enabled": True,
            "mode": os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only"),
            "passportStatus": None,
            "message": "Compliance passport will appear for new runs.",
        },
    )
    run_pipeline_background(
        job_id,
        str(video_path),
        lang_codes,
        source_language=source_lang or None,
        voice_options=voice_opts,
        voice_sample_path=voice_sample_path,
        include_captions=captions_requested,
        run_source="api",
    )
    return _json_no_cache({"jobId": job_id})


@app.get("/api/job-status/{job_id}")
def job_status(job_id: str):
    """Return job status for polling."""
    data = job_store.get_job_status_response(job_id)
    if data is None:
        raise HTTPException(404, "Job not found", headers=NO_CACHE_HEADERS)
    return _json_no_cache(data)


@app.get("/api/result/{job_id}")
def result(job_id: str):
    """Return processing result when job is complete (or error)."""
    data = job_store.get_job_result_response(job_id)
    if data is None:
        # Job still running or not found
        job = job_store.get_job(job_id)
        if job is None:
            raise HTTPException(404, "Job not found", headers=NO_CACHE_HEADERS)
        raise HTTPException(202, "Job not complete", headers=NO_CACHE_HEADERS)
    return _json_no_cache(data)


@app.get("/api/result/{job_id}/file/{filename:path}")
def result_file(job_id: str, filename: str):
    """Serve result media or caption sidecars with path traversal safeguards."""
    normalized = (filename or "").replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if (
        not parts
        or "\x00" in filename
        or normalized.startswith("/")
        or any(part in {".", ".."} for part in parts)
    ):
        raise HTTPException(400, "Invalid filename", headers=NO_CACHE_HEADERS)
    job_dir = JOBS_DIR / job_id
    results_dir = job_dir / "results"
    captions_dir = job_dir / "captions"
    candidates: list[tuple[Path, Path]] = []
    if len(parts) == 1:
        candidates.extend([(results_dir, results_dir / parts[0]), (captions_dir, captions_dir / parts[0])])
    elif parts[0] == "captions":
        candidates.append((captions_dir, captions_dir.joinpath(*parts[1:])))
    else:
        raise HTTPException(400, "Invalid filename", headers=NO_CACHE_HEADERS)

    file_path = None
    for root, candidate in candidates:
        root_resolved = root.resolve()
        resolved = candidate.resolve()
        if resolved != root_resolved and str(resolved).startswith(str(root_resolved) + os.sep) and resolved.is_file():
            file_path = resolved
            break
    if file_path is None:
        raise HTTPException(404, "File not found", headers=NO_CACHE_HEADERS)
    media_types = {
        ".vtt": "text/vtt; charset=utf-8",
        ".srt": "application/x-subrip",
    }
    return FileResponse(
        file_path,
        filename=file_path.name,
        media_type=media_types.get(file_path.suffix.lower()),
        headers=NO_CACHE_HEADERS,
    )


@app.post("/api/multilingual-export")
def create_multilingual_export(payload: MultilingualExportRequest):
    """Package existing output audio tracks into a multilingual export folder."""
    if not payload.tracks:
        raise HTTPException(400, "At least one audio track is required")
    export_id = _safe_export_id(payload.exportId)
    source_video = _safe_project_path(
        payload.sourceVideo,
        allowed_roots=[PROJECT_ROOT, PROJECT_ROOT / "outputs", JOBS_DIR],
        allowed_suffixes={".mp4", ".mov", ".mkv", ".avi"},
    )
    track_args: list[str] = []
    seen_languages: set[str] = set()
    for track in payload.tracks:
        language = (track.language or "").strip().lower().replace("_", "-").split("-")[0]
        if not language:
            raise HTTPException(400, "Track language cannot be empty")
        if language in seen_languages:
            raise HTTPException(400, f"Duplicate language track: {language}")
        seen_languages.add(language)
        audio_path = _safe_project_path(
            track.audioPath,
            allowed_roots=[PROJECT_ROOT / "outputs", JOBS_DIR],
            allowed_suffixes={".wav", ".aac", ".m4a", ".mp3"},
        )
        track_args.append(f"{language}={audio_path}")

    from tools.create_multilingual_export import ExportError, create_export

    output_dir = MULTILINGUAL_EXPORTS_DIR / export_id
    args = argparse.Namespace(
        source_video=str(source_video),
        track=track_args,
        output_dir=str(output_dir),
        create_hls=payload.createHls,
        create_mp4=payload.createMp4,
    )
    try:
        result_data = create_export(args)
    except ExportError as exc:
        raise HTTPException(400, str(exc)) from exc
    manifest = result_data["manifest"]
    return {
        "exportId": export_id,
        "status": "created",
        "manifest": manifest,
        "links": {
            "manifest": f"/api/multilingual-export/{export_id}/file/metadata/multilingual_manifest.json",
            "validationReport": f"/api/multilingual-export/{export_id}/file/metadata/validation_report.json",
            "hlsMaster": f"/api/multilingual-export/{export_id}/file/{manifest.get('exports', {}).get('hls_master')}" if manifest.get("exports", {}).get("hls_master") else None,
            "multiAudioMp4": f"/api/multilingual-export/{export_id}/file/{manifest.get('exports', {}).get('multi_audio_mp4')}" if manifest.get("exports", {}).get("multi_audio_mp4") else None,
        },
    }


@app.get("/api/multilingual-export/{export_id}")
def get_multilingual_export(export_id: str):
    export_id = _safe_export_id(export_id)
    export_dir = (MULTILINGUAL_EXPORTS_DIR / export_id).resolve()
    manifest_path = export_dir / "metadata" / "multilingual_manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(404, "Multilingual export not found")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(500, f"Could not read export manifest: {exc}") from exc
    return {
        "exportId": export_id,
        "manifest": manifest,
        "links": {
            "manifest": f"/api/multilingual-export/{export_id}/file/metadata/multilingual_manifest.json",
            "validationReport": f"/api/multilingual-export/{export_id}/file/metadata/validation_report.json",
            "hlsMaster": f"/api/multilingual-export/{export_id}/file/{manifest.get('exports', {}).get('hls_master')}" if manifest.get("exports", {}).get("hls_master") else None,
            "multiAudioMp4": f"/api/multilingual-export/{export_id}/file/{manifest.get('exports', {}).get('multi_audio_mp4')}" if manifest.get("exports", {}).get("multi_audio_mp4") else None,
        },
    }


@app.get("/api/multilingual-export/{export_id}/file/{file_path:path}")
def multilingual_export_file(export_id: str, file_path: str):
    export_id = _safe_export_id(export_id)
    if not file_path or "\x00" in file_path:
        raise HTTPException(400, "Invalid file path")
    export_dir = (MULTILINGUAL_EXPORTS_DIR / export_id).resolve()
    requested = (export_dir / file_path).resolve()
    if requested != export_dir and not str(requested).startswith(str(export_dir) + os.sep):
        raise HTTPException(400, "Invalid file path")
    if not requested.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(requested, filename=requested.name)
