"""Generate or validate responsible AI compliance artifacts for a job folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compliance.compliance_passport import COMPLIANCE_ARTIFACTS, generate_compliance_bundle


def _resolve(path: str | Path) -> Path:
    target = Path(path)
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    return target.resolve()


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def validate_required(compliance_dir: Path) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    errors: list[str] = []
    for key, filename in COMPLIANCE_ARTIFACTS.items():
        path = compliance_dir / filename
        if key == "audit_ledger":
            if not path.is_file() or path.stat().st_size <= 0:
                missing.append(filename)
            continue
        if not path.is_file():
            missing.append(filename)
            continue
        if path.suffix.lower() == ".json" and not _load(path):
            errors.append(f"{filename} is not valid JSON.")
    provenance = _load(compliance_dir / "provenance_manifest.json")
    fingerprint = _load(compliance_dir / "fingerprint_report.json")
    passport = _load(compliance_dir / "compliance_passport.json")
    if provenance and fingerprint:
        if provenance.get("output", {}).get("sha256") and fingerprint.get("output_video_sha256"):
            if provenance["output"]["sha256"] != fingerprint["output_video_sha256"]:
                errors.append("Output SHA-256 mismatch between provenance manifest and fingerprint report.")
        if provenance.get("input", {}).get("sha256") and fingerprint.get("input_video_sha256"):
            if provenance["input"]["sha256"] != fingerprint["input_video_sha256"]:
                errors.append("Input SHA-256 mismatch between provenance manifest and fingerprint report.")
    if passport:
        required = [
            "passport_id",
            "job_id",
            "overall_status",
            "sgi_risk_level",
            "abuse_risk_status",
            "provenance_manifest_created",
            "hashes_generated",
            "audit_ledger_created",
            "safe_for_demo_export",
            "artifacts",
        ]
        for key in required:
            if key not in passport:
                errors.append(f"Passport missing required key: {key}")
    return missing, errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and validate a VideoLingua Responsible AI compliance passport.")
    parser.add_argument("--job-dir", required=True, help="Existing job folder to inspect.")
    parser.add_argument("--output", default=None, help="Optional output folder for generated compliance artifacts.")
    parser.add_argument("--mode", choices=["report_only", "strict"], default="report_only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    job_dir = _resolve(args.job_dir)
    output_dir = _resolve(args.output) if args.output else None
    if not job_dir.is_dir():
        print(f"[compliance] ERROR: job dir not found: {job_dir}", file=sys.stderr)
        return 1
    bundle = generate_compliance_bundle(
        job_dir=job_dir,
        output_dir=output_dir,
        mode=args.mode,
        final=True,
        raise_on_block=False,
    )
    compliance_dir = Path(bundle["compliance_dir"])
    missing, errors = validate_required(compliance_dir)
    passport = bundle.get("passport") or {}
    print("[compliance] validation summary")
    print(f"job_dir={job_dir}")
    print(f"compliance_dir={compliance_dir}")
    print(f"mode={args.mode}")
    print(f"passport_status={passport.get('overall_status')}")
    print(f"sgi_risk_level={passport.get('sgi_risk_level')}")
    print(f"abuse_risk_status={passport.get('abuse_risk_status')}")
    print(f"safe_for_demo_export={passport.get('safe_for_demo_export')}")
    print(f"warnings={len(passport.get('warnings') or [])}")
    print(f"errors={len(passport.get('errors') or []) + len(errors)}")
    if missing:
        print("missing=" + ", ".join(missing))
    if errors:
        print("validation_errors=" + " | ".join(errors))
    return 1 if missing or errors or (args.mode == "strict" and passport.get("overall_status") == "blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
