"""Inspect VideoLingua pipeline policy without loading heavy models."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from translation.base import SUPPORTED_INDICTRANS2_LANGS
from voice.base import INDICF5_SUPPORTED_LANGS, SARVAM_SUPPORTED_LANGS, XTTS_SUPPORTED_LANGS


PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "backend" / ".env")
except Exception:
    pass


def _python_path(env_name: str, default: str) -> str:
    return os.environ.get(env_name, str(PROJECT_ROOT / default)).strip()


def _path_exists(path: str) -> bool:
    return bool(path) and Path(path).is_file()


def _mask_secret(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "<missing>"
    if len(value) <= 7:
        return "****"
    return f"{value[:3]}****{value[-4:]}"


def main() -> int:
    xtts_dir = Path(os.environ.get("VIDIOLINGUA_XTTS_MODEL_PATH", PROJECT_ROOT / "models" / "xtts_v2"))
    sarvam_key = os.environ.get("SARVAM_API_KEY", "").strip()
    report = {
        "translation_policy": {
            "engine": os.environ.get("VIDIOLINGUA_TRANSLATION_ENGINE", "auto"),
            "auto_engine_for_supported_indic_pairs": "indictrans2",
            "explicit_google_engine_honored": True,
            "linguistic_integrity_enabled": os.environ.get("VIDIOLINGUA_ENABLE_LINGUISTIC_INTEGRITY", "true"),
            "fail_on_linguistic_errors": os.environ.get("VIDIOLINGUA_FAIL_ON_LINGUISTIC_ERRORS", "true"),
            "indictrans2_enabled": os.environ.get("VIDIOLINGUA_INDICTRANS2_ENABLED", "true"),
            "allow_llm_fallback": os.environ.get("VIDIOLINGUA_ALLOW_LLM_TRANSLATION_FALLBACK", "false"),
            "allow_deep_translator_fallback": os.environ.get("VIDIOLINGUA_ALLOW_DEEP_TRANSLATOR_FALLBACK", "false"),
            "allow_llm_post_edit": os.environ.get("VIDIOLINGUA_ALLOW_LLM_POST_EDIT", "false"),
            "supported_indictrans2_languages": sorted(SUPPORTED_INDICTRANS2_LANGS),
        },
        "voice_policy": {
            "engine": os.environ.get("VIDIOLINGUA_TTS_ENGINE", "auto"),
            "prosody_engine_enabled": os.environ.get("VIDIOLINGUA_ENABLE_PROSODY_ENGINE", "true"),
            "prosody_preset": os.environ.get("VIDIOLINGUA_PROSODY_PRESET", "balanced"),
            "hubert_prosody_enabled": os.environ.get("VIDIOLINGUA_ENABLE_HUBERT_PROSODY", "false"),
            "hubert_timeout_sec": os.environ.get("VIDIOLINGUA_HUBERT_TIMEOUT_SEC", "90"),
            "hubert_required_for_prosody_validation": os.environ.get("VIDIOLINGUA_HUBERT_REQUIRED_FOR_PROSODY_VALIDATION", "true"),
            "hubert_fails_main_pipeline": os.environ.get("VIDIOLINGUA_HUBERT_FAILS_MAIN_PIPELINE", "false"),
            "prosody_fail_on_error": os.environ.get("VIDIOLINGUA_PROSODY_FAIL_ON_ERROR", "false"),
            "indictrans2_timeout_sec": os.environ.get("VIDIOLINGUA_INDICTRANS2_TIMEOUT_SEC", os.environ.get("VIDIOLINGUA_INDICTRANS2_TIMEOUT_SECONDS", "300")),
            "phonetic_resolution_enabled": os.environ.get("VIDIOLINGUA_ENABLE_PHONETIC_RESOLUTION", "true"),
            "use_tts_prepared_text": os.environ.get("VIDIOLINGUA_USE_TTS_PREPARED_TEXT", "true"),
            "pronunciation_dictionary": os.environ.get("VIDIOLINGUA_PRONUNCIATION_DICTIONARY", "config/pronunciation_dictionary.json"),
            "voice_engine": os.environ.get("VIDIOLINGUA_VOICE_ENGINE", "auto"),
            "cloning_required_default": True,
            "allow_generic_fallback": os.environ.get("ALLOW_GENERIC_TTS_FALLBACK", "false"),
            "allow_xtts_to_indicf5_fallback": os.environ.get("VIDIOLINGUA_ALLOW_XTTS_TO_INDICF5_FALLBACK", "true"),
            "indic_voice_backend": os.environ.get("VIDIOLINGUA_INDIC_VOICE_BACKEND", "sarvam"),
            "sarvam_enabled": os.environ.get("VIDIOLINGUA_ENABLE_SARVAM", "true" if sarvam_key else "false"),
            "sarvam_api_key_configured": bool(sarvam_key),
            "sarvam_api_key_masked": _mask_secret(sarvam_key),
            "sarvam_model": os.environ.get("VIDIOLINGUA_SARVAM_MODEL", "bulbul:v3"),
            "sarvam_speaker": os.environ.get("VIDIOLINGUA_SARVAM_SPEAKER", "shubh"),
            "sarvam_managed_tts": True,
            "sarvam_exact_voice_clone": False,
            "indicf5_enabled": os.environ.get("VIDIOLINGUA_ENABLE_INDICF5", os.environ.get("VIDIOLINGUA_INDICF5_ENABLED", "false")),
            "indicf5_execution_mode": os.environ.get("VIDIOLINGUA_INDICF5_EXECUTION_MODE", "local_disabled"),
            "reference_text_configured": bool(
                os.environ.get("VIDIOLINGUA_REFERENCE_TEXT", "").strip()
                or os.environ.get("VIDIOLINGUA_REFERENCE_TEXT_PATH", "").strip()
            ),
            "xtts_languages": sorted(XTTS_SUPPORTED_LANGS),
            "sarvam_languages": sorted(SARVAM_SUPPORTED_LANGS),
            "indicf5_languages": sorted(INDICF5_SUPPORTED_LANGS),
            "indic_parler": "disabled_absent_forbidden",
        },
        "speaker_analysis_policy": {
            "enabled": os.environ.get("VIDIOLINGUA_ENABLE_SPEAKER_DIARIZATION", "true"),
            "backend": os.environ.get("VIDIOLINGUA_DIARIZATION_BACKEND", "pyannote"),
            "pyannote_model": os.environ.get("VIDIOLINGUA_PYANNOTE_MODEL", "pyannote/speaker-diarization-community-1"),
            "pyannote_token_configured": bool(
                os.environ.get("VIDIOLINGUA_PYANNOTE_TOKEN", "").strip()
                or os.environ.get("HUGGINGFACE_TOKEN", "").strip()
                or os.environ.get("HF_TOKEN", "").strip()
                or os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
            ),
            "pyannote_device": os.environ.get("VIDIOLINGUA_PYANNOTE_DEVICE", "auto"),
            "fail_on_diarization_error": os.environ.get("VIDIOLINGUA_FAIL_ON_DIARIZATION_ERROR", "false"),
            "auto_extract_speaker_references": os.environ.get("VIDIOLINGUA_AUTO_EXTRACT_SPEAKER_REFERENCES", "true"),
            "auto_use_extracted_references_for_xtts": os.environ.get("VIDIOLINGUA_AUTO_USE_EXTRACTED_REFERENCES_FOR_XTTS", "false"),
            "sarvam_voice_profile_config": os.environ.get("VIDIOLINGUA_SARVAM_VOICE_PROFILE_CONFIG", "config/sarvam_voice_profiles.example.json"),
        },
        "worker_paths": {
            "api_python": _python_path("VIDIOLINGUA_API_PYTHON", ".venv_api/Scripts/python.exe"),
            "asr_python": _python_path("VIDIOLINGUA_ASR_PYTHON", ".venv_asr/Scripts/python.exe"),
            "xtts_python": _python_path("VIDIOLINGUA_TTS_PYTHON", ".venv_tts/Scripts/python.exe"),
            "indicf5_python": _python_path("VIDIOLINGUA_INDICF5_PYTHON", ".venv_indicf5/Scripts/python.exe"),
            "indictrans2_python": _python_path("VIDIOLINGUA_INDICTRANS2_PYTHON", ".venv_indictrans2/Scripts/python.exe"),
            "prosody_python": _python_path("VIDIOLINGUA_PROSODY_PYTHON", ".venv_prosody/Scripts/python.exe"),
            "bgm_python": _python_path("VIDIOLINGUA_BGM_PYTHON", ".venv_bgm/Scripts/python.exe"),
        },
        "responsible_ai_policy": {
            "enabled": os.environ.get("VIDIOLINGUA_ENABLE_RESPONSIBLE_AI", "true"),
            "mode": os.environ.get("VIDIOLINGUA_COMPLIANCE_MODE", "report_only"),
            "require_speaker_consent": os.environ.get("VIDIOLINGUA_REQUIRE_SPEAKER_CONSENT", "false"),
            "apply_visible_disclosure": os.environ.get("VIDIOLINGUA_APPLY_VISIBLE_DISCLOSURE", "false"),
            "apply_audio_disclosure": os.environ.get("VIDIOLINGUA_APPLY_AUDIO_DISCLOSURE", "false"),
            "embed_provenance_metadata": os.environ.get("VIDIOLINGUA_EMBED_PROVENANCE_METADATA", "true"),
            "generate_compliance_passport": os.environ.get("VIDIOLINGUA_GENERATE_COMPLIANCE_PASSPORT", "true"),
            "block_high_risk_sgi": os.environ.get("VIDIOLINGUA_BLOCK_HIGH_RISK_SGI", "false"),
            "retention_days": os.environ.get("VIDIOLINGUA_RETENTION_DAYS", "30"),
        },
        "artifacts": {
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "ffprobe": bool(shutil.which("ffprobe")),
            "xtts_model_dir": str(xtts_dir),
            "xtts_model_ready": (
                xtts_dir.is_dir()
                and (xtts_dir / "config.json").is_file()
                and (xtts_dir / "model.pth").is_file()
                and ((xtts_dir / "vocab.json").is_file() or (xtts_dir / "tokenizer.json").is_file())
            ),
        },
    }
    report["worker_path_exists"] = {key: _path_exists(value) for key, value in report["worker_paths"].items()}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
