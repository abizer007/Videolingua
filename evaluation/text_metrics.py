"""Dependency-light text evaluation metrics."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def word_tokens(text: str) -> list[str]:
    return normalize_text(text).split()


def char_tokens(text: str) -> list[str]:
    return list(normalize_text(text).replace(" ", ""))


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    if not reference:
        return len(hypothesis)
    if not hypothesis:
        return len(reference)
    previous = list(range(len(hypothesis) + 1))
    for i, ref_item in enumerate(reference, start=1):
        current = [i]
        for j, hyp_item in enumerate(hypothesis, start=1):
            cost = 0 if ref_item == hyp_item else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref = word_tokens(reference)
    hyp = word_tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / float(len(ref))


def cer(reference: str, hypothesis: str) -> float:
    ref = char_tokens(reference)
    hyp = char_tokens(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / float(len(ref))


def asr_accuracy_from_wer(wer_value: float) -> float:
    return max(0.0, 1.0 - float(wer_value))


def _ngrams(tokens: list[str], n: int) -> Counter[tuple[str, ...]]:
    if n <= 0 or len(tokens) < n:
        return Counter()
    return Counter(tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1))


def bleu_lite(reference: str, hypothesis: str, max_order: int = 4) -> float:
    """Small sentence-level BLEU implementation with add-one smoothing.

    This is intentionally labeled BLEU-lite and should not be presented as
    SacreBLEU or corpus BLEU.
    """
    ref_tokens = word_tokens(reference)
    hyp_tokens = word_tokens(hypothesis)
    if not ref_tokens and not hyp_tokens:
        return 1.0
    if not ref_tokens or not hyp_tokens:
        return 0.0

    precisions: list[float] = []
    for order in range(1, max_order + 1):
        ref_counts = _ngrams(ref_tokens, order)
        hyp_counts = _ngrams(hyp_tokens, order)
        overlap = sum((hyp_counts & ref_counts).values())
        total = sum(hyp_counts.values())
        precisions.append((overlap + 1.0) / (total + 1.0))

    log_precision = sum(math.log(p) for p in precisions) / max_order
    brevity_penalty = 1.0
    if len(hyp_tokens) < len(ref_tokens):
        brevity_penalty = math.exp(1.0 - (len(ref_tokens) / max(1, len(hyp_tokens))))
    return max(0.0, min(1.0, brevity_penalty * math.exp(log_precision)))


def _char_ngrams(text: str, n: int) -> Counter[str]:
    compact = normalize_text(text)
    if len(compact) < n:
        return Counter()
    return Counter(compact[index : index + n] for index in range(len(compact) - n + 1))


def chrf_lite(reference: str, hypothesis: str, max_order: int = 6, beta: float = 2.0) -> float:
    """Small chrF-style character n-gram F-score."""
    if not normalize_text(reference) and not normalize_text(hypothesis):
        return 1.0
    if not normalize_text(reference) or not normalize_text(hypothesis):
        return 0.0

    precisions: list[float] = []
    recalls: list[float] = []
    for order in range(1, max_order + 1):
        ref_counts = _char_ngrams(reference, order)
        hyp_counts = _char_ngrams(hypothesis, order)
        overlap = sum((hyp_counts & ref_counts).values())
        hyp_total = sum(hyp_counts.values())
        ref_total = sum(ref_counts.values())
        if hyp_total:
            precisions.append(overlap / hyp_total)
        if ref_total:
            recalls.append(overlap / ref_total)

    precision = sum(precisions) / len(precisions) if precisions else 0.0
    recall = sum(recalls) / len(recalls) if recalls else 0.0
    if precision <= 0.0 and recall <= 0.0:
        return 0.0
    beta_sq = beta * beta
    return (1.0 + beta_sq) * precision * recall / max(1e-12, beta_sq * precision + recall)


def join_segment_text(segments: Iterable[dict]) -> str:
    return " ".join(str(segment.get("text") or "").strip() for segment in segments if str(segment.get("text") or "").strip())

