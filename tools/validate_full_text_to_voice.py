"""Validate translation routing followed by voice routing."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from translation.base import TranslationRequest
from translation.router import select_translation_engine, translate
from voice.base import VoiceSynthesisRequest
from voice.router import select_voice_engine, synthesize_voice


if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate text-to-voice routing.")
    parser.add_argument("--source-language", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true", help="Compatibility flag; real run is default unless --dry-run/--policy-only is set.")
    parser.add_argument("--dry-run", action="store_true", help="Policy-only alias; do not run heavy models.")
    parser.add_argument("--policy-only", action="store_true", help="Policy-only alias; do not run heavy models.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    execute = not args.dry_run and not args.policy_only
    translation_request = TranslationRequest(
        source_text=args.text,
        source_language=args.source_language,
        target_language=args.target_language,
    )
    try:
        translation_engine = select_translation_engine(translation_request)
        voice_text = args.text
        translation_payload = {"selected_engine": translation_engine, "policy_only": not execute}
        if execute:
            translation_result = translate(translation_request)
            translation_payload.update(asdict(translation_result))
            voice_text = translation_result.translated_text

        voice_request = VoiceSynthesisRequest(
            text=voice_text,
            target_language=args.target_language,
            output_path=Path(args.output),
            reference_audio_path=Path(args.reference),
            reference_text=args.reference_text,
            cloning_required=True,
        )
        voice_engine = select_voice_engine(voice_request)
        voice_payload = {
            "selected_engine": voice_engine,
            "policy_only": not execute,
            "managed_tts": voice_engine == "sarvam",
            "exact_voice_clone": voice_engine != "sarvam",
            "speaker_preservation": "not_supported" if voice_engine == "sarvam" else "reference_conditioned",
        }
        if execute:
            voice_result = synthesize_voice(voice_request)
            voice_payload.update(asdict(voice_result))
            voice_payload["output_path"] = str(voice_result.output_path)
        payload = {
            "ok": True,
            "translation": translation_payload,
            "voice": voice_payload,
            "llama_used": False,
            "deep_translator_used": False,
            "indic_parler_used": False,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "indic_parler_used": False}, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
