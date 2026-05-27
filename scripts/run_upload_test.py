import json
import mimetypes
import sys
from pathlib import Path

import requests


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_upload_test.py <video_path>")
        return 2
    video_path = Path(sys.argv[1]).resolve()
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        return 2

    languages = ["hi", "es", "fr", "de", "ja", "zh", "ar", "pt"]
    voice_options = {"gender": "neutral", "emotion": "neutral", "cloned": True}
    data = {
        "languages": json.dumps(languages),
        "voiceOptions": json.dumps(voice_options),
        "sourceLanguage": "auto",
    }
    mime_type, _ = mimetypes.guess_type(video_path.name)
    if not mime_type:
        mime_type = "video/mp4"
    files = {"video": (video_path.name, open(video_path, "rb"), mime_type)}
    try:
        resp = requests.post("http://localhost:8000/api/upload", files=files, data=data, timeout=300)
    finally:
        files["video"][1].close()

    print(resp.status_code)
    print(resp.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
