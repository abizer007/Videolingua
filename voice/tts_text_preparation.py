"""TTS-safe text preparation without mutating canonical transcript text."""

from __future__ import annotations

from typing import Any
import re

from voice.base import normalize_voice_language, sarvam_supports_language, xtts_supports_language
from voice.pronunciation_dictionary import PronunciationDictionary, PronunciationEntry


ACRONYM_RE = re.compile(r"\b(?:[A-Z]{2,}\d*|(?:[A-Z]\.){2,}[A-Z]?)\b")
DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b")
HOMOPHONE_AMBIGUITIES = {
    "read": "read can be present or past tense",
    "lead": "lead can be a metal or a verb",
    "bow": "bow can mean bend, weapon, or knot",
    "live": "live can be a verb or adjective",
    "wind": "wind can mean air movement or turning",
    "minute": "minute can mean time unit or very small",
    "bass": "bass can be a sound range or a fish",
}


def _spell_acronym(value: str) -> str:
    chars = [char for char in value.replace(".", "") if char.isalnum()]
    return " ".join(chars)


def _safe_for_dictionary_replacement(language: str, entry: PronunciationEntry) -> bool:
    target = normalize_voice_language(language)
    if not entry.supports(target):
        return False
    if sarvam_supports_language(target) and not xtts_supports_language(target):
        return True
    return True


def _apply_dictionary(text: str, language: str, dictionary: PronunciationDictionary) -> tuple[str, list[dict[str, str]], list[str]]:
    prepared = text
    replacements: list[dict[str, str]] = []
    detected: list[str] = []
    for entry in dictionary.terms:
        if not _safe_for_dictionary_replacement(language, entry):
            continue
        pattern = re.compile(rf"\b{re.escape(entry.term)}\b", re.IGNORECASE)
        if not pattern.search(prepared):
            continue
        detected.append(entry.term)
        prepared = pattern.sub(entry.spoken_form, prepared)
        replacements.append({"term": entry.term, "spoken_form": entry.spoken_form, "reason": "pronunciation_dictionary"})
    return prepared, replacements, detected


def _detect_homophones(text: str, source_language: str | None, target_language: str) -> list[dict[str, str]]:
    language = normalize_voice_language(source_language or target_language)
    if language != "en":
        return []
    words = {word.lower() for word in re.findall(r"\b[A-Za-z]+\b", text or "")}
    return [{"term": term, "reason": reason} for term, reason in HOMOPHONE_AMBIGUITIES.items() if term in words]


def prepare_tts_text(
    display_text: str,
    target_language: str,
    *,
    dictionary: PronunciationDictionary | None = None,
    source_text: str | None = None,
    source_language: str | None = None,
) -> dict[str, Any]:
    text = display_text or ""
    prepared = re.sub(r"\s+", " ", text).strip()
    dictionary = dictionary or PronunciationDictionary(path=None, terms=())
    replacements: list[dict[str, str]] = []
    terms_detected: list[str] = []
    warnings: list[str] = []

    prepared, dictionary_replacements, detected = _apply_dictionary(prepared, target_language, dictionary)
    replacements.extend(dictionary_replacements)
    terms_detected.extend(detected)

    acronyms = []
    for match in ACRONYM_RE.finditer(prepared):
        raw = match.group(0)
        spoken = _spell_acronym(raw)
        if spoken and spoken != raw:
            acronyms.append(raw)
    for raw in sorted(set(acronyms), key=len, reverse=True):
        spoken = _spell_acronym(raw)
        prepared = re.sub(rf"\b{re.escape(raw)}\b", spoken, prepared)
        replacements.append({"term": raw, "spoken_form": spoken, "reason": "safe_acronym_expansion"})

    date_warnings = [{"term": match.group(0), "reason": "date format may be ambiguous for TTS"} for match in DATE_RE.finditer(text)]
    if date_warnings:
        warnings.append("date_ambiguity")

    ambiguity_warnings = _detect_homophones(source_text or text, source_language, target_language)
    if ambiguity_warnings:
        warnings.append("english_homophone_ambiguity")

    changes = []
    if prepared != text:
        changes.append("tts_prepared_text_changed")
    return {
        "display_text": text,
        "tts_prepared_text": prepared,
        "terms_detected": sorted(set(terms_detected)),
        "acronyms_detected": sorted(set(acronyms)),
        "ambiguity_warnings": ambiguity_warnings + date_warnings,
        "pronunciation_replacements_applied": replacements,
        "warnings": warnings,
        "changes": changes,
    }
