"""Automatic ASR evaluation layers."""

from __future__ import annotations

from typing import Any

from evaluation.quality_schema import clamp, metric, unavailable
from evaluation.text_metrics import asr_accuracy_from_wer, cer, join_segment_text, wer


def _word_confidence(segments: list[Any]) -> tuple[float | None, int]:
    scores: list[float] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        for word in segment.get("words") or []:
            if not isinstance(word, dict):
                continue
            try:
                scores.append(float(word.get("score")))
            except (TypeError, ValueError):
                continue
    if not scores:
        return None, 0
    return sum(scores) / len(scores), len(scores)


def evaluate_asr(context: dict[str, Any]) -> dict[str, Any]:
    data = context.get("asr_data") if isinstance(context.get("asr_data"), dict) else {}
    segments = data.get("segments") if isinstance(data.get("segments"), list) else []
    hypothesis = join_segment_text(segments)
    segment_count = len([segment for segment in segments if isinstance(segment, dict)])
    empty_count = sum(1 for segment in segments if isinstance(segment, dict) and not str(segment.get("text") or "").strip())
    empty_ratio = empty_count / segment_count if segment_count else 1.0
    avg_confidence, word_count = _word_confidence(segments)

    true_reference = str(context.get("true_transcript") or "").strip()
    if true_reference:
        wer_value = wer(true_reference, hypothesis)
        cer_value = cer(true_reference, hypothesis)
        accuracy = asr_accuracy_from_wer(wer_value)
        method = "extracted_reference_transcript" if context.get("true_transcript_source") else "reference_transcript"
        return {
            "display_label": "ASR accuracy",
            "score": metric(
                status="computed",
                value=round(accuracy * 100.0, 3),
                unit="percent",
                method=method,
                confidence="high",
                source=str(context.get("true_transcript_source") or "evaluation_reference_transcript"),
                explanation="Computed against a real transcript/reference text available with the job.",
                reference_type="true_reference",
            ),
            "asr_accuracy": metric(
                status="computed",
                value=round(accuracy, 6),
                unit="ratio",
                method=method,
                confidence="high",
                source=str(context.get("true_transcript_source") or "evaluation_reference_transcript"),
                explanation="ASR accuracy is max(0, 1 - WER) against a true reference transcript.",
                reference_type="true_reference",
            ),
            "wer": metric(
                status="computed",
                value=round(wer_value, 6),
                unit="ratio",
                method=method,
                confidence="high",
                source=str(context.get("true_transcript_source") or "evaluation_reference_transcript"),
                explanation="Word error rate against a true reference transcript.",
                reference_type="true_reference",
            ),
            "cer": metric(
                status="computed",
                value=round(cer_value, 6),
                unit="ratio",
                method=method,
                confidence="high",
                source=str(context.get("true_transcript_source") or "evaluation_reference_transcript"),
                explanation="Character error rate against a true reference transcript.",
                reference_type="true_reference",
            ),
            "signals": {"segment_count": segment_count, "empty_segment_ratio": round(empty_ratio, 6), "word_confidence_count": word_count},
        }

    consensus = context.get("auto_consensus_transcript")
    if isinstance(consensus, dict) and consensus.get("text"):
        wer_value = wer(str(consensus["text"]), hypothesis)
        cer_value = cer(str(consensus["text"]), hypothesis)
        accuracy = asr_accuracy_from_wer(wer_value)
        return {
            "display_label": "ASR agreement",
            "score": metric(
                status="computed",
                value=round(accuracy * 100.0, 3),
                unit="percent",
                method="consensus_reference",
                confidence="medium",
                source="pipeline_asr_vs_auto_consensus_transcript",
                explanation="Computed against an automatically selected consensus transcript, not a human transcript.",
                reference_type="auto_reference",
            ),
            "asr_accuracy": metric(
                status="computed",
                value=round(accuracy, 6),
                unit="ratio",
                method="consensus_reference",
                confidence="medium",
                source="pipeline_asr_vs_auto_consensus_transcript",
                explanation="Agreement accuracy is max(0, 1 - WER) against an automatic consensus transcript.",
                reference_type="auto_reference",
            ),
            "wer": metric(
                status="computed",
                value=round(wer_value, 6),
                unit="ratio",
                method="consensus_reference",
                confidence="medium",
                source=str(consensus.get("path") or "auto_consensus_transcript"),
                explanation="WER against an automatic consensus transcript.",
                reference_type="auto_reference",
            ),
            "cer": metric(
                status="computed",
                value=round(cer_value, 6),
                unit="ratio",
                method="consensus_reference",
                confidence="medium",
                source=str(consensus.get("path") or "auto_consensus_transcript"),
                explanation="CER against an automatic consensus transcript.",
                reference_type="auto_reference",
            ),
            "signals": {"segment_count": segment_count, "empty_segment_ratio": round(empty_ratio, 6), "word_confidence_count": word_count},
        }

    structural_score = (1.0 - empty_ratio) if segment_count else 0.0
    length_score = 1.0 if len(hypothesis.strip()) >= 20 else clamp(len(hypothesis.strip()) / 20.0)
    if avg_confidence is not None:
        reliability = clamp((0.68 * avg_confidence) + (0.22 * structural_score) + (0.10 * length_score))
    else:
        # Without word-level confidence, keep this as a low-confidence
        # structural proxy instead of treating non-empty text as accuracy.
        reliability = clamp(((0.70 * structural_score) + (0.30 * length_score)) * 0.65)
    return {
        "display_label": "Transcript reliability",
        "score": metric(
            status="proxy_computed",
            value=round(reliability * 100.0, 3),
            unit="percent",
            method="asr_structural_confidence_proxy",
            confidence="medium" if avg_confidence is not None else "low",
            source="pipeline_asr_segments_and_word_scores",
            explanation="No human transcript or independent ASR consensus was found, so this is an artifact-derived transcript reliability proxy.",
            reference_type="proxy",
            details={
                "avg_word_confidence": round(avg_confidence, 6) if avg_confidence is not None else None,
                "empty_segment_ratio": round(empty_ratio, 6),
                "word_confidence_count": word_count,
            },
        ),
        "asr_accuracy": metric(
            status="proxy_computed",
            value=round(reliability, 6),
            unit="ratio",
            method="asr_structural_confidence_proxy",
            confidence="medium" if avg_confidence is not None else "low",
            source="pipeline_asr_segments_and_word_scores",
            explanation="This is not human-ground-truth ASR accuracy; it is a transcript reliability proxy from ASR confidence and structure.",
            reference_type="proxy",
        ),
        "wer": unavailable("requires_reference_or_consensus", "WER requires a true transcript or independent ASR consensus."),
        "cer": unavailable("requires_reference_or_consensus", "CER requires a true transcript or independent ASR consensus."),
        "signals": {"segment_count": segment_count, "empty_segment_ratio": round(empty_ratio, 6), "word_confidence_count": word_count},
    }
