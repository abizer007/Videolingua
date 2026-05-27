"""Validate Coqui XTTS speaker cloning without running video/lip-sync stages."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from voice.xtts_cloner import (
    VoiceCloningError,
    VoiceClonePreflightError,
    clone_voice,
    config_from_env,
    preflight_xtts_voice_cloning,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate XTTS voice cloning end to end.")
    parser.add_argument("--text", help="Text to synthesize.")
    parser.add_argument("--reference", required=True, help="Reference speaker audio path.")
    parser.add_argument("--output", required=True, help="Output WAV path.")
    parser.add_argument("--language", default="en", help="XTTS language code, for example en or es.")
    parser.add_argument(
        "--model-path",
        help="Local XTTS v2 model directory containing config.json, model.pth, and vocab.json.",
    )
    parser.add_argument("--device", default=None, choices=["auto", "cpu", "cuda"], help="XTTS runtime device.")
    parser.add_argument("--model-load-timeout-seconds", type=int, default=None)
    parser.add_argument("--generation-timeout-seconds", type=int, default=None)
    parser.add_argument(
        "--intermediate-dir",
        default="outputs/intermediate",
        help="Directory for reference_clean.wav, xtts_raw.wav, and xtts_clean.wav.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate config, paths, model files, device, and reference audio without generation.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Generate the short phrase 'This is a short XTTS validation test.' once.",
    )
    parser.add_argument(
        "--force-voice-regenerate",
        action="store_true",
        help="Ignore reusable output artifacts and regenerate voice audio.",
    )
    parser.add_argument("--json", action="store_true", help="Print the validation report as JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    config = config_from_env(args.language)
    config.intermediate_dir = Path(args.intermediate_dir)
    config.force_regenerate = bool(args.force_voice_regenerate)
    config.voice_cloning_required = True
    config.allow_generic_tts_fallback = False
    if args.model_path:
        config.model_path = Path(args.model_path)
    if args.device:
        config.device = args.device
    if args.model_load_timeout_seconds is not None:
        config.model_load_timeout_seconds = args.model_load_timeout_seconds
    if args.generation_timeout_seconds is not None:
        config.generation_timeout_seconds = args.generation_timeout_seconds

    text = args.text
    if args.smoke_test:
        text = "This is a short XTTS validation test."
    if not args.preflight_only and not text:
        print("XTTS voice cloning validation FAILED: --text is required unless --preflight-only is used", file=sys.stderr)
        return 2

    try:
        preflight = preflight_xtts_voice_cloning(
            reference_audio_path=args.reference,
            output_path=args.output,
            language=args.language,
            config=config,
        )
        if args.preflight_only:
            report = preflight.to_report()
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print("XTTS voice cloning preflight PASSED")
                print(f"  model: {preflight.model_name}")
                print(f"  model dir: {preflight.model_files.model_dir if preflight.model_files else 'missing'}")
                print(f"  device: {preflight.device}")
                print(f"  cuda available: {preflight.cuda_available}")
                print(f"  reference duration: {preflight.reference_stats.duration_s:.2f}s")
                print(f"  output dir: {preflight.output_dir}")
                print(f"  intermediate dir: {preflight.intermediate_dir}")
                for warning in preflight.warnings:
                    print(f"  warning: {warning}")
            return 0

        result = clone_voice(
            text=text or "",
            reference_audio_path=args.reference,
            output_path=args.output,
            language=args.language,
            config=config,
        )
    except VoiceClonePreflightError as exc:
        print(f"XTTS voice cloning preflight FAILED: {exc}", file=sys.stderr)
        return 1
    except VoiceCloningError as exc:
        print(f"XTTS voice cloning validation FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"XTTS voice cloning validation FAILED unexpectedly: {exc}", file=sys.stderr)
        return 1

    report = result.to_report()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("XTTS voice cloning validation PASSED")
        print(f"  model: {result.model_name}")
        print(f"  language: {result.language}")
        print(f"  speaker_wav used: {result.speaker_wav_used}")
        print(f"  fallback attempted: {result.fallback_attempted}")
        print(f"  reference: {result.cleaned_reference_path}")
        print(f"  reference duration: {result.reference_stats.duration_s:.2f}s")
        print(f"  raw XTTS: {result.raw_xtts_path}")
        print(f"  clean XTTS: {result.clean_xtts_path}")
        print(f"  output: {result.output_path}")
        print(f"  generated duration: {result.generated_stats.duration_s:.2f}s")
        print(f"  cache key: {result.cache_key}")
        print("  speaker similarity: not objectively verified; no embedding model is configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
