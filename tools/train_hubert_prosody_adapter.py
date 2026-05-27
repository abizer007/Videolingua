"""Train the lightweight HuBERT prosody adapter."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from voice.hubert_prosody import DEFAULT_MODEL, prosody_python


def _delegate_if_needed(argv: list[str]) -> int | None:
    if os.environ.get("VIDIOLINGUA_PROSODY_DELEGATED") == "1":
        return None
    py = prosody_python()
    if not py:
        return None
    if Path(sys.executable).resolve() == py.resolve():
        return None
    env = dict(os.environ)
    env["VIDIOLINGUA_PROSODY_DELEGATED"] = "1"
    result = subprocess.run(
        [str(py), "-m", "tools.train_hubert_prosody_adapter", *argv],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    delegated = _delegate_if_needed(argv)
    if delegated is not None:
        return delegated
    parser = argparse.ArgumentParser(description="Train the lightweight HuBERT prosody adapter.")
    parser.add_argument("--training-jobs", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    from prosody.adapter_train import train_adapter

    report = train_adapter(args.training_jobs, args.output_dir, model_name=args.model_name)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("status") in {"trained", "insufficient_data"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
