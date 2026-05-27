"""Conservative first-pass rule-based abuse and impersonation checks."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from compliance.schemas import write_json


CHECK_PATTERNS: dict[str, list[str]] = {
    "impersonation": ["impersonate", "pretend to be", "as the ceo", "as prime minister", "as police", "deepfake"],
    "fake_emergency_public_safety": ["evacuate immediately", "bomb", "terror", "emergency order", "public safety alert"],
    "financial_transfer_fraud": ["wire transfer", "bank account", "send money", "urgent payment", "gift card", "ceo fraud"],
    "government_certificate_order": ["government order", "certificate", "official notice", "court order", "police order"],
    "election_misinformation": ["vote twice", "polling station closed", "election fraud", "ballot", "candidate withdrew"],
    "non_consensual_intimate": ["nude", "sexual", "intimate image", "revenge porn", "morphed explicit"],
    "minors_child_exploitation": ["child sexual", "minor nude", "csam", "cseam", "underage sexual"],
    "forged_documents": ["fake passport", "fake id", "forged", "counterfeit certificate", "fake document"],
    "violence_public_order_deception": ["riot", "attack now", "kill", "lynch", "violent protest"],
}


HIGH_RISK_CHECKS = {
    "non_consensual_intimate",
    "minors_child_exploitation",
    "financial_transfer_fraud",
    "fake_emergency_public_safety",
    "election_misinformation",
}


def _contains(text: str, pattern: str) -> bool:
    return re.search(r"\b" + re.escape(pattern).replace(r"\ ", r"\s+") + r"\b", text, re.IGNORECASE) is not None


def check_abuse_risk(
    *,
    output_path: str | Path,
    filename: str = "",
    target_language: str | None = None,
    transcript_text: str = "",
    translated_text: str = "",
    user_purpose: str | None = None,
    consent_fields: dict[str, Any] | None = None,
    mode: str = "report_only",
) -> dict[str, Any]:
    del target_language, consent_fields
    haystack = " ".join([filename or "", transcript_text or "", translated_text or "", user_purpose or ""]).lower()
    checks: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    blocked_reasons: list[str] = []
    high_hits = 0
    medium_hits = 0
    for name, patterns in CHECK_PATTERNS.items():
        matched = [pattern for pattern in patterns if _contains(haystack, pattern)]
        checks[name] = {"matched": bool(matched), "matched_terms": matched}
        if matched:
            if name in HIGH_RISK_CHECKS:
                high_hits += 1
                blocked_reasons.append(f"High-risk first-pass abuse pattern matched: {name}.")
            else:
                medium_hits += 1
                warnings.append(f"Potential misuse pattern matched: {name}.")
    risk_level = "high" if high_hits else "medium" if medium_hits else "low"
    status = "blocked" if risk_level == "high" and mode == "strict" else "warning" if risk_level in {"medium", "high"} else "passed"
    if risk_level == "high" and mode != "strict":
        warnings.append("High-risk terms were detected, but report_only mode does not block the pipeline.")
    report = {
        "status": status,
        "risk_level": risk_level,
        "mode": mode,
        "checker_type": "first_pass_rule_based_guardrail",
        "checks": checks,
        "warnings": warnings,
        "blocked_reasons": blocked_reasons if status == "blocked" else [],
        "human_review_recommended": risk_level in {"medium", "high"},
        "limitations": [
            "Keyword rules can miss harmful content and can over-flag benign content.",
            "This report is not a robust abuse detector.",
        ],
    }
    write_json(output_path, report)
    return report
