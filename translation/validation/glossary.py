"""Optional glossary support for translation QA."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_glossary(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    glossary_path = Path(path)
    if not glossary_path.is_file():
        raise FileNotFoundError(f"Translation glossary not found: {glossary_path}")
    data = json.loads(glossary_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Translation glossary must be a JSON object")
    terms = data.get("terms")
    if terms is not None and not isinstance(terms, list):
        raise ValueError("Translation glossary 'terms' must be a list")
    data["terms"] = [term for term in (terms or []) if isinstance(term, dict)]
    return data


def glossary_hash(glossary: dict[str, Any] | None) -> str | None:
    if not glossary:
        return None
    payload = json.dumps(glossary, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def glossary_terms(glossary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not glossary:
        return []
    return [term for term in glossary.get("terms", []) if isinstance(term, dict) and str(term.get("source") or "").strip()]


def preserved_terms(glossary: dict[str, Any] | None) -> list[str]:
    terms: list[str] = []
    for item in glossary_terms(glossary):
        if item.get("preserve") is True:
            source = str(item.get("source") or "").strip()
            if source:
                terms.append(source)
    return terms


def check_glossary_terms(
    source_text: str,
    translated_text: str,
    glossary: dict[str, Any] | None,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    source_lower = source_text.lower()
    translated_lower = translated_text.lower()
    for term in glossary_terms(glossary):
        source = str(term.get("source") or "").strip()
        if not source or source.lower() not in source_lower:
            continue
        target = str(term.get("target") or "").strip()
        preserve = term.get("preserve") is True
        expected_values = [value for value in (source if preserve else "", target) if value]
        if not expected_values:
            continue
        if not any(value.lower() in translated_lower for value in expected_values):
            issues.append(
                {
                    "term": source,
                    "expected": " or ".join(expected_values),
                    "reason": "glossary term was present in source but not found in translation",
                }
            )
    return issues
