"""Validate translation router selection and optionally execute translation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from translation.base import TranslationRequest, indictrans2_supports_pair, normalize_language_code
from translation.router import select_translation_engine, translate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate translation router policy.")
    parser.add_argument("--source-language", required=True)
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preferred-engine", default="auto")
    parser.add_argument("--allow-llm-fallback", action="store_true")
    parser.add_argument("--allow-deep-translator-fallback", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Compatibility flag; execution is the default unless dry-run/policy-only is set.")
    parser.add_argument("--dry-run", action="store_true", help="Policy-only alias; do not run engines.")
    parser.add_argument("--policy-only", action="store_true", help="Policy-only alias; do not run engines.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = TranslationRequest(
        source_text=args.text,
        source_language=args.source_language,
        target_language=args.target_language,
        preferred_engine=args.preferred_engine,
        allow_llm_fallback=args.allow_llm_fallback,
        allow_deep_translator_fallback=args.allow_deep_translator_fallback,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    execute = not args.dry_run and not args.policy_only
    source = normalize_language_code(args.source_language)
    target = normalize_language_code(args.target_language)
    supported_pair = indictrans2_supports_pair(source, target)
    try:
        selected = select_translation_engine(request)
        payload = {
            "ok": True,
            "selected_engine": selected,
            "source_language": source,
            "target_language": target,
            "indictrans2_supported_pair": supported_pair,
            "llama_used": False,
            "deep_translator_used": False,
            "indictrans2_used": selected == "indictrans2",
            "fallback_blocked": selected == "indictrans2" or selected == "blocked",
            "policy_only": not execute,
        }
        if execute:
            result = translate(request)
            payload.update(asdict(result))
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    except Exception as exc:
        payload = {
            "ok": bool(args.dry_run or args.policy_only),
            "selected_engine": "blocked",
            "source_language": source,
            "target_language": target,
            "indictrans2_supported_pair": supported_pair,
            "llama_used": False,
            "deep_translator_used": False,
            "indictrans2_used": False,
            "fallback_blocked": True,
            "policy_only": not execute,
            "error": str(exc),
        }
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0 if args.dry_run or args.policy_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
