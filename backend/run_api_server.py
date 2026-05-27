"""Start the VideoLingua API server with file-backed logs on Windows."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "backend"


def main() -> None:
    os.chdir(PROJECT_ROOT)
    sys.path.insert(0, str(PROJECT_ROOT))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_log = (LOG_DIR / "codex-api-server.stdout.log").open("a", encoding="utf-8", buffering=1)
    stderr_log = (LOG_DIR / "codex-api-server.stderr.log").open("a", encoding="utf-8", buffering=1)
    sys.stdout = stdout_log
    sys.stderr = stderr_log
    print("[API] Starting VideoLingua API server on http://127.0.0.1:8000", flush=True)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
