"""Lightweight named-entity, acronym, and project term preservation checks."""

from __future__ import annotations

import re
from typing import Any, Iterable


PROJECT_TERMS = [
    "Vidiolingua",
    "VideoLingua",
    "Techgium",
    "NMIMS",
    "Sarvam",
    "IndicTrans2",
    "XTTS",
    "Coqui",
    "API",
    "AI",
    "TTS",
    "ASR",
]

ACRONYM_RE = re.compile(r"\b(?:[A-Z]{2,}(?:\d+)?|(?:[A-Z]\.){2,}[A-Z]?)\b")
CAMEL_TERM_RE = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\b")
CAPITALIZED_NAME_RE = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,3}\b")

COMMON_STARTERS = {
    "A",
    "An",
    "And",
    "As",
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
    "We",
    "Well",
    "With",
    "Why",
}


def normalize_term(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).strip(".,;:!?()[]{}\"'")


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        clean = normalize_term(str(value))
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            out.append(clean)
    return out


def extract_acronyms(text: str) -> list[str]:
    return _unique(match.group(0).replace(".", "") for match in ACRONYM_RE.finditer(text or ""))


def extract_candidate_terms(text: str, glossary_terms: Iterable[str] | None = None) -> list[str]:
    candidates: list[str] = []
    source_text = text or ""
    lower_source = source_text.lower()
    candidates.extend(extract_acronyms(source_text))
    candidates.extend(match.group(0) for match in CAMEL_TERM_RE.finditer(source_text))
    for match in CAPITALIZED_NAME_RE.finditer(source_text):
        term = normalize_term(match.group(0))
        words = term.split()
        if len(words) == 1 and words[0] in COMMON_STARTERS:
            continue
        candidates.append(term)
    for term in PROJECT_TERMS:
        if term.lower() in lower_source:
            candidates.append(term)
    for term in glossary_terms or []:
        clean = normalize_term(str(term))
        if clean and clean.lower() in lower_source:
            candidates.append(clean)
    return _unique(candidates)


def check_name_entity_preservation(
    source_text: str,
    translated_text: str,
    *,
    glossary_terms: Iterable[str] | None = None,
    roman_allowlist: Iterable[str] | None = None,
) -> dict[str, Any]:
    terms = extract_candidate_terms(source_text, glossary_terms)
    translated_lower = (translated_text or "").lower()
    allowlist = {normalize_term(term).lower() for term in roman_allowlist or []}
    missing: list[dict[str, str]] = []
    detected: list[dict[str, str]] = []
    for term in terms:
        key = term.lower()
        detected.append({"term": term, "type": "acronym" if term in extract_acronyms(term) else "proper_noun"})
        if key in translated_lower:
            continue
        severity = "warning"
        if key in allowlist or term in PROJECT_TERMS or term.isupper():
            severity = "warning"
        missing.append({"term": term, "severity": severity, "reason": "not found literally in translated text"})
    return {
        "status": "warning" if missing else "passed",
        "detected": detected,
        "missing": missing,
        "missing_count": len(missing),
    }
