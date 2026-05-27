"""Download or verify the official Coqui XTTS v2 model files.

The Coqui downloader requires explicit CPML/commercial license acceptance for
XTTS v2. This script is intentionally idempotent and non-destructive: it
verifies an existing model directory first and only downloads missing files
when requested.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"


def _valid_model_dir(path: Path) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not (path / "config.json").is_file():
        missing.append("config.json")
    if not any(path.glob("*.pth")):
        missing.append("model.pth or another .pth checkpoint")
    if not ((path / "vocab.json").is_file() or (path / "tokenizer.json").is_file()):
        missing.append("vocab.json or tokenizer.json")
    return not missing, missing


def _copy_downloaded_model(downloaded_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in downloaded_dir.iterdir():
        dest = output_dir / item.name
        if item.is_file() and not dest.exists():
            shutil.copy2(item, dest)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download/verify Coqui XTTS v2 model files.")
    parser.add_argument("--output-dir", default="models/xtts_v2")
    parser.add_argument(
        "--agree-to-coqui-terms",
        action="store_true",
        help="Confirm you have accepted Coqui XTTS v2 CPML/commercial terms.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    ok, missing = _valid_model_dir(output_dir)
    if ok:
        print(f"XTTS v2 model already present: {output_dir}")
        return 0

    if not args.agree_to_coqui_terms and os.environ.get("COQUI_TOS_AGREED") != "1":
        print("XTTS v2 model is missing or incomplete.", file=sys.stderr)
        print(f"Target directory: {output_dir}", file=sys.stderr)
        print(f"Missing: {', '.join(missing)}", file=sys.stderr)
        print("Coqui XTTS v2 requires CPML/commercial license acceptance.", file=sys.stderr)
        print("Rerun with --agree-to-coqui-terms after accepting the terms.", file=sys.stderr)
        return 2

    os.environ["COQUI_TOS_AGREED"] = "1"
    os.environ.setdefault("TTS_HOME", str(PROJECT_ROOT / "models" / ".coqui_cache"))

    from TTS.utils.manage import ModelManager

    manager = ModelManager(progress_bar=True, verbose=True)
    model_path, _config_path, _model_item = manager.download_model(XTTS_MODEL)
    downloaded_dir = Path(model_path)
    if not downloaded_dir.is_dir():
        raise RuntimeError(f"Coqui downloader returned a non-directory model path: {downloaded_dir}")

    _copy_downloaded_model(downloaded_dir, output_dir)
    ok, missing = _valid_model_dir(output_dir)
    if not ok:
        raise RuntimeError(f"Downloaded XTTS v2 model is incomplete: {', '.join(missing)}")

    print(f"XTTS v2 model ready: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
