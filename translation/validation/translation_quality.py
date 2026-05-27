"""Context-preserving translation QA and post-edit reporting."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any
import re

from translation.base import normalize_language_code
from translation.cache.translation_memory import append_memory_entry, build_memory_key
from translation.validation.context_window import analyze_context_window
from translation.validation.entity_preservation import (
    extract_entities,
    has_sentence_end_punctuation,
    missing_entities,
    missing_numbers,
)
from translation.validation.glossary import check_glossary_terms, glossary_hash, preserved_terms
from translation.validation.script_checks import analyze_script
from translation.validation.translation_memory import analyze_memory_hits


DEFAULT_MIN_RATIO = 0.25
DEFAULT_MAX_RATIO = 4.0


@dataclass
class TranslationQAReport:
    status: str
    source_language: str
    target_language: str
    segment_count_source: int
    segment_count_translated: int
    segment_count_match: bool
    checks: dict[str, Any] = field(default_factory=dict)
    segment_reports: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    glossary_applied: bool = False
    translation_memory_hits: int = 0
    post_edit_used: bool = False
    post_edit_engine: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "segment_count_source": self.segment_count_source,
            "segment_count_translated": self.segment_count_translated,
            "segment_count_match": self.segment_count_match,
            "checks": self.checks,
            "segment_reports": self.segment_reports,
            "warnings": self.warnings,
            "errors": self.errors,
            "glossary_applied": self.glossary_applied,
            "translation_memory_hits": self.translation_memory_hits,
            "post_edit_used": self.post_edit_used,
            "post_edit_engine": self.post_edit_engine,
        }


def analyze_translation_segments(
    source_segments: list[Any],
    translated_segments: list[Any],
    source_language: str,
    target_language: str,
    glossary: dict[str, Any] | None = None,
    context_window_size: int = 2,
    enable_post_edit: bool = False,
    post_edit_engine: str | None = None,
    *,
    translation_engine: str | None = None,
    domain: str | None = None,
    update_memory: bool = False,
    memory_path: str | None = None,
    min_expansion_ratio: float = DEFAULT_MIN_RATIO,
    max_expansion_ratio: float = DEFAULT_MAX_RATIO,
) -> TranslationQAReport:
    source_lang = normalize_language_code(source_language)
    target_lang = normalize_language_code(target_language)
    source = [_segment_dict(segment, index) for index, segment in enumerate(source_segments or [])]
    translated = [_segment_dict(segment, index) for index, segment in enumerate(translated_segments or [])]
    preserved = preserved_terms(glossary)
    g_hash = glossary_hash(glossary)

    errors: list[str] = []
    warnings: list[str] = []
    segment_reports: list[dict[str, Any]] = []

    if len(source) != len(translated):
        errors.append(f"Segment count mismatch: source={len(source)} translated={len(translated)}")

    empty_ids: list[str] = []
    expansion_warnings: list[dict[str, Any]] = []
    number_issues: list[dict[str, Any]] = []
    entity_issues: list[dict[str, Any]] = []
    glossary_issues: list[dict[str, Any]] = []
    punctuation_warnings: list[dict[str, Any]] = []
    script_failures: list[dict[str, Any]] = []
    script_warnings: list[dict[str, Any]] = []
    repetition_warnings: list[dict[str, Any]] = []

    for index, source_segment in enumerate(source):
        translated_segment = translated[index] if index < len(translated) else {"id": source_segment["id"], "text": ""}
        source_text = str(source_segment.get("text") or "")
        translated_text = str(translated_segment.get("text") or "")
        segment_id = str(source_segment.get("id") if source_segment.get("id") is not None else index)
        source_chars = len(source_text.strip())
        translated_chars = len(translated_text.strip())
        ratio = translated_chars / max(1, source_chars)
        report = {
            "segment_id": segment_id,
            "source_chars": source_chars,
            "translated_chars": translated_chars,
            "expansion_ratio": round(ratio, 6),
            "warnings": [],
            "errors": [],
        }

        if source_text.strip() and not translated_text.strip():
            empty_ids.append(segment_id)
            report["errors"].append("empty_translation")

        if source_text.strip() and translated_text.strip() and (ratio < min_expansion_ratio or ratio > max_expansion_ratio):
            item = {"segment_id": segment_id, "ratio": round(ratio, 6)}
            expansion_warnings.append(item)
            report["warnings"].append("expansion_ratio_anomaly")

        missing_nums = missing_numbers(source_text, translated_text)
        if missing_nums:
            item = {"segment_id": segment_id, "missing": missing_nums}
            number_issues.append(item)
            report["warnings"].append("number_preservation")

        missing_ents = missing_entities(source_text, translated_text, preserved)
        if missing_ents:
            item = {"segment_id": segment_id, "missing": missing_ents}
            entity_issues.append(item)
            report["warnings"].append("entity_preservation")

        term_issues = check_glossary_terms(source_text, translated_text, glossary)
        if term_issues:
            glossary_issues.extend({"segment_id": segment_id, **issue} for issue in term_issues)
            report["warnings"].append("glossary_preservation")

        script = analyze_script(translated_text, target_lang, roman_allowlist=preserved + extract_entities(source_text))
        report["script"] = script
        if script.get("severity") == "failed" and translated_text.strip():
            item = {"segment_id": segment_id, **script}
            script_failures.append(item)
            report["errors"].append("script_mismatch")
        elif script.get("severity") == "warning":
            item = {"segment_id": segment_id, **script}
            script_warnings.append(item)
            report["warnings"].append("script_mismatch")

        if has_sentence_end_punctuation(source_text) and not has_sentence_end_punctuation(translated_text):
            item = {"segment_id": segment_id, "reason": "source ended with sentence punctuation but translation did not"}
            punctuation_warnings.append(item)
            report["warnings"].append("sentence_boundary")

        repeated = _repetition_issue(translated_text)
        if repeated:
            item = {"segment_id": segment_id, **repeated}
            repetition_warnings.append(item)
            report["warnings"].append("repetition")

        segment_reports.append(report)

    duplicate_translation_warnings = _duplicate_translation_warnings(source, translated)
    repetition_warnings.extend(duplicate_translation_warnings)

    if empty_ids:
        errors.append(f"Empty translations for non-empty source segment(s): {', '.join(empty_ids)}")
    if script_failures:
        errors.append(f"Severe script mismatch in {len(script_failures)} translated segment(s)")
    if expansion_warnings:
        warnings.append(f"Expansion ratio anomaly in {len(expansion_warnings)} segment(s)")
    if number_issues:
        warnings.append(f"Number preservation warning in {len(number_issues)} segment(s)")
    if entity_issues:
        warnings.append(f"Entity preservation warning in {len(entity_issues)} segment(s)")
    if glossary_issues:
        warnings.append(f"Glossary preservation warning in {len(glossary_issues)} segment(s)")
    if script_warnings:
        warnings.append(f"Script ratio warning in {len(script_warnings)} segment(s)")
    if punctuation_warnings:
        warnings.append(f"Sentence-boundary punctuation warning in {len(punctuation_warnings)} segment(s)")
    if repetition_warnings:
        warnings.append(f"Repetition warning in {len(repetition_warnings)} case(s)")

    context = analyze_context_window(source, translated, window_size=context_window_size, glossary_terms=preserved)
    if context.get("warning_count"):
        warnings.append(f"Context-window warning in {context.get('warning_count')} case(s)")

    memory = analyze_memory_hits(
        source,
        translated,
        source_language=source_lang,
        target_language=target_lang,
        glossary_hash=g_hash,
        translation_engine=translation_engine,
        domain=domain or (glossary or {}).get("domain"),
        memory_path=memory_path,
    )
    if memory.get("consistency_warning_count"):
        warnings.append(f"Translation memory consistency warning in {memory.get('consistency_warning_count')} segment(s)")

    post_edit = _post_edit_status(enable_post_edit, post_edit_engine)
    if post_edit.get("warning"):
        warnings.append(str(post_edit["warning"]))

    status = "failed" if errors else "warning" if warnings else "passed"

    checks = {
        "empty_translation": {"status": "failed" if empty_ids else "passed", "count": len(empty_ids), "segment_ids": empty_ids},
        "segment_count_alignment": {"status": "passed" if len(source) == len(translated) else "failed"},
        "expansion_ratio": {
            "status": "warning" if expansion_warnings else "passed",
            "min_ratio": min_expansion_ratio,
            "max_ratio": max_expansion_ratio,
            "warnings": expansion_warnings,
        },
        "repetition": {"status": "warning" if repetition_warnings else "passed", "warnings": repetition_warnings},
        "number_preservation": {"status": "warning" if number_issues else "passed", "issues": number_issues},
        "entity_preservation": {"status": "warning" if entity_issues else "passed", "issues": entity_issues},
        "glossary": {
            "status": "warning" if glossary_issues else "passed",
            "applied": bool(glossary),
            "domain": (glossary or {}).get("domain") if isinstance(glossary, dict) else None,
            "issues": glossary_issues,
        },
        "script": {
            "status": "failed" if script_failures else "warning" if script_warnings else "passed",
            "failures": script_failures,
            "warnings": script_warnings,
        },
        "sentence_boundary": {"status": "warning" if punctuation_warnings else "passed", "warnings": punctuation_warnings},
        "context_window": context,
        "translation_memory": memory,
        "post_edit": post_edit,
    }

    report = TranslationQAReport(
        status=status,
        source_language=source_lang,
        target_language=target_lang,
        segment_count_source=len(source),
        segment_count_translated=len(translated),
        segment_count_match=len(source) == len(translated),
        checks=checks,
        segment_reports=segment_reports,
        warnings=warnings,
        errors=errors,
        glossary_applied=bool(glossary),
        translation_memory_hits=int(memory.get("hits") or 0),
        post_edit_used=bool(post_edit.get("used")),
        post_edit_engine=post_edit.get("engine"),
    )

    if update_memory:
        _append_memory_entries(report, source, translated, source_lang, target_lang, translation_engine, g_hash, domain or (glossary or {}).get("domain"), memory_path)

    return report


def build_translation_qa_summary(report: dict[str, Any] | TranslationQAReport, report_path: str | None = None) -> dict[str, Any]:
    payload = report.to_dict() if isinstance(report, TranslationQAReport) else report
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    script = checks.get("script") if isinstance(checks.get("script"), dict) else {}
    return {
        "status": payload.get("status"),
        "checksPassed": sum(1 for value in checks.values() if isinstance(value, dict) and value.get("status") == "passed"),
        "warningsCount": len(payload.get("warnings") or []),
        "errorsCount": len(payload.get("errors") or []),
        "emptySegments": (checks.get("empty_translation") or {}).get("count") if isinstance(checks.get("empty_translation"), dict) else None,
        "scriptMatch": True if script.get("status") == "passed" else False if script.get("status") in {"failed", "warning"} else None,
        "numberIssues": len((checks.get("number_preservation") or {}).get("issues") or []) if isinstance(checks.get("number_preservation"), dict) else None,
        "entityIssues": len((checks.get("entity_preservation") or {}).get("issues") or []) if isinstance(checks.get("entity_preservation"), dict) else None,
        "expansionRatioWarnings": len((checks.get("expansion_ratio") or {}).get("warnings") or []) if isinstance(checks.get("expansion_ratio"), dict) else None,
        "glossaryApplied": bool(payload.get("glossary_applied")),
        "translationMemoryHits": int(payload.get("translation_memory_hits") or 0),
        "postEditUsed": bool(payload.get("post_edit_used")),
        "postEditEngine": payload.get("post_edit_engine"),
        "reportPath": report_path,
    }


def _segment_dict(segment: Any, index: int) -> dict[str, Any]:
    if isinstance(segment, dict):
        out = dict(segment)
        out.setdefault("id", str(index))
        out.setdefault("text", "")
        return out
    return {"id": str(index), "text": str(segment or "")}


def _repetition_issue(text: str) -> dict[str, Any] | None:
    clean = (text or "").strip()
    if not clean:
        return None
    tokens = re.findall(r"\w+|[^\w\s]", clean, flags=re.UNICODE)
    if len(tokens) >= 6:
        counts = Counter(token.lower() for token in tokens)
        token, count = counts.most_common(1)[0]
        if count >= 5 and count / max(1, len(tokens)) >= 0.45:
            return {"reason": "excessive repeated token", "token": token, "count": count}
    if re.search(r"([.!?।,])\1{3,}", clean):
        return {"reason": "excessive repeated punctuation"}
    return None


def _duplicate_translation_warnings(source: list[dict[str, Any]], translated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: dict[str, list[int]] = {}
    for index, segment in enumerate(translated):
        text = str(segment.get("text") or "").strip()
        if len(text) >= 3:
            pairs.setdefault(text, []).append(index)
    warnings: list[dict[str, Any]] = []
    for text, indexes in pairs.items():
        if len(indexes) < 3:
            continue
        source_texts = {str(source[index].get("text") or "").strip() for index in indexes if index < len(source)}
        if len(source_texts) > 1:
            warnings.append({"reason": "same translated segment repeated across multiple source segments", "count": len(indexes)})
    return warnings


def _post_edit_status(enable_post_edit: bool, post_edit_engine: str | None) -> dict[str, Any]:
    if not enable_post_edit:
        return {"enabled": False, "used": False, "engine": None, "status": "disabled"}
    return {
        "enabled": True,
        "used": False,
        "engine": post_edit_engine,
        "status": "skipped",
        "warning": "LLM post-edit was requested but no post-edit engine is wired in this phase.",
    }


def _append_memory_entries(
    report: TranslationQAReport,
    source: list[dict[str, Any]],
    translated: list[dict[str, Any]],
    source_language: str,
    target_language: str,
    translation_engine: str | None,
    g_hash: str | None,
    domain: str | None,
    memory_path: str | None,
) -> None:
    if report.status == "failed":
        return
    for index, source_segment in enumerate(source):
        if index >= len(translated):
            continue
        source_text = str(source_segment.get("text") or "")
        translated_text = str(translated[index].get("text") or "")
        if not source_text.strip() or not translated_text.strip():
            continue
        key = build_memory_key(
            source_language=source_language,
            target_language=target_language,
            source_text=source_text,
            glossary_hash=g_hash,
            translation_engine=translation_engine,
            domain=domain,
        )
        append_memory_entry(
            key=key,
            source_language=source_language,
            target_language=target_language,
            source_text=source_text,
            translated_text=translated_text,
            quality_status=report.status,
            translation_engine=translation_engine,
            glossary_hash=g_hash,
            domain=domain,
            path=memory_path,
        )
