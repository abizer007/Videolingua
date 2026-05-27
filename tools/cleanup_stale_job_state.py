"""Dry-run-first cleanup for stale VideoLingua temp job state."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_PATHS = {
    PROJECT_ROOT / "models" / "xtts_v2",
    PROJECT_ROOT / "outputs" / "french_official_test",
    PROJECT_ROOT / "outputs" / "kannada_sarvam_practical_test_clipfix",
    PROJECT_ROOT / "outputs" / "multilingual_exports" / "official_fr_kn_test",
}
ALLOWED_ROOTS = {
    PROJECT_ROOT / "jobs",
    PROJECT_ROOT / "outputs" / "validation",
}


def _is_under(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    root_resolved = root.resolve()
    return resolved == root_resolved or str(resolved).startswith(str(root_resolved) + "\\") or str(resolved).startswith(str(root_resolved) + "/")


def _is_protected(path: Path) -> bool:
    return any(_is_under(path, protected) for protected in PROTECTED_PATHS)


def discover_candidates() -> list[Path]:
    candidates: list[Path] = []
    validation_tmp = PROJECT_ROOT / "outputs" / "validation" / "indictrans2_worker_tmp"
    if validation_tmp.is_dir():
        candidates.extend(path for path in validation_tmp.iterdir() if path.is_dir())
    jobs_dir = PROJECT_ROOT / "jobs"
    if jobs_dir.is_dir():
        candidates.extend(jobs_dir.glob("*/tmp/indictrans2_worker/*"))
    return sorted({path.resolve() for path in candidates if path.exists()})


def clean(apply: bool) -> dict[str, Any]:
    actions = []
    for candidate in discover_candidates():
        allowed = any(_is_under(candidate, root) for root in ALLOWED_ROOTS)
        protected = _is_protected(candidate)
        action = {
            "path": str(candidate),
            "allowed": allowed,
            "protected": protected,
            "deleted": False,
        }
        if apply and allowed and not protected:
            shutil.rmtree(candidate, ignore_errors=True)
            action["deleted"] = not candidate.exists()
        actions.append(action)
    return {"apply": apply, "actions": actions, "deleted_count": sum(1 for item in actions if item["deleted"])}


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean stale VideoLingua temp job state. Dry-run by default.")
    parser.add_argument("--apply", action="store_true", help="Actually delete eligible temp directories.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()
    report = clean(apply=args.apply)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        mode = "APPLY" if args.apply else "DRY RUN"
        print(f"{mode}: {len(report['actions'])} candidate temp directories, {report['deleted_count']} deleted.")
        for item in report["actions"]:
            marker = "deleted" if item["deleted"] else "kept"
            print(f"{marker}: {item['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
