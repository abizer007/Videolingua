"""Validate voice router selection and optionally synthesize audio."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from voice.base import VoiceSynthesisRequest
from voice.base import (
    indicf5_supports_language,
    normalize_voice_language,
    sarvam_supports_language,
    xtts_supports_language,
)
from voice.router import select_voice_engine, synthesize_voice


if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _bool_arg(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate voice router policy.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--reference")
    parser.add_argument("--reference-text")
    parser.add_argument("--cloning-required", default="true")
    parser.add_argument("--preferred-engine", default="auto")
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true", help="Compatibility flag; real run is default unless --dry-run/--policy-only is set.")
    parser.add_argument("--dry-run", action="store_true", help="Policy-only alias; do not synthesize audio.")
    parser.add_argument("--policy-only", action="store_true", help="Policy-only alias; do not synthesize audio.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = VoiceSynthesisRequest(
        text=args.text,
        target_language=args.target_language,
        output_path=Path(args.output),
        reference_audio_path=Path(args.reference) if args.reference else None,
        reference_text=args.reference_text,
        preferred_engine=args.preferred_engine,
        cloning_required=_bool_arg(args.cloning_required),
    )
    payload: dict = {}
    execute = not args.dry_run and not args.policy_only
    language = normalize_voice_language(args.target_language)
    try:
        selected = select_voice_engine(request)
        payload = {
            "ok": True,
            "selected_engine": selected,
            "target_language": language,
            "xtts_supported": xtts_supports_language(language),
            "sarvam_supported": sarvam_supports_language(language),
            "indicf5_supported": indicf5_supports_language(language),
            "cloning_required": _bool_arg(args.cloning_required),
            "reference_audio": args.reference,
            "reference_text_present": bool((args.reference_text or "").strip()),
            "xtts_used": selected == "xtts",
            "sarvam_used": selected == "sarvam",
            "indicf5_used": selected == "indicf5",
            "indic_parler_used": False,
            "generic_fallback_used": False,
            "managed_tts": selected == "sarvam",
            "exact_voice_clone": selected != "sarvam",
            "speaker_preservation": "not_supported" if selected == "sarvam" else "reference_conditioned",
            "policy_only": not execute,
        }
        if execute:
            result = synthesize_voice(request)
            payload.update(asdict(result))
            payload["output_path"] = str(result.output_path)
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0
    except Exception as exc:
        payload = {
            "ok": False,
            "selected_engine": "blocked",
            "target_language": language,
            "xtts_supported": xtts_supports_language(language),
            "sarvam_supported": sarvam_supports_language(language),
            "indicf5_supported": indicf5_supports_language(language),
            "cloning_required": _bool_arg(args.cloning_required),
            "reference_audio": args.reference,
            "reference_text_present": bool((args.reference_text or "").strip()),
            "sarvam_used": False,
            "generic_fallback_used": False,
            "indic_parler_used": False,
            "managed_tts": False,
            "exact_voice_clone": False,
            "policy_only": not execute,
            "error": str(exc),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
