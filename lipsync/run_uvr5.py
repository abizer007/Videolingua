"""
UVR5 / Demucs Background Music Separation Module

Splits audio/video into:
  vocals.wav    — original speech (discarded; replaced by TTS)
  no_vocals.wav — background music + SFX (preserved and remixed)

Uses Facebook's Demucs library (pip install demucs) with the htdemucs model.
Falls back gracefully if demucs is not installed (UVR5 step is skipped).

Usage:
  python lipsync/run_uvr5.py <input_video_or_audio> <output_dir>

  Or import extract_bgm() from pipeline_runner.py.

Environment variables:
  VIDIOLINGUA_USE_UVR5=true     — enable BGM separation (default: false)
  VIDIOLINGUA_DEMUCS_MODEL      — demucs model name (default: htdemucs)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

DEMUCS_MODEL = os.environ.get("VIDIOLINGUA_DEMUCS_MODEL", "htdemucs")


def extract_audio_from_video(video_path: Path, output_wav: Path) -> None:
    """Extract full audio from video as WAV for Demucs."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(output_wav),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extract failed: {r.stderr or r.stdout}")


def separate_bgm(input_audio: Path, output_dir: Path) -> tuple[Path, Path]:
    """
    Run Demucs to separate vocals and background music.

    Returns:
        (vocals_path, no_vocals_path) — paths to the separated stems.

    Raises:
        RuntimeError if demucs is not installed or fails.
    """
    try:
        import demucs.separate  # noqa: F401 — verify import early
    except ImportError as e:
        raise RuntimeError(
            "Demucs not installed. Run: pip install demucs\n"
            "Or set VIDIOLINGUA_USE_UVR5=false to skip BGM separation."
        ) from e

    output_dir.mkdir(parents=True, exist_ok=True)

    # Demucs CLI: outputs to <output_dir>/<model>/<track_stem>/{vocals,no_vocals,...}.wav
    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems", "vocals",       # produce only vocals + no_vocals (faster)
        "--model", DEMUCS_MODEL,
        "--out", str(output_dir),
        str(input_audio),
    ]
    print(f"[UVR5/Demucs] Separating BGM from: {input_audio.name}")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"Demucs separation failed: {r.stderr or r.stdout}")

    # Locate output stems
    stem_name = input_audio.stem
    demucs_out = output_dir / DEMUCS_MODEL / stem_name
    if not demucs_out.exists():
        # Search for the folder
        for candidate in output_dir.rglob(stem_name):
            if candidate.is_dir():
                demucs_out = candidate
                break

    vocals_path = demucs_out / "vocals.wav"
    no_vocals_path = demucs_out / "no_vocals.wav"

    if not vocals_path.exists() or not no_vocals_path.exists():
        raise RuntimeError(
            f"Demucs output not found at {demucs_out}. "
            f"Expected: vocals.wav, no_vocals.wav"
        )

    # Copy to flat output_dir for easy access
    final_vocals = output_dir / "vocals.wav"
    final_bgm = output_dir / "no_vocals.wav"
    shutil.copy2(vocals_path, final_vocals)
    shutil.copy2(no_vocals_path, final_bgm)

    print(f"[UVR5/Demucs] BGM extracted → {final_bgm.name}")
    print(f"[UVR5/Demucs] Vocals extracted → {final_vocals.name}")
    return final_vocals, final_bgm


def remix_bgm_with_tts(tts_audio: Path, bgm_audio: Path, output_path: Path) -> Path:
    """
    Mix TTS dubbed speech with the original background music using ffmpeg.

    The BGM is attenuated slightly (0.85x) so speech is clear.
    Both tracks are mixed to stereo AAC output.

    Args:
        tts_audio:   Dubbed speech WAV (from TTS stage).
        bgm_audio:   Background music WAV (from Demucs separation).
        output_path: Output mixed WAV path.

    Returns:
        Path to the mixed output file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # amix: input 0 = TTS (full volume), input 1 = BGM (0.85 volume)
    # duration=longest: pad shorter stream with silence
    cmd = [
        "ffmpeg", "-y",
        "-i", str(tts_audio),       # input 0: dubbed speech
        "-i", str(bgm_audio),       # input 1: background music
        "-filter_complex",
        "[0:a]volume=1.0[speech];[1:a]volume=0.85[bgm];[speech][bgm]amix=inputs=2:duration=longest",
        "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"BGM remix failed: {r.stderr or r.stdout}")

    print(f"[UVR5/Demucs] Remixed audio → {output_path.name}")
    return output_path


def extract_bgm_from_video(video_path: Path, work_dir: Path) -> tuple[Path | None, Path | None]:
    """
    High-level helper used by pipeline_runner.py.

    Extracts audio from video, runs Demucs separation.
    Returns (vocals_path, bgm_path) or (None, None) if UVR5 is disabled or fails.
    """
    use_uvr5 = os.environ.get("VIDIOLINGUA_USE_UVR5", "false").strip().lower() == "true"
    if not use_uvr5:
        return None, None

    work_dir.mkdir(parents=True, exist_ok=True)
    raw_audio = work_dir / "full_audio.wav"

    try:
        extract_audio_from_video(video_path, raw_audio)
        vocals, bgm = separate_bgm(raw_audio, work_dir)
        return vocals, bgm
    except Exception as e:
        print(f"[UVR5/Demucs] BGM separation failed (skipping): {e}", file=sys.stderr)
        return None, None


# ---------------------------------------------------------------------------
# CLI entry point for standalone testing
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: python run_uvr5.py <input_video_or_audio> <output_dir>")
        print("  Env: VIDIOLINGUA_USE_UVR5=true  (must be set)")
        sys.exit(1)

    os.environ["VIDIOLINGUA_USE_UVR5"] = "true"
    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}:
        raw_audio = output_dir / "full_audio.wav"
        extract_audio_from_video(input_path, raw_audio)
        input_path = raw_audio

    vocals, bgm = separate_bgm(input_path, output_dir)
    print(f"Vocals: {vocals}")
    print(f"BGM:    {bgm}")


if __name__ == "__main__":
    main()
