"""Unicode script checks for translated text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from translation.base import normalize_language_code


@dataclass(frozen=True)
class ScriptExpectation:
    name: str
    ranges: tuple[tuple[int, int], ...]
    min_ratio: float = 0.45
    severe_min_ratio: float = 0.20


SCRIPT_EXPECTATIONS: dict[str, ScriptExpectation] = {
    "kn": ScriptExpectation("Kannada", ((0x0C80, 0x0CFF),)),
    "hi": ScriptExpectation("Devanagari", ((0x0900, 0x097F),)),
    "mr": ScriptExpectation("Devanagari", ((0x0900, 0x097F),)),
    "sa": ScriptExpectation("Devanagari", ((0x0900, 0x097F),)),
    "ne": ScriptExpectation("Devanagari", ((0x0900, 0x097F),)),
    "ta": ScriptExpectation("Tamil", ((0x0B80, 0x0BFF),)),
    "te": ScriptExpectation("Telugu", ((0x0C00, 0x0C7F),)),
    "bn": ScriptExpectation("Bengali", ((0x0980, 0x09FF),)),
    "as": ScriptExpectation("Bengali", ((0x0980, 0x09FF),)),
    "ml": ScriptExpectation("Malayalam", ((0x0D00, 0x0D7F),)),
    "gu": ScriptExpectation("Gujarati", ((0x0A80, 0x0AFF),)),
    "pa": ScriptExpectation("Gurmukhi", ((0x0A00, 0x0A7F),)),
    "or": ScriptExpectation("Odia", ((0x0B00, 0x0B7F),)),
    "ar": ScriptExpectation("Arabic", ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF))),
    "ru": ScriptExpectation("Cyrillic", ((0x0400, 0x04FF),)),
    "zh": ScriptExpectation("CJK", ((0x4E00, 0x9FFF),)),
    "ja": ScriptExpectation("Japanese", ((0x3040, 0x30FF), (0x4E00, 0x9FFF))),
    "ko": ScriptExpectation("Hangul", ((0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F))),
}


def _is_in_ranges(char: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    code = ord(char)
    return any(start <= code <= end for start, end in ranges)


def _is_letter(char: str) -> bool:
    return char.isalpha()


def roman_letter_count(text: str) -> int:
    return sum(1 for char in text or "" if ("A" <= char <= "Z") or ("a" <= char <= "z"))


def analyze_script(
    text: str,
    target_language: str,
    *,
    roman_allowlist: list[str] | None = None,
) -> dict[str, object]:
    target = normalize_language_code(target_language)
    expectation = SCRIPT_EXPECTATIONS.get(target)
    letters = [char for char in text or "" if _is_letter(char)]
    if not expectation:
        return {
            "target_language": target,
            "expected_script": None,
            "script_ratio": None,
            "english_leakage_ratio": None,
            "script_match": None,
            "severity": "not_applicable",
        }
    expected_count = sum(1 for char in letters if _is_in_ranges(char, expectation.ranges))
    roman_count = roman_letter_count(text or "")
    denominator = max(1, len(letters))
    script_ratio = expected_count / denominator
    english_leakage_ratio = roman_count / max(1, len(text or ""))
    allowlist_text = " ".join(roman_allowlist or [])
    allowlist_roman = roman_letter_count(allowlist_text)
    adjusted_roman_count = max(0, roman_count - allowlist_roman)
    adjusted_english_ratio = adjusted_roman_count / max(1, len(text or ""))
    if script_ratio >= expectation.min_ratio:
        severity = "passed"
    elif script_ratio < expectation.severe_min_ratio:
        severity = "failed"
    else:
        severity = "warning"
    return {
        "target_language": target,
        "expected_script": expectation.name,
        "script_ratio": round(script_ratio, 6),
        "english_leakage_ratio": round(english_leakage_ratio, 6),
        "adjusted_english_leakage_ratio": round(adjusted_english_ratio, 6),
        "script_match": severity == "passed",
        "severity": severity,
        "status": severity if severity in {"passed", "warning", "failed"} else "passed",
    }


def script_distribution(text: str) -> dict[str, int]:
    counts = {expectation.name: 0 for expectation in SCRIPT_EXPECTATIONS.values()}
    counts["Latin"] = 0
    counts["Other"] = 0
    for char in text or "":
        if not _is_letter(char):
            continue
        if ("A" <= char <= "Z") or ("a" <= char <= "z"):
            counts["Latin"] += 1
            continue
        matched = False
        for expectation in SCRIPT_EXPECTATIONS.values():
            if _is_in_ranges(char, expectation.ranges):
                counts[expectation.name] = counts.get(expectation.name, 0) + 1
                matched = True
                break
        if not matched:
            counts["Other"] += 1
    return {key: value for key, value in counts.items() if value}


def analyze_script_segments(
    translated_segments: list[dict[str, Any]],
    target_language: str,
    *,
    roman_allowlist: list[str] | None = None,
) -> dict[str, Any]:
    segment_reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    combined_text = " ".join(str(segment.get("text") or "") for segment in translated_segments)
    aggregate = analyze_script(combined_text, target_language, roman_allowlist=roman_allowlist)
    for index, segment in enumerate(translated_segments):
        text = str(segment.get("text") or "")
        report = analyze_script(text, target_language, roman_allowlist=roman_allowlist)
        report["segment_id"] = str(segment.get("id") or index)
        segment_reports.append(report)
        if report.get("severity") == "failed" and text.strip():
            failures.append(report)
        elif report.get("severity") == "warning" and text.strip():
            warnings.append(report)
    status = "failed" if failures else "warning" if warnings else "passed"
    return {
        "status": status,
        "target_language": normalize_language_code(target_language),
        "expected_script": aggregate.get("expected_script"),
        "aggregate": aggregate,
        "script_distribution": script_distribution(combined_text),
        "segment_reports": segment_reports,
        "failures": failures,
        "warnings": warnings,
        "affected_segment_ids": [str(item.get("segment_id")) for item in failures + warnings],
    }
