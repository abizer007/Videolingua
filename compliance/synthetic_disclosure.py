"""Synthetic media disclosure reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from compliance.schemas import AUDIO_DISCLOSURE_TEXT, DISCLOSURE_TEXT, env_true, write_json
from compliance.watermarking import apply_visible_disclosure


def generate_disclosure_report(
    *,
    output_path: str | Path,
    job_id: str,
    final_video_path: str | Path | None,
    compliance_dir: str | Path,
    disclosure_text: str = DISCLOSURE_TEXT,
    audio_only: bool = False,
) -> dict[str, Any]:
    visible_enabled = env_true("VIDIOLINGUA_APPLY_VISIBLE_DISCLOSURE", False)
    audio_enabled = env_true("VIDIOLINGUA_APPLY_AUDIO_DISCLOSURE", False)
    disclosed_output_path = Path(compliance_dir) / "disclosed_output.mp4"
    warnings: list[str] = []
    visible_applied = False
    if visible_enabled:
        visible_applied, visible_warnings = apply_visible_disclosure(
            input_video_path=final_video_path,
            output_video_path=disclosed_output_path,
            disclosure_text=disclosure_text,
        )
        warnings.extend(visible_warnings)
    report = {
        "job_id": job_id,
        "visible_disclosure_applied": visible_applied,
        "audio_disclosure_applied": False,
        "disclosure_text": AUDIO_DISCLOSURE_TEXT if audio_only else disclosure_text,
        "disclosed_output_path": str(disclosed_output_path) if visible_applied else None,
        "metadata_only_disclosure": not visible_applied,
        "audio_disclosure_requested": audio_enabled,
        "warnings": warnings,
        "limitations": [
            "Visible label can be removed by editing; use with provenance/fingerprints.",
            "Audio disclosure is not prepended by default because it can disturb demo timing.",
            "Metadata-only disclosure can be stripped by downstream platforms.",
        ],
    }
    write_json(output_path, report)
    return report
