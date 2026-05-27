"""Automatic translation evaluation layers."""

from __future__ import annotations

import unicodedata
from typing import Any

from evaluation.quality_schema import clamp, metric, unavailable
from evaluation.text_metrics import bleu_lite, chrf_lite, join_segment_text


SCRIPT_RANGES = {
    "kn": ((0x0C80, 0x0CFF),),
    "hi": ((0x0900, 0x097F),),
    "mr": ((0x0900, 0x097F),),
    "ne": ((0x0900, 0x097F),),
    "bn": ((0x0980, 0x09FF),),
    "pa": ((0x0A00, 0x0A7F),),
    "gu": ((0x0A80, 0x0AFF),),
    "or": ((0x0B00, 0x0B7F),),
    "od": ((0x0B00, 0x0B7F),),
    "ta": ((0x0B80, 0x0BFF),),
    "te": ((0x0C00, 0x0C7F),),
    "ml": ((0x0D00, 0x0D7F),),
}


def _target_language(data: dict[str, Any]) -> str:
    return str(data.get("language") or data.get("target_language") or "").lower().replace("_", "-").split("-")[0]


def _letter_chars(text: str) -> list[str]:
    return [char for char in text if unicodedata.category(char).startswith("L")]


def _script_ratio(text: str, target_language: str) -> float:
    letters = _letter_chars(text)
    if not letters:
        return 0.0
    ranges = SCRIPT_RANGES.get(target_language)
    if ranges:
        matching = 0
        for char in letters:
            code = ord(char)
            if any(start <= code <= end for start, end in ranges):
                matching += 1
        return matching / len(letters)
    latin = sum(1 for char in letters if "LATIN" in unicodedata.name(char, ""))
    return latin / len(letters)


def _structural_scores(source_segments: list[Any], translated_segments: list[Any], target_language: str) -> dict[str, Any]:
    source_count = len([segment for segment in source_segments if isinstance(segment, dict)])
    translated_count = len([segment for segment in translated_segments if isinstance(segment, dict)])
    translated_text = join_segment_text(translated_segments)
    source_text = join_segment_text(source_segments)
    empty_count = sum(1 for segment in translated_segments if isinstance(segment, dict) and not str(segment.get("text") or "").strip())
    segment_score = 1.0 if source_count == translated_count else 1.0 - min(1.0, abs(source_count - translated_count) / max(source_count, translated_count, 1))
    empty_score = 1.0 - (empty_count / translated_count if translated_count else 1.0)
    script_score = _script_ratio(translated_text, target_language)
    expansion_ratio = len(translated_text) / max(1, len(source_text))
    if 0.45 <= expansion_ratio <= 2.2:
        expansion_score = 1.0
    else:
        expansion_score = clamp(1.0 - min(abs(expansion_ratio - 1.15), 2.0) / 2.0)
    suspicious_count = 0
    for source_segment, translated_segment in zip(source_segments, translated_segments):
        if not isinstance(source_segment, dict) or not isinstance(translated_segment, dict):
            continue
        source_len = max(1, len(str(source_segment.get("text") or "").strip()))
        translated_len = len(str(translated_segment.get("text") or "").strip())
        if translated_len / source_len > 2.5:
            suspicious_count += 1
    suspicious_score = 1.0 - (suspicious_count / translated_count if translated_count else 1.0)
    return {
        "source_segment_count": source_count,
        "translated_segment_count": translated_count,
        "segment_score": segment_score,
        "empty_segment_count": empty_count,
        "empty_score": empty_score,
        "target_script_match": script_score,
        "expansion_ratio": expansion_ratio,
        "expansion_score": expansion_score,
        "suspiciously_long_segment_count": suspicious_count,
        "suspicious_score": suspicious_score,
        "translated_text": translated_text,
    }


