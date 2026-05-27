"""Validate Sarvam AI managed Indian-language TTS."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from voice.base import VoiceSynthesisRequest, normalize_voice_language, sarvam_supports_language
from voice.engines.sarvam_engine import SarvamEngine, mask_secret


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "backend" / ".env")
except Exception:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Sarvam AI TTS.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--speaker")
    parser.add_argument("--model")
    parser.add_argument("--dry-run", action="store_true", help="Show request config without calling Sarvam.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    language = normalize_voice_language(args.language)
    engine = SarvamEngine(model=args.model, speaker=args.speaker)
    api_key = os.environ.get("SARVAM_API_KEY", "").strip()

    try:
        config = engine.request_config(language, args.text)
        payload = {
            "ok": True,
            "provider": "sarvam",
            "dry_run": bool(args.dry_run),
            "api_key_configured": bool(api_key),
            "api_key_masked": mask_secret(api_key),
            "language": language,
            "sarvam_supported": sarvam_supports_language(language),
            "output_path": str(Path(args.output)),
            "request": config,
            "managed_tts": True,
            "exact_voice_clone": False,
            "speaker_preservation": "not_supported",
        }
        if args.dry_run:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        result = engine.synthesize(
            VoiceSynthesisRequest(
                text=args.text,
                target_language=language,
                output_path=Path(args.output),
                preferred_engine="sarvam",
                cloning_required=True,
            )
        )
        payload["result"] = asdict(result)
        payload["result"]["output_path"] = str(result.output_path)
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "provider": "sarvam",
                    "dry_run": bool(args.dry_run),
                    "api_key_configured": bool(api_key),
                    "api_key_masked": mask_secret(api_key),
                    "language": language,
                    "sarvam_supported": sarvam_supports_language(language),
                    "managed_tts": True,
                    "exact_voice_clone": False,
                    "speaker_preservation": "not_supported",
                    "error": str(exc).replace(api_key, mask_secret(api_key)) if api_key else str(exc),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
