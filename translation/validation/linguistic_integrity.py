"""Grammar and Linguistic Integrity Engine.

This module is a validation/preparation layer around translation output. It
does not claim trained grammar correction; it computes concrete localization QA
signals and produces auditable reports for pipeline artifacts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import re

from translation.base import normalize_language_code
from translation.validation.expansion_ratio import analyze_expansion_ratios
from translation.validation.glossary import preserved_terms
from translation.validation.name_entity_preservation import PROJECT_TERMS, check_name_entity_preservation, extract_candidate_terms
from translation.validation.number_preservation import check_number_preservation
from translation.validation.punctuation_checks import check_punctuation_preservation
from translation.validation.script_checks import analyze_script_segments
from translation.validation.segment_integrity import check_empty_segments, check_segment_alignment, normalize_segments


@dataclass
class LinguisticIntegrityReport:
    status: str
    score_0_100: float
    severity: str
    source_language: str
    target_language: str
    checks: dict[str, Any]
    segment_reports: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "score_0_100": self.score_0_100,
            "severity": self.severity,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "checks": self.checks,
            "segment_reports": self.segment_reports,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _status_from_issues(errors: list[str], warnings: list[str]) -> str:
    return "failed" if errors else "warning" if warnings else "passed"


def _severity_from_score(score: float, status: str) -> str:
    if status == "failed" or score < 55:
        return "failed"
    if score < 75:
        return "needs review"
    if score < 90:
        return "good"
    return "excellent"


def _status(check: dict[str, Any]) -> str:
    value = check.get("status")
    return value if value in {"passed", "warning", "failed"} else "passed"


def _compute_score(checks: dict[str, Any], segment_reports: list[dict[str, Any]]) -> float:
    score = 100.0
    for check in checks.values():
        if not isinstance(check, dict):
            continue
        if _status(check) == "failed":
            score -= 18.0
        elif _status(check) == "warning":
            score -= 7.0
    segment_warning_count = sum(len(item.get("warnings") or []) for item in segment_reports)
    segment_error_count = sum(len(item.get("errors") or []) for item in segment_reports)
    score -= min(25.0, segment_warning_count * 1.2)
    score -= min(35.0, segment_error_count * 5.0)
    return round(max(0.0, min(100.0, score)), 2)


def _repetition_check(translated_segments: list[dict[str, Any]]) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    texts = [str(segment.get("text") or "").strip() for segment in translated_segments]
    repeated_texts = {
        text: count
        for text, count in Counter(text for text in texts if len(text) >= 3).items()
        if count >= 3
    }
    for text, count in repeated_texts.items():
        warnings.append({"reason": "identical translated segment repeated", "count": count, "text_preview": text[:80]})
    for index, text in enumerate(texts):
        tokens = re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
        if len(tokens) >= 6:
            token, count = Counter(token.lower() for token in tokens).most_common(1)[0]
            if count >= 5 and count / max(1, len(tokens)) >= 0.45:
                warnings.append({"segment_id": str(translated_segments[index].get("id") or index), "reason": "repeated token", "token": token, "count": count})
        if re.search(r"([.!?,;:।])\1{2,}", text):
            warnings.append({"segment_id": str(translated_segments[index].get("id") or index), "reason": "repeated punctuation"})
    repetition_score = max(0.0, 100.0 - (len(warnings) * 12.5))
    return {
        "status": "warning" if warnings else "passed",
        "repetition_score": round(repetition_score, 2),
        "warnings": warnings,
        "affected_segment_ids": [str(item.get("segment_id")) for item in warnings if item.get("segment_id")],
    }


def _glossary_terms(glossary: dict[str, Any] | None) -> list[str]:
    return [str(term).strip() for term in preserved_terms(glossary) if str(term).strip()]


def analyze_linguistic_integrity(
    source_segments: list[Any],
    translated_segments: list[Any],
    source_language: str,
    target_language: str,
    *,
    glossary: dict[str, Any] | None = None,
) -> LinguisticIntegrityReport:
    source_lang = normalize_language_code(source_language)
    target_lang = normalize_language_code(target_language)
    source = normalize_segments(source_segments)
    translated = normalize_segments(translated_segments)
    glossary_terms = _glossary_terms(glossary)
    roman_allowlist = sorted(set(PROJECT_TERMS + glossary_terms + [term for segment in source for term in extract_candidate_terms(str(segment.get("text") or ""), glossary_terms)]))

    checks: dict[str, Any] = {
        "segment_alignment": check_segment_alignment(source, translated),
        "empty_segments": check_empty_segments(source, translated),
        "script": analyze_script_segments(translated, target_lang, roman_allowlist=roman_allowlist),
        "repetition": _repetition_check(translated),
        "length_ratio": analyze_expansion_ratios(source, translated, target_lang),
    }

    number_issues: list[dict[str, Any]] = []
    name_issues: list[dict[str, Any]] = []
    punctuation_issues: list[dict[str, Any]] = []
    segment_reports: list[dict[str, Any]] = []
    for index, source_segment in enumerate(source):
        translated_segment = translated[index] if index < len(translated) else {"id": source_segment.get("id"), "text": ""}
        segment_id = str(source_segment.get("id") or index)
        source_text = str(source_segment.get("text") or "")
        translated_text = str(translated_segment.get("text") or "")
        numbers = check_number_preservation(source_text, translated_text)
        names = check_name_entity_preservation(
            source_text,
            translated_text,
            glossary_terms=glossary_terms,
            roman_allowlist=roman_allowlist,
        )
        punctuation = check_punctuation_preservation(source_text, translated_text)
        warnings = []
        errors = []
        if numbers["status"] == "warning":
            number_issues.append({"segment_id": segment_id, **numbers})
            warnings.append("number_preservation")
        if names["status"] == "warning":
            name_issues.append({"segment_id": segment_id, **names})
            warnings.append("names_entities")
        if punctuation["status"] == "warning":
            punctuation_issues.append({"segment_id": segment_id, **punctuation})
            warnings.append("punctuation")
        if source_text.strip() and not translated_text.strip():
            errors.append("empty_translation")
        segment_reports.append(
            {
                "segment_id": segment_id,
                "source_text_preview": source_text[:160],
                "translated_text_preview": translated_text[:160],
                "numbers": numbers,
                "names_entities": names,
                "punctuation": punctuation,
                "warnings": warnings,
                "errors": errors,
            }
        )

    checks["numbers"] = {
        "status": "warning" if number_issues else "passed",
        "issues": number_issues,
        "affected_segment_ids": [item["segment_id"] for item in number_issues],
    }
    checks["names_entities"] = {
        "status": "warning" if name_issues else "passed",
        "issues": name_issues,
        "project_terms": PROJECT_TERMS,
        "roman_allowlist": roman_allowlist,
        "affected_segment_ids": [item["segment_id"] for item in name_issues],
    }
    checks["punctuation"] = {
        "status": "warning" if punctuation_issues else "passed",
        "issues": punctuation_issues,
        "affected_segment_ids": [item["segment_id"] for item in punctuation_issues],
    }

    errors: list[str] = []
    warnings: list[str] = []
    for name, check in checks.items():
        check_status = _status(check)
        if check_status == "failed":
            errors.append(f"{name} failed")
        elif check_status == "warning":
            warnings.append(f"{name} warning")

    score = _compute_score(checks, segment_reports)
    status = _status_from_issues(errors, warnings)
    return LinguisticIntegrityReport(
        status=status,
        score_0_100=score,
        severity=_severity_from_score(score, status),
        source_language=source_lang,
        target_language=target_lang,
        checks=checks,
        segment_reports=segment_reports,
        warnings=warnings,
        errors=errors,
    )


def build_linguistic_integrity_summary(report: dict[str, Any] | LinguisticIntegrityReport, report_path: str | None = None) -> dict[str, Any]:
    payload = report.to_dict() if isinstance(report, LinguisticIntegrityReport) else report
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    script = checks.get("script") if isinstance(checks.get("script"), dict) else {}
    empty = checks.get("empty_segments") if isinstance(checks.get("empty_segments"), dict) else {}
    numbers = checks.get("numbers") if isinstance(checks.get("numbers"), dict) else {}
    names = checks.get("names_entities") if isinstance(checks.get("names_entities"), dict) else {}
    expansion = checks.get("length_ratio") if isinstance(checks.get("length_ratio"), dict) else {}
    return {
        "status": payload.get("status"),
        "score": payload.get("score_0_100"),
        "severity": payload.get("severity"),
        "scriptStatus": script.get("status"),
        "emptySegments": empty.get("empty_translated_text_count"),
        "numberWarnings": len(numbers.get("issues") or []),
        "nameWarnings": len(names.get("issues") or []),
        "expansionWarnings": expansion.get("dubbing_pressure_warnings"),
        "reportPath": report_path,
    }


def write_linguistic_integrity_report(report: dict[str, Any] | LinguisticIntegrityReport, output_path: str | Path) -> Path:
    payload = report.to_dict() if isinstance(report, LinguisticIntegrityReport) else report
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
