"""IndicF5 voice engine adapter."""

from __future__ import annotations

from voice.base import VoiceSynthesisRequest, VoiceSynthesisResult, normalize_voice_language


class IndicF5Engine:
    name = "indicf5"
    model_name = "ai4bharat/IndicF5"

    def synthesize(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        from app.services.indicf5_tts_service import synthesize_to_wav

        synthesize_to_wav(
            text=request.text,
            output_path=request.output_path,
            speaker_wav=str(request.reference_audio_path) if request.reference_audio_path else None,
            ref_text=request.reference_text,
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
            used_reference_text=True,
            fallback_used=False,
            cache_hit=False,
            metadata={"model_name": self.model_name, "segment_id": request.segment_id},
        )
