"""
run_uvr5_subprocess.py — Standalone Demucs BGM separator

This script is called by pipeline_runner.py as a subprocess using the isolated
BGM Python env (.venv_bgm) because Demucs has its own torch dependency set.

Usage:
    python lipsync/run_uvr5_subprocess.py <input_video_or_audio> <output_dir>

Environment:
    VIDIOLINGUA_USE_UVR5=true  (must be set)
    VIDIOLINGUA_DEMUCS_MODEL   (default: htdemucs)

Output files in <output_dir>:
    vocals.wav      — clean isolated speech
    no_vocals.wav   — background music / SFX
"""

import sys
import os
from pathlib import Path

# Ensure the project root is in sys.path so run_uvr5 can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["VIDIOLINGUA_USE_UVR5"] = "true"

if len(sys.argv) < 3:
    print("Usage: python run_uvr5_subprocess.py <input_video_or_audio> <output_dir>")
    sys.exit(1)

from lipsync.run_uvr5 import extract_bgm_from_video, separate_bgm, extract_audio_from_video

input_path = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)

print(f"[UVR5-Subprocess] Input: {input_path.name}")
print(f"[UVR5-Subprocess] Output dir: {output_dir}")

# If input is video, extract audio first
audio_path = input_path
if input_path.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
    audio_path = output_dir / "full_audio.wav"
    print(f"[UVR5-Subprocess] Extracting audio from video...")
    extract_audio_from_video(input_path, audio_path)

print(f"[UVR5-Subprocess] Running Demucs separation...")
vocals, bgm = separate_bgm(audio_path, output_dir)

print(f"[UVR5-Subprocess] Done.")
print(f"  vocals:     {vocals}")
print(f"  no_vocals:  {bgm}")
