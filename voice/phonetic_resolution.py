"""Phonetic and Ambiguity Resolution Layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from voice.base import normalize_voice_language
from voice.pronunciation_dictionary import PronunciationDictionary, load_pronunciation_dictionary
from voice.tts_text_preparation import prepare_tts_text


@dataclass
class PhoneticResolutionReport:
    status: str
    phonetic_risk_score_0_100: float
    target_language: str
    dictionary_used: bool
    terms_detected: list[str] = field(default_factory=list)
    acronyms_detected: list[str] = field(default_factory=list)
    ambiguity_warnings: list[dict[str, Any]] = field(default_factory=list)
    replacements_applied: list[dict[str, Any]] = field(default_factory=list)
    segment_reports: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "phonetic_risk_score_0_100": self.phonetic_risk_score_0_100,
            "target_language": self.target_language,
            "dictionary_used": self.dictionary_used,
            "terms_detected": self.terms_detected,
            "acronyms_detected": self.acronyms_detected,
            "ambiguity_warnings": self.ambiguity_warnings,
            "replacements_applied": self.replacements_applied,
            "segment_reports": self.segment_reports,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _risk_score(segment_reports: list[dict[str, Any]], errors: list[str]) -> float:
    risk = 0.0
    if errors:
        risk += 40.0
    risk += min(35.0, sum(len(item.get("acronyms_detected") or []) for item in segment_reports) * 5.0)
    risk += min(30.0, sum(len(item.get("ambiguity_warnings") or []) for item in segment_reports) * 8.0)
    risk -= min(25.0, sum(len(item.get("pronunciation_replacements_applied") or []) for item in segment_reports) * 4.0)
    return round(max(0.0, min(100.0, risk)), 2)


def analyze_phonetic_resolution(
    translation_data: dict[str, Any],
    *,
    target_language: str | None = None,
    dictionary: PronunciationDictionary | None = None,
    dictionary_path: str | Path | None = None,
    source_segments: list[dict[str, Any]] | None = None,
    source_language: str | None = None,
) -> tuple[dict[str, Any], PhoneticResolutionReport]:
    target = normalize_voice_language(target_language or str(translation_data.get("language") or ""))
    dictionary = dictionary if dictionary is not None else load_pronunciation_dictionary(dictionary_path)
    output = dict(translation_data)
    prepared_segments: list[dict[str, Any]] = []
    segment_reports: list[dict[str, Any]] = []
    terms_detected: set[str] = set()
    acronyms_detected: set[str] = set()
    ambiguity_warnings: list[dict[str, Any]] = []
    replacements: list[dict[str, Any]] = []
    warnings: set[str] = set()
    errors: list[str] = []
    source_by_id = {str(segment.get("id")): segment for segment in source_segments or [] if isinstance(segment, dict)}

    for index, segment in enumerate(output.get("segments") or []):
        if not isinstance(segment, dict):
            continue
        next_segment = dict(segment)
        segment_id = str(next_segment.get("id") or index)
        display_text = str(next_segment.get("text") or "")
        source_text = str((source_by_id.get(segment_id) or {}).get("text") or "")
        prepared = prepare_tts_text(
            display_text,
            target,
            dictionary=dictionary,
            source_text=source_text,
            source_language=source_language or output.get("source_language"),
        )
        next_segment["display_text"] = display_text
        next_segment["tts_prepared_text"] = prepared["tts_prepared_text"]
        prepared_segments.append(next_segment)
        report_item = {"segment_id": segment_id, **prepared}
        segment_reports.append(report_item)
        terms_detected.update(prepared.get("terms_detected") or [])
        acronyms_detected.update(prepared.get("acronyms_detected") or [])
        ambiguity_warnings.extend({"segment_id": segment_id, **item} for item in prepared.get("ambiguity_warnings") or [])
        replacements.extend({"segment_id": segment_id, **item} for item in prepared.get("pronunciation_replacements_applied") or [])
        warnings.update(prepared.get("warnings") or [])

    output["segments"] = prepared_segments
    risk = _risk_score(segment_reports, errors)
    status = "failed" if errors else "warning" if warnings or risk >= 25 else "passed"
    report = PhoneticResolutionReport(
        status=status,
        phonetic_risk_score_0_100=risk,
        target_language=target,
        dictionary_used=dictionary.used,
        terms_detected=sorted(terms_detected),
        acronyms_detected=sorted(acronyms_detected),
        ambiguity_warnings=ambiguity_warnings,
        replacements_applied=replacements,
        segment_reports=segment_reports,
        warnings=sorted(warnings),
        errors=errors,
    )
    output["phonetic_resolution"] = build_phonetic_resolution_summary(report)
    return output, report


def build_phonetic_resolution_summary(report: dict[str, Any] | PhoneticResolutionReport, report_path: str | None = None) -> dict[str, Any]:
    payload = report.to_dict() if isinstance(report, PhoneticResolutionReport) else report
    return {
        "status": payload.get("status"),
        "phoneticRiskScore": payload.get("phonetic_risk_score_0_100"),
        "termsDetected": len(payload.get("terms_detected") or []),
        "acronymsDetected": len(payload.get("acronyms_detected") or []),
        "ambiguityWarnings": len(payload.get("ambiguity_warnings") or []),
        "dictionaryUsed": bool(payload.get("dictionary_used")),
        "reportPath": report_path,
    }


def write_phonetic_resolution_report(report: dict[str, Any] | PhoneticResolutionReport, output_path: str | Path) -> Path:
    payload = report.to_dict() if isinstance(report, PhoneticResolutionReport) else report
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
