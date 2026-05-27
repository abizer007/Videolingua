"""Punctuation and sentence-boundary validation helpers."""

from __future__ import annotations

import re
from typing import Any


SENTENCE_END_RE = re.compile(r"[.!?।॥。！？؟]$")
REPEATED_PUNCT_RE = re.compile(r"([.!?,;:।])\1{2,}")


def has_sentence_end_punctuation(text: str) -> bool:
    return bool(SENTENCE_END_RE.search((text or "").strip()))


def punctuation_profile(text: str) -> dict[str, int]:
    value = text or ""
    return {
        "sentence_end": int(has_sentence_end_punctuation(value)),
        "commas": value.count(","),
        "question_marks": value.count("?") + value.count("؟"),
        "exclamation_marks": value.count("!"),
        "repeated_punctuation": len(REPEATED_PUNCT_RE.findall(value)),
    }


def check_punctuation_preservation(source_text: str, translated_text: str) -> dict[str, Any]:
    source_profile = punctuation_profile(source_text)
    translated_profile = punctuation_profile(translated_text)
    warnings: list[str] = []
    if source_profile["sentence_end"] and not translated_profile["sentence_end"]:
        warnings.append("sentence-ending punctuation missing")
    if translated_profile["repeated_punctuation"]:
        warnings.append("repeated punctuation anomaly")
    if source_profile["question_marks"] and not translated_profile["question_marks"]:
        warnings.append("source question mark not reflected")
    return {
        "status": "warning" if warnings else "passed",
        "source": source_profile,
        "translated": translated_profile,
        "warnings": warnings,
    }
