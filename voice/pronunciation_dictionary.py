"""Pronunciation dictionary loading and lookup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import os

from voice.base import normalize_voice_language


@dataclass(frozen=True)
class PronunciationEntry:
    term: str
    spoken_form: str
    preserve_text: bool = True
    languages: tuple[str, ...] = ()

    def supports(self, language: str) -> bool:
        if not self.languages:
            return True
        target = normalize_voice_language(language)
        return target in {normalize_voice_language(item) for item in self.languages}


@dataclass(frozen=True)
class PronunciationDictionary:
    path: str | None
    terms: tuple[PronunciationEntry, ...]

    @property
    def used(self) -> bool:
        return bool(self.terms)


def _entry_from_dict(item: dict[str, Any]) -> PronunciationEntry | None:
    term = str(item.get("term") or "").strip()
    spoken_form = str(item.get("spoken_form") or "").strip()
    if not term or not spoken_form:
        return None
    languages = item.get("languages")
    if not isinstance(languages, list):
        languages = []
    return PronunciationEntry(
        term=term,
        spoken_form=spoken_form,
        preserve_text=bool(item.get("preserve_text", True)),
        languages=tuple(str(lang).strip() for lang in languages if str(lang).strip()),
    )


def load_pronunciation_dictionary(path: str | Path | None = None, *, strict: bool = False) -> PronunciationDictionary:
    raw_path = str(path or os.environ.get("VIDIOLINGUA_PRONUNCIATION_DICTIONARY", "")).strip()
    if not raw_path:
        return PronunciationDictionary(path=None, terms=())
    dictionary_path = Path(raw_path)
    if not dictionary_path.is_absolute():
        dictionary_path = Path(__file__).resolve().parents[1] / dictionary_path
    if not dictionary_path.is_file():
        if strict:
            raise FileNotFoundError(f"Pronunciation dictionary not found: {dictionary_path}")
        return PronunciationDictionary(path=str(dictionary_path), terms=())
    data = json.loads(dictionary_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Pronunciation dictionary must be a JSON object")
    entries = tuple(
        entry
        for item in data.get("terms", [])
        if isinstance(item, dict)
        for entry in [_entry_from_dict(item)]
        if entry is not None
    )
    return PronunciationDictionary(path=str(dictionary_path), terms=entries)
