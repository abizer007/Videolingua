"""Sarvam AI managed Indian-language TTS engine."""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from voice.base import (
    VoiceSynthesisError,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
    sarvam_supports_language,
    sarvam_target_language_code,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "backend" / ".env")
except Exception:
    pass


def mask_secret(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "<missing>"
    if len(value) <= 7:
        return "****"
    return f"{value[:3]}****{value[-4:]}"


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


class SarvamEngine:
    name = "sarvam"
    provider = "sarvam"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        speaker: str | None = None,
        pace: float | None = None,
        temperature: float | None = None,
        sample_rate: int | None = None,
        output_codec: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.api_key = (api_key or os.environ.get("SARVAM_API_KEY", "")).strip()
        self.model = model or os.environ.get("VIDIOLINGUA_SARVAM_MODEL", "bulbul:v3").strip() or "bulbul:v3"
        self.speaker = speaker or os.environ.get("VIDIOLINGUA_SARVAM_SPEAKER", "shubh").strip() or "shubh"
        self.pace = pace if pace is not None else _env_float("VIDIOLINGUA_SARVAM_PACE", 1.0)
        self.temperature = (
            temperature
            if temperature is not None
            else _env_float("VIDIOLINGUA_SARVAM_TEMPERATURE", 0.45)
        )
        self.sample_rate = (
            sample_rate
            if sample_rate is not None
            else _env_int("VIDIOLINGUA_SARVAM_SAMPLE_RATE", 24000)
        )
        self.output_codec = (
            output_codec
            or os.environ.get("VIDIOLINGUA_SARVAM_OUTPUT_CODEC", "wav").strip()
            or "wav"
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else _env_int("VIDIOLINGUA_SARVAM_TIMEOUT_SECONDS", 120)
        )

    def request_config(self, language: str, text: str) -> dict:
        if not sarvam_supports_language(language):
            raise VoiceSynthesisError(f"Sarvam does not support language '{language}'")
        return {
            "text": text,
            "target_language_code": sarvam_target_language_code(language),
            "speaker": self.speaker,
            "model": self.model,
            "pace": self.pace,
            "temperature": self.temperature,
            "speech_sample_rate": self.sample_rate,
            "output_audio_codec": self.output_codec,
        }

    def synthesize(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        if not self.api_key:
            raise VoiceSynthesisError("SARVAM_API_KEY is required for Sarvam TTS")
        if not request.text.strip():
            raise VoiceSynthesisError("Sarvam TTS requires non-empty text")

        payload = self.request_config(request.target_language, request.text)
        response_payload = self._post(payload)
        audios = response_payload.get("audios")
        if not isinstance(audios, list) or not audios:
            raise VoiceSynthesisError("Sarvam TTS response did not include any audio")
        try:
            wav_bytes = base64.b64decode(str(audios[0]), validate=True)
        except Exception as exc:
            raise VoiceSynthesisError("Sarvam TTS returned invalid base64 WAV audio") from exc
        if not wav_bytes:
            raise VoiceSynthesisError("Sarvam TTS returned empty WAV audio")

        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path, clean_path, cleanup_metadata = self._write_clean_wav(
            wav_bytes,
            request.output_path,
        )

        from voice.audio_validation import analyze_audio, validate_generated_audio

        validate_generated_audio(request.output_path)
        stats = analyze_audio(request.output_path)
        return VoiceSynthesisResult(
            engine=self.name,
            output_path=request.output_path,
            sample_rate=stats.sample_rate,
            duration_sec=stats.duration_s,
            used_reference_audio=False,
            used_reference_text=False,
            fallback_used=False,
            cache_hit=False,
            metadata={
                "provider": self.provider,
                "model": self.model,
                "speaker": self.speaker,
                "pace": self.pace,
                "temperature": self.temperature,
                "target_language_code": payload["target_language_code"],
                "request_id": response_payload.get("request_id"),
                "sample_rate": stats.sample_rate,
                "managed_tts": True,
                "exact_voice_clone": False,
                "speaker_preservation": "not_supported",
                "raw_audio_path": str(raw_path),
                "clean_audio_path": str(clean_path),
                **cleanup_metadata,
            },
        )

    def _write_clean_wav(self, wav_bytes: bytes, output_path: Path) -> tuple[Path, Path, dict]:
        from voice.audio_validation import (
            AudioValidationError,
            analyze_audio,
            normalize_pcm16_wav_peak,
        )

        raw_path = output_path.with_name(f"{output_path.stem}.sarvam_raw{output_path.suffix}")
        clean_path = output_path.with_name(f"{output_path.stem}.sarvam_clean{output_path.suffix}")
        raw_path.write_bytes(wav_bytes)

        raw_stats = analyze_audio(raw_path)
        self._validate_raw_basics(raw_stats)

        target_peak = _env_float("VIDIOLINGUA_SARVAM_TARGET_PEAK", 0.95)
        normalize_threshold = _env_float("VIDIOLINGUA_SARVAM_NORMALIZE_PEAK_THRESHOLD", 0.98)
        max_raw_clipping = _env_float("VIDIOLINGUA_SARVAM_MAX_RAW_CLIPPING_RATIO", 0.001)
        normalized = raw_stats.peak >= normalize_threshold

        if raw_stats.clipping_ratio > max_raw_clipping:
            raise AudioValidationError(
                "Sarvam raw audio appears heavily clipped "
                f"(peak={raw_stats.peak:.3f}, clipped={raw_stats.clipping_ratio:.3%})"
            )

        if normalized:
            warning = (
                "Sarvam raw audio near full scale; applying safe peak normalization "
                f"(peak={raw_stats.peak:.3f}, target_peak={target_peak:.2f})"
            )
            logger.warning(warning)
            print(f"[Sarvam] WARNING: {warning}")
            clean_stats = normalize_pcm16_wav_peak(raw_path, clean_path, target_peak=target_peak)
        else:
            shutil.copyfile(raw_path, clean_path)
            clean_stats = analyze_audio(clean_path)

        shutil.copyfile(clean_path, output_path)
        return raw_path, clean_path, {
            "raw_peak": raw_stats.peak,
            "raw_rms": raw_stats.rms,
            "raw_clipping_ratio": raw_stats.clipping_ratio,
            "raw_duration_sec": raw_stats.duration_s,
            "raw_sample_rate": raw_stats.sample_rate,
            "peak_normalized": normalized,
            "target_peak": target_peak,
            "clean_peak": clean_stats.peak,
            "clean_rms": clean_stats.rms,
            "clean_clipping_ratio": clean_stats.clipping_ratio,
        }

    @staticmethod
    def _validate_raw_basics(stats) -> None:
        errors: list[str] = []
        if stats.duration_s < 0.2:
            errors.append(f"duration {stats.duration_s:.2f}s is below required 0.20s")
        if stats.sample_rate < 16000:
            errors.append(f"sample rate {stats.sample_rate} Hz is too low")
        if stats.peak <= 0.005 or stats.rms <= 0.001:
            errors.append("raw audio is empty or nearly silent")
        if stats.silence_ratio > 0.85:
            errors.append(f"raw audio is mostly silence ({stats.silence_ratio:.1%} silent frames)")
        if stats.dropout_ratio > 0.90:
            errors.append(f"raw audio has excessive dropouts ({stats.dropout_ratio:.1%} near-zero frames)")
        if errors:
            raise VoiceSynthesisError(
                f"Sarvam raw audio failed basic validation '{stats.path}': " + "; ".join(errors)
            )

    def _post(self, payload: dict) -> dict:
        try:
            import requests

            response = requests.post(
                SARVAM_TTS_URL,
                headers={
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 300:
                raise VoiceSynthesisError(
                    "Sarvam TTS API failed: "
                    f"status={response.status_code} body={self._sanitize(response.text)[:500]}"
                )
            return response.json()
        except ImportError:
            return self._post_urllib(payload)
        except ValueError as exc:
            raise VoiceSynthesisError("Sarvam TTS API returned invalid JSON") from exc

    def _post_urllib(self, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(
            SARVAM_TTS_URL,
            data=body,
            method="POST",
            headers={
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise VoiceSynthesisError(
                "Sarvam TTS API failed: "
                f"status={exc.code} body={self._sanitize(raw)[:500]}"
            ) from exc
        except URLError as exc:
            raise VoiceSynthesisError(f"Sarvam TTS API request failed: {exc}") from exc
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise VoiceSynthesisError("Sarvam TTS API returned invalid JSON") from exc

    def _sanitize(self, value: str) -> str:
        sanitized = value or ""
        if self.api_key:
            sanitized = sanitized.replace(self.api_key, mask_secret(self.api_key))
        return sanitized
