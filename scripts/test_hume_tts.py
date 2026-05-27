"""
Standalone test for Hume TTS: generate_speech() with cloned voice.
Reads HUME_API_KEY from env, calls generate_speech, prints path and file size.
Run from project root: python scripts/test_hume_tts.py
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Enable debug logging to see request/response
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s %(message)s")

from app.services.hume_tts_service import generate_speech


def main() -> None:
    if not os.environ.get("HUME_API_KEY", "").strip():
        print("ERROR: HUME_API_KEY is not set")
        sys.exit(1)
    test_text = "Hello this is Abizer speaking in another language."
    print(f"Calling generate_speech with: {test_text!r}")
    path = generate_speech(test_text)
    print(f"Saved path: {path}")
    size = Path(path).stat().st_size
    print(f"File size: {size} bytes")
    print("OK")


if __name__ == "__main__":
    main()