def evaluate_translation(context: dict[str, Any]) -> dict[str, Any]:
    asr_data = context.get("asr_data") if isinstance(context.get("asr_data"), dict) else {}
    translation_data = context.get("translation_data") if isinstance(context.get("translation_data"), dict) else {}
    source_segments = asr_data.get("segments") if isinstance(asr_data.get("segments"), list) else []
    translated_segments = translation_data.get("segments") if isinstance(translation_data.get("segments"), list) else []
    target_language = _target_language(translation_data)
    signals = _structural_scores(source_segments, translated_segments, target_language)
    hypothesis = signals["translated_text"]
    reference = str(context.get("reference_translation") or "").strip()
    auto_reference = context.get("auto_reference_translation")

    if reference:
        bleu = bleu_lite(reference, hypothesis)
        chrf = chrf_lite(reference, hypothesis)
        score = clamp((bleu * 0.48) + (chrf * 0.52))
        source = str(context.get("reference_translation_source") or "evaluation_reference_translation")
        return {
            "display_label": "BLEU / chrF",
            "score": metric(
                status="computed",
                value=round(score * 100.0, 3),
                unit="percent",
                method="reference_translation",
                confidence="high",
                source=source,
                explanation="Translation score computed with BLEU-lite and chrF-lite against a true reference translation.",
                reference_type="true_reference",
            ),
            "bleu": metric(status="computed", value=round(bleu, 6), unit="ratio", method="reference_translation", confidence="high", source=source, explanation="BLEU-lite against a true reference translation.", reference_type="true_reference"),
            "chrf": metric(status="computed", value=round(chrf, 6), unit="ratio", method="reference_translation", confidence="high", source=source, explanation="chrF-lite against a true reference translation.", reference_type="true_reference"),
            "round_trip_consistency": unavailable("reverse_translation_not_available", "No configured reverse translation evaluator was available."),
            "signals": {key: round(value, 6) if isinstance(value, float) else value for key, value in signals.items() if key != "translated_text"},
        }

    if isinstance(auto_reference, dict) and auto_reference.get("text"):
        bleu = bleu_lite(str(auto_reference["text"]), hypothesis)
        chrf = chrf_lite(str(auto_reference["text"]), hypothesis)
        score = clamp((bleu * 0.45) + (chrf * 0.45) + (signals["target_script_match"] * 0.10))
        source = f"{auto_reference.get('path')}:{auto_reference.get('field')}"
        return {
            "display_label": "BLEU vs auto-reference / chrF vs auto-reference",
            "score": metric(status="computed", value=round(score * 100.0, 3), unit="percent", method="auto_reference_translation", confidence="medium", source=source, explanation="Translation score computed against an independent automatic evaluator translation, not a human reference.", reference_type="auto_reference"),
            "bleu": metric(status="computed", value=round(bleu, 6), unit="ratio", method="auto_reference_translation", confidence="medium", source=source, explanation="BLEU-lite against an automatic reference translation.", reference_type="auto_reference"),
            "chrf": metric(status="computed", value=round(chrf, 6), unit="ratio", method="auto_reference_translation", confidence="medium", source=source, explanation="chrF-lite against an automatic reference translation.", reference_type="auto_reference"),
            "round_trip_consistency": unavailable("reverse_translation_not_available", "No configured reverse translation evaluator was available."),
            "signals": {key: round(value, 6) if isinstance(value, float) else value for key, value in signals.items() if key != "translated_text"},
        }

    proxy = clamp(
        (signals["segment_score"] * 0.24)
        + (signals["empty_score"] * 0.24)
        + (signals["target_script_match"] * 0.24)
        + (signals["expansion_score"] * 0.18)
        + (signals["suspicious_score"] * 0.10)
    )
    return {
        "display_label": "Translation quality estimate",
        "score": metric(
            status="proxy_computed",
            value=round(proxy * 100.0, 3),
            unit="percent",
            method="artifact_translation_quality_proxy",
            confidence="medium",
            source="translated_segments_script_and_length_checks",
            explanation="No human or independent translation reference was found, so this score comes from script, segment alignment, empty output, and length-ratio checks.",
            reference_type="proxy",
        ),
        "bleu": unavailable("requires_reference_or_independent_evaluator", "BLEU requires a true reference translation or independent auto-reference."),
        "chrf": unavailable("requires_reference_or_independent_evaluator", "chrF requires a true reference translation or independent auto-reference."),
        "round_trip_consistency": unavailable("reverse_translation_not_available", "No configured reverse translation evaluator was available."),
        "signals": {key: round(value, 6) if isinstance(value, float) else value for key, value in signals.items() if key != "translated_text"},
    }
