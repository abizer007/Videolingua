"""Number, date, percent, and currency preservation checks."""

from __future__ import annotations

import re
from typing import Any


NUMBER_TOKEN_RE = re.compile(
    r"""
    (?P<currency>[$€£₹]\s*\d[\d,]*(?:\.\d+)?)
    |(?P<percent>\d[\d,]*(?:\.\d+)?\s*%)
    |(?P<date>\b\d{1,4}[/-]\d{1,2}(?:[/-]\d{1,4})?\b)
    |(?P<ordinal>\b\d+(?:st|nd|rd|th)\b)
    |(?P<number>\b\d[\d,]*(?:\.\d+)?\b)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _normalize_digits(value: str) -> str:
    return re.sub(r"[^\d.%-]", "", value or "")


def extract_number_tokens(text: str) -> list[dict[str, str]]:
    tokens: list[dict[str, str]] = []
    for match in NUMBER_TOKEN_RE.finditer(text or ""):
        kind = next((name for name, value in match.groupdict().items() if value), "number")
        raw = match.group(0).strip()
        normalized = _normalize_digits(raw)
        if raw and normalized:
            tokens.append({"raw": raw, "normalized": normalized, "kind": kind})
    return tokens


def check_number_preservation(source_text: str, translated_text: str) -> dict[str, Any]:
    source_tokens = extract_number_tokens(source_text)
    translated_tokens = extract_number_tokens(translated_text)
    translated_values = {token["normalized"] for token in translated_tokens}
    missing = [token for token in source_tokens if token["normalized"] not in translated_values]
    changed_count = max(0, len(translated_tokens) - len(source_tokens))
    status = "warning" if missing or changed_count else "passed"
    return {
        "status": status,
        "source_tokens": source_tokens,
        "translated_tokens": translated_tokens,
        "missing": missing,
        "extra_or_changed_count": changed_count,
        "issue_count": len(missing) + changed_count,
    }
