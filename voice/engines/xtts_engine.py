"""XTTS voice engine adapter."""

from __future__ import annotations

import os

from voice.base import VoiceSynthesisRequest, VoiceSynthesisResult, normalize_voice_language


class XTTSEngine:
    name = "xtts"
    model_name = "tts_models/multilingual/multi-dataset/xtts_v2"

    def synthesize(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        from app.services.xtts_tts_service import synthesize_to_wav

        synthesize_to_wav(
            text=request.text,
            output_path=request.output_path,
            speaker_wav=str(request.reference_audio_path) if request.reference_audio_path else None,
            language_code=normalize_voice_language(request.target_language),
        )
        from voice.audio_validation import analyze_audio

        stats = analyze_audio(request.output_path)
        return VoiceSynthesisResult(
            engine=self.name,
            output_path=request.output_path,
            sample_rate=stats.sample_rate,
            duration_sec=stats.duration_s,
            used_reference_audio=True,
            used_reference_text=False,
            fallback_used=False,
            cache_hit=False,
            metadata={
                "model_name": self.model_name,
                "segment_id": request.segment_id,
                "prosody_controls": {
                    "temperature": os.environ.get("VIDIOLINGUA_XTTS_TEMP"),
                    "repetition_penalty": os.environ.get("VIDIOLINGUA_XTTS_REPETITION_PENALTY"),
                    "max_chars": os.environ.get("VIDIOLINGUA_XTTS_MAX_CHARS"),
                    "crossfade_ms": os.environ.get("VIDIOLINGUA_XTTS_CROSSFADE_MS"),
                    "preset": os.environ.get("VIDIOLINGUA_PROSODY_PRESET_USED"),
                },
            },
        )
