"""Lightweight entity and number preservation checks."""

from __future__ import annotations

import re
from typing import Iterable


NUMBER_RE = re.compile(
    r"""
    (?:
      (?:[$€£₹]\s*)?
      \b\d{1,4}(?:[,\-/.:]\d{1,4})*(?:\.\d+)?%?
    )
    """,
    re.VERBOSE,
)

ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9&.-]{1,}\b")
MIXED_CASE_RE = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\b")
CAPITALIZED_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+|$)){1,4}")

COMMON_SENTENCE_STARTERS = {
    "A",
    "An",
    "And",
    "But",
    "For",
    "I",
    "If",
    "It",
    "So",
    "The",
    "This",
    "That",
    "These",
    "Those",
    "Well",
    "Why",
    "With",
}


def normalize_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).strip(".,;:!?()[]{}\"'")


def extract_number_tokens(text: str) -> list[str]:
    return [normalize_token(match.group(0)) for match in NUMBER_RE.finditer(text or "") if normalize_token(match.group(0))]


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = normalize_token(value)
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            out.append(normalized)
    return out


def extract_entities(text: str, glossary_terms: Iterable[str] | None = None) -> list[str]:
    candidates: list[str] = []
    text = text or ""
    candidates.extend(match.group(0) for match in ACRONYM_RE.finditer(text))
    candidates.extend(match.group(0) for match in MIXED_CASE_RE.finditer(text))
    for match in CAPITALIZED_PHRASE_RE.finditer(text):
        phrase = normalize_token(match.group(0))
        if not phrase:
            continue
        words = phrase.split()
        if len(words) == 1 and words[0] in COMMON_SENTENCE_STARTERS:
            continue
        candidates.append(phrase)
    if glossary_terms:
        lower_text = text.lower()
        for term in glossary_terms:
            clean = normalize_token(str(term))
            if clean and clean.lower() in lower_text:
                candidates.append(clean)
    return _unique(candidates)


def missing_numbers(source_text: str, translated_text: str) -> list[str]:
    translated_numbers = set(extract_number_tokens(translated_text))
    missing: list[str] = []
    for token in extract_number_tokens(source_text):
        if token not in translated_numbers:
            missing.append(token)
    return missing


def missing_entities(source_text: str, translated_text: str, glossary_terms: Iterable[str] | None = None) -> list[str]:
    translated_lower = (translated_text or "").lower()
    missing: list[str] = []
    for entity in extract_entities(source_text, glossary_terms):
        if entity.lower() not in translated_lower:
            missing.append(entity)
    return missing


def has_sentence_end_punctuation(text: str) -> bool:
    return bool(re.search(r"[.!?।॥。！？؟]$", (text or "").strip()))
