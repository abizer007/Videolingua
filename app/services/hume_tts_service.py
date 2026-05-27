"""
Hume AI TTS service integration.

Uses the Hume REST API to synthesize speech and write WAV output.
Supports cloned voice via generate_speech() and synthesize_to_wav().
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import requests

HUME_TTS_URL = "https://api.hume.ai/v0/tts/file"
DEFAULT_TIMEOUT_S = 120
MIN_WAV_SIZE_BYTES = 5 * 1024  # 5KB

# Cloned voice ID (override via HUME_VOICE_ID env)
DEFAULT_CLONED_VOICE_ID = "ae7c30d2-94fd-485b-aedf-45b1647549e8"

logger = logging.getLogger(__name__)

_EMOTION_DESCRIPTIONS = {
    "happy": "Bright, cheerful tone.",
    "sad": "Somber, gentle tone.",
    "excited": "Energetic, enthusiastic delivery.",
    "calm": "Calm, relaxed delivery.",
    "angry": "Firm, intense delivery.",
    "neutral": "",
}


def _default_output_path() -> Path:
    """Default path for output.wav: project_root/tts/output/output.wav."""
    project_root = Path(__file__).resolve().parent.parent.parent
    return (project_root / "tts" / "output" / "output.wav").resolve()


def is_configured() -> bool:
    return bool(os.environ.get("HUME_API_KEY", "").strip())


def _build_description(voice_options: Optional[dict]) -> Optional[str]:
    if not voice_options:
        return None
    emotion = (voice_options.get("emotion") or "").strip().lower()
    if not emotion or emotion == "neutral":
        return None
    return _EMOTION_DESCRIPTIONS.get(emotion, f"Speak with a {emotion} tone.")


def _build_request_payload(
    text: str,
    voice_id: str = DEFAULT_CLONED_VOICE_ID,
    description_override: Optional[str] = None,
) -> dict:
    """Build request body. Hume API expects utterances array and format object."""
    desc = description_override or "Natural conversational tone."
    return {
        "utterances": [
            {
                "text": text,
                "voice": {
                    "id": voice_id,
                    "provider": "CUSTOM_VOICE",
                },
                "description": desc,
                "speed": 1.0,
            }
        ],
        "format": {"type": "wav"},
    }


def _headers_bearer(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/octet-stream",
    }


def _headers_x_hume_key(api_key: str) -> dict:
    return {
        "X-Hume-Api-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/octet-stream",
    }


def _do_sync_request(api_key: str, payload: dict) -> requests.Response:
    """POST to Hume TTS; try Bearer first, on 401/403 retry with X-Hume-Api-Key."""
    logger.debug("Hume TTS request payload (no API key): %s", payload)
    headers = _headers_bearer(api_key)
    try:
        resp = requests.post(
            HUME_TTS_URL,
            json=payload,
            headers=headers,
            timeout=DEFAULT_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        logger.error("Hume TTS request failed: %s", exc)
        raise RuntimeError(f"Hume TTS request failed: {exc}") from exc

    logger.debug("Hume TTS response status: %s", resp.status_code)
    logger.debug("Hume TTS response headers: %s", dict(resp.headers))

    if resp.status_code in (401, 403):
        logger.debug("Hume TTS got %s, retrying with X-Hume-Api-Key", resp.status_code)
        headers = _headers_x_hume_key(api_key)
        try:
            resp = requests.post(
                HUME_TTS_URL,
                json=payload,
                headers=headers,
                timeout=DEFAULT_TIMEOUT_S,
            )
        except requests.RequestException as exc:
            logger.error("Hume TTS retry request failed: %s", exc)
            raise RuntimeError(f"Hume TTS request failed: {exc}") from exc
        logger.debug("Hume TTS retry response status: %s", resp.status_code)
        logger.debug("Hume TTS retry response headers: %s", dict(resp.headers))

    return resp


def _handle_response_and_save(
    resp: requests.Response,
    path: Path,
    *,
    is_path_str: bool = False,
) -> str | Path:
    """Decode body, validate, save raw bytes, validate file size. Return path (str or Path)."""
    if resp.status_code != 200:
        try:
            body = resp.text
        except Exception:
            body = resp.content.decode(errors="replace")
        logger.error("Hume TTS failed status=%s body=%s", resp.status_code, body)
        raise RuntimeError(
            f"Hume TTS failed (status={resp.status_code}): {body}"
        )

    content = resp.content
    content_type = (resp.headers.get("Content-Type") or "").lower()

    if content_type and "application/json" in content_type:
        try:
            import json as _json
            decoded = _json.loads(content.decode("utf-8"))
            logger.debug("Hume TTS returned JSON (unexpected for file endpoint): %s", type(decoded))
            # If API returns JSON with base64 audio, decode and save
            if isinstance(decoded, dict) and "audio" in decoded:
                import base64
                content = base64.b64decode(decoded["audio"])
            else:
                raise RuntimeError(
                    f"Hume TTS failed (status=200 but JSON response): {resp.text[:500]}"
                )
        except (ValueError, TypeError) as e:
            raise RuntimeError(
                f"Hume TTS failed (status=200 but invalid JSON): {e}"
            ) from e
    else:
        if len(content) == 0:
            raise RuntimeError("Hume TTS returned empty body (status=200)")

    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    size = path.stat().st_size
    logger.debug("Hume TTS saved file size: %s bytes", size)

    if size < MIN_WAV_SIZE_BYTES:
        raise RuntimeError(
            f"Hume TTS output too small ({size} bytes < {MIN_WAV_SIZE_BYTES} bytes), invalid audio?"
        )

    return str(path) if is_path_str else path


def generate_speech(text: str, output_path: Optional[Path] = None) -> str:
    """
    Generate speech from text using Hume AI TTS with cloned voice.
    Saves WAV and returns its absolute path. Validates file size > 5KB.
    """
    api_key = os.environ.get("HUME_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("HUME_API_KEY is not set")

    path = output_path if output_path is not None else _default_output_path()
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    if not text or not text.strip():
        path.write_bytes(b"")
        logger.debug("Hume TTS skipped (empty text), saved 0 bytes")
        return str(path)

    voice_id = os.environ.get("HUME_VOICE_ID", "").strip() or DEFAULT_CLONED_VOICE_ID
    payload = _build_request_payload(text, voice_id=voice_id)
    resp = _do_sync_request(api_key, payload)
    return _handle_response_and_save(resp, path, is_path_str=True)


async def generate_speech_async(text: str, output_path: Optional[Path] = None) -> str:
    """Async version: uses httpx if available, else asyncio.to_thread(sync)."""
    try:
        import httpx
    except ImportError:
        return await asyncio.to_thread(
            generate_speech, text, output_path
        )

    api_key = os.environ.get("HUME_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("HUME_API_KEY is not set")

    path = output_path if output_path is not None else _default_output_path()
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    if not text or not text.strip():
        path.write_bytes(b"")
        return str(path)

    voice_id = os.environ.get("HUME_VOICE_ID", "").strip() or DEFAULT_CLONED_VOICE_ID
    payload = _build_request_payload(text, voice_id=voice_id)
    logger.debug("Hume TTS request payload (no API key): %s", payload)

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
        headers = _headers_bearer(api_key)
        resp = await client.post(
            HUME_TTS_URL,
            json=payload,
            headers=headers,
        )
        logger.debug("Hume TTS response status: %s", resp.status_code)
        logger.debug("Hume TTS response headers: %s", dict(resp.headers))

        if resp.status_code in (401, 403):
            logger.debug("Hume TTS got %s, retrying with X-Hume-Api-Key", resp.status_code)
            headers = _headers_x_hume_key(api_key)
            resp = await client.post(
                HUME_TTS_URL,
                json=payload,
                headers=headers,
            )
            logger.debug("Hume TTS retry response status: %s", resp.status_code)
            logger.debug("Hume TTS retry response headers: %s", dict(resp.headers))

    # Build a minimal response-like object for _handle_response_and_save
    class _AsyncResp:
        status_code = resp.status_code
        content = resp.content
        headers = resp.headers
        text = resp.text

    return _handle_response_and_save(_AsyncResp(), path, is_path_str=True)


def synthesize_to_wav(
    text: str,
    output_path: Path,
    voice_options: Optional[dict] = None,
    voice_id: Optional[str] = None,
) -> Path:
    """
    Synthesize text to WAV at the given path using Hume TTS (cloned voice).
    Same auth retry, payload, validation and logging as generate_speech.
    """
    api_key = os.environ.get("HUME_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("HUME_API_KEY is not set")

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not text or not text.strip():
        output_path.write_bytes(b"")
        return output_path

    vid = voice_id or os.environ.get("HUME_VOICE_ID", "").strip() or DEFAULT_CLONED_VOICE_ID
    description_override = _build_description(voice_options)
    payload = _build_request_payload(
        text,
        voice_id=vid,
        description_override=description_override or "Natural conversational tone.",
    )
    resp = _do_sync_request(api_key, payload)
    return _handle_response_and_save(resp, output_path, is_path_str=False)
