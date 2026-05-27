"""
Lip Synchronization Module â€” SadTalker + GFPGAN + Fallback Chain

Upgrade over baseline Wav2Lip:
  - SadTalker: generates realistic talking-head animation from audio + portrait.
  - GFPGAN: face restoration post-processing to repair compression & upscale quality.
  - Fallback chain: SadTalker â†’ Wav2Lip â†’ ffmpeg (audio-only replace)

Engine selection (via env vars):
  VIDIOLINGUA_SADTALKER_DIR  â€” path to local SadTalker repo (activates SadTalker)
  VIDIOLINGUA_GFPGAN_DIR     â€” path to local GFPGAN repo (activates face restoration)
  VIDIOLINGUA_WAV2LIP_DIR    â€” path to local Wav2Lip repo (existing fallback)

If none of the above are set, audio is replaced with ffmpeg only (no lip-sync animation).

BGM remix:
  If VIDIOLINGUA_USE_UVR5=true, the lipsync output is remixed with the BGM
  extracted during the UVR5 stage. The BGM path is passed via env var:
  VIDIOLINGUA_BGM_PATH â€” set automatically by pipeline_runner.py
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path

INPUT_DIR = Path(os.environ.get("VIDIOLINGUA_LIPSYNC_INPUT_DIR", Path(__file__).parent / "input"))
OUTPUT_DIR = Path(os.environ.get("VIDIOLINGUA_LIPSYNC_OUTPUT_DIR", Path(__file__).parent / "output"))


def _env_true(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _lipsync_mode() -> str:
    mode = os.environ.get("VIDIOLINGUA_LIPSYNC_MODE", "").strip().lower()
    if mode in {"ffmpeg_mux", "wav2lip_optional", "wav2lip_required"}:
        return mode
    engine = os.environ.get("VIDIOLINGUA_LIPSYNC_ENGINE", "").strip().lower()
    if engine == "wav2lip":
        return "wav2lip_required" if _env_true("VIDIOLINGUA_REQUIRE_VISUAL_LIPSYNC") else "wav2lip_optional"
    return "ffmpeg_mux"


def _probe_duration(media_path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(media_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return float(r.stdout.strip())
    except (TypeError, ValueError):
        return 0.0


def _prepare_audio_for_video_duration(video_path: Path, audio_path: Path, output_path: Path) -> dict:
    video_duration = _probe_duration(video_path)
    audio_duration = _probe_duration(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    padded_sec = max(0.0, video_duration - audio_duration)
    trimmed_sec = max(0.0, audio_duration - video_duration)
    if video_duration <= 0:
        shutil.copy2(audio_path, output_path)
    else:
        audio_filter = f"apad,atrim=0:{video_duration:.6f},asetpts=PTS-STARTPTS"
        r = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(audio_path),
                "-af", audio_filter,
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            raise RuntimeError(f"Audio duration preparation failed: {r.stderr or r.stdout}")
    prepared_duration = _probe_duration(output_path)
    return {
        "source_video_duration_s": round(video_duration, 3),
        "generated_audio_duration_s": round(audio_duration, 3),
        "prepared_audio_duration_s": round(prepared_duration, 3),
        "audio_padded_sec": round(padded_sec, 3),
        "audio_trimmed_sec": round(trimmed_sec, 3),
    }


# ---------------------------------------------------------------------------
# ffmpeg: simple audio replacement (baseline, no lip-sync animation)
# ---------------------------------------------------------------------------

def replace_audio_with_ffmpeg(video_path: Path, audio_path: Path, output_path: Path) -> dict:
    """
    Replace video audio track with dubbed audio. No lip-sync animation.
    Pads or trims TTS to match video length.
    """
    import time

    started = time.time()
    print(f"[LipSync] Muxing start: video={video_path} audio={audio_path}")
    video_duration = _probe_duration(video_path)
    audio_duration = _probe_duration(audio_path)
    print(
        f"[LipSync] Duration diagnostics: video={video_duration:.2f}s "
        f"audio={audio_duration:.2f}s diff={audio_duration - video_duration:+.2f}s "
        "ffmpeg_shortest=false speedup_applied=false"
    )
    if abs(audio_duration - video_duration) > 1.0:
        print(
            f"[LipSync] WARNING: audio/video duration mismatch is "
            f"{audio_duration - video_duration:+.2f}s before mux."
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prepared_audio = output_path.with_name(output_path.stem + "_prepared_audio.wav")
    duration_meta = _prepare_audio_for_video_duration(video_path, audio_path, prepared_audio)
    print(
        f"[LipSync] Prepared audio duration={duration_meta['prepared_audio_duration_s']:.2f}s "
        f"padded={duration_meta['audio_padded_sec']:.2f}s trimmed={duration_meta['audio_trimmed_sec']:.2f}s"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(prepared_audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        str(output_path),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {r.stderr or r.stdout}")
    finally:
        prepared_audio.unlink(missing_ok=True)
    final_duration = _probe_duration(output_path)
    print(
        f"[LipSync] Duration diagnostics: final_mp4={final_duration:.2f}s "
        f"diff_vs_video={final_duration - video_duration:+.2f}s"
    )
    print(f"[LipSync] Muxing end: output={output_path} elapsed={time.time() - started:.1f}s")
    return {
        "method": "ffmpeg",
        "output_path": str(output_path),
        "visual_sync_applied": False,
        "fallback_used": False,
        "final_mp4_duration_s": round(final_duration, 3),
        "duration_delta_s": round(final_duration - video_duration, 3),
        **duration_meta,
    }


# ---------------------------------------------------------------------------
# MuseTalk 1.5 (intended production lip-sync backend)
# ---------------------------------------------------------------------------

def run_musetalk(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Run MuseTalk inference. Requires VIDIOLINGUA_MUSETALK_DIR to be set."""
    musetalk_dir = os.environ.get("VIDIOLINGUA_MUSETALK_DIR", "").strip()
    if not musetalk_dir:
        raise RuntimeError("VIDIOLINGUA_MUSETALK_DIR is not set")
    musetalk_dir = Path(musetalk_dir)
    if not musetalk_dir.is_dir():
        raise RuntimeError(f"MuseTalk directory not found at {musetalk_dir}")

    candidates = [
        musetalk_dir / "scripts" / "inference.py",
        musetalk_dir / "inference.py",
        musetalk_dir / "musetalk" / "inference.py",
    ]
    inference_script = next((p for p in candidates if p.is_file()), None)
    if inference_script is None:
        raise RuntimeError(
            "MuseTalk inference script not found. Expected one of: "
            + ", ".join(str(p) for p in candidates)
        )

    checkpoint_dir = os.environ.get("VIDIOLINGUA_MUSETALK_CHECKPOINT_DIR", "").strip()
    if checkpoint_dir and not Path(checkpoint_dir).exists():
        raise RuntimeError(f"MuseTalk checkpoint directory not found at {checkpoint_dir}")

    cmd = [
        os.environ.get("PYTHON", sys.executable),
        str(inference_script),
        "--video", str(video_path),
        "--audio", str(audio_path),
        "--result", str(output_path),
    ]
    if checkpoint_dir:
        cmd.extend(["--checkpoint_dir", checkpoint_dir])

    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(musetalk_dir),
    )
    if r.returncode != 0:
        raise RuntimeError(f"MuseTalk failed: {r.stderr or r.stdout}")
    if not output_path.is_file():
        candidates = sorted(
            output_path.parent.rglob("*.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            shutil.copy2(candidates[0], output_path)
        else:
            raise RuntimeError(f"MuseTalk produced no output MP4 near {output_path.parent}")


# ---------------------------------------------------------------------------
# Wav2Lip (legacy fallback)
# ---------------------------------------------------------------------------

def run_wav2lip(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Run Wav2Lip inference. Requires VIDIOLINGUA_WAV2LIP_DIR to be set."""
    wav2lip_dir = os.environ.get("VIDIOLINGUA_WAV2LIP_DIR", "").strip()
    if not wav2lip_dir:
        raise RuntimeError("VIDIOLINGUA_WAV2LIP_DIR is not set")
    wav2lip_dir = Path(wav2lip_dir)
    inference_script = wav2lip_dir / "inference.py"
    checkpoint = os.environ.get(
        "VIDIOLINGUA_WAV2LIP_CHECKPOINT",
        str(wav2lip_dir / "checkpoints" / "wav2lip_gan.pth"),
    )
    if not inference_script.exists():
        raise RuntimeError(f"Wav2Lip inference.py not found at {inference_script}")
    checkpoint_path = Path(checkpoint)
    if not checkpoint_path.is_file():
        raise RuntimeError(f"Wav2Lip checkpoint not found at {checkpoint_path}")
    wav2lip_python = (
        os.environ.get("VIDIOLINGUA_WAV2LIP_PYTHON", "").strip()
        or os.environ.get("PYTHON", "").strip()
        or sys.executable
    )
    resize_factor = os.environ.get("VIDIOLINGUA_WAV2LIP_RESIZE_FACTOR", "2").strip() or "2"
    face_batch_size = os.environ.get("VIDIOLINGUA_WAV2LIP_FACE_BATCH_SIZE", "4").strip() or "4"
    wav_batch_size = os.environ.get("VIDIOLINGUA_WAV2LIP_BATCH_SIZE", "16").strip() or "16"
    cmd = [
        wav2lip_python,
        str(inference_script),
        "--checkpoint_path", str(checkpoint_path),
        "--face", str(video_path.resolve()),
        "--audio", str(audio_path.resolve()),
        "--outfile", str(output_path.resolve()),
        "--resize_factor", resize_factor,
        "--face_det_batch_size", face_batch_size,
        "--wav2lip_batch_size", wav_batch_size,
    ]
    print(
        "[LipSync] Running Wav2Lip: "
        f"python={wav2lip_python} resize_factor={resize_factor} "
        f"face_batch={face_batch_size} wav_batch={wav_batch_size}"
    )
    r = subprocess.run(
        cmd,
        cwd=str(wav2lip_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"Wav2Lip failed: {r.stderr or r.stdout}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(
            "Wav2Lip completed without producing an output MP4. "
            f"stdout={r.stdout[-1200:]} stderr={r.stderr[-1200:]}"
        )


# ---------------------------------------------------------------------------
# SadTalker
# ---------------------------------------------------------------------------

def run_sadtalker(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """
    Run SadTalker to generate a talking-head video.

    SadTalker is designed for portrait images, but can accept a video (first frame used).
    Requires VIDIOLINGUA_SADTALKER_DIR to be set.

    SadTalker outputs to a timestamped directory; we copy the result to output_path.
    """
    sadtalker_dir = os.environ.get("VIDIOLINGUA_SADTALKER_DIR", "").strip()
    if not sadtalker_dir:
        raise RuntimeError("VIDIOLINGUA_SADTALKER_DIR is not set")
    sadtalker_dir = Path(sadtalker_dir)
    inference_script = sadtalker_dir / "inference.py"
    if not inference_script.exists():
        raise RuntimeError(f"SadTalker inference.py not found at {inference_script}")

    result_dir = output_path.parent / "sadtalker_result"
    result_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        os.environ.get("PYTHON", "python"),
        str(inference_script),
        "--driven_audio", str(audio_path),
        "--source_image", str(video_path),   # SadTalker accepts video; uses first frame
        "--result_dir", str(result_dir),
        "--still",            # reduced head motion (better for dubbing)
        "--enhancer", "gfpgan",  # built-in GFPGAN enhancer (if SadTalker has it bundled)
    ]
    print(f"[LipSync] Running SadTalker...")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"SadTalker failed: {r.stderr or r.stdout}")

    # Find the output video produced by SadTalker
    output_candidates = list(result_dir.rglob("*.mp4"))
    if not output_candidates:
        raise RuntimeError(f"SadTalker produced no output MP4 in {result_dir}")
    shutil.copy2(output_candidates[0], output_path)
    print(f"[LipSync] SadTalker output: {output_path.name}")


# ---------------------------------------------------------------------------
# GFPGAN face restoration (post-processing on any lipsync output)
# ---------------------------------------------------------------------------

def run_gfpgan(input_video: Path, output_video: Path) -> None:
    """
    Enhance face quality in video using GFPGAN.

    Extracts frames, runs GFPGAN on each, then re-encodes with original audio.
    Requires VIDIOLINGUA_GFPGAN_DIR to be set.
    """
    gfpgan_dir = os.environ.get("VIDIOLINGUA_GFPGAN_DIR", "").strip()
    if not gfpgan_dir:
        raise RuntimeError("VIDIOLINGUA_GFPGAN_DIR is not set")
    gfpgan_dir = Path(gfpgan_dir)
    restore_script = gfpgan_dir / "inference_gfpgan.py"
    if not restore_script.exists():
        raise RuntimeError(f"GFPGAN inference_gfpgan.py not found at {restore_script}")

    work_dir = output_video.parent / "_gfpgan_work"
    frames_dir = work_dir / "frames"
    restored_dir = work_dir / "restored"
    frames_dir.mkdir(parents=True, exist_ok=True)
    restored_dir.mkdir(parents=True, exist_ok=True)

    print(f"[LipSync/GFPGAN] Extracting frames from {input_video.name}...")
    # 1. Extract frames
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_video), str(frames_dir / "frame_%05d.png")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"Frame extraction failed: {r.stderr}")

    # 2. Run GFPGAN on frames directory
    print("[LipSync/GFPGAN] Running face restoration...")
    r = subprocess.run(
        [
            os.environ.get("PYTHON", "python"),
            str(restore_script),
            "-i", str(frames_dir),
            "-o", str(restored_dir),
            "--version", "1.3",
            "--upscale", "2",
            "--only_center_face",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(gfpgan_dir),
    )
    if r.returncode != 0:
        raise RuntimeError(f"GFPGAN failed: {r.stderr or r.stdout}")

    restored_frames_dir = restored_dir / "restored_imgs"
    if not restored_frames_dir.exists():
        restored_frames_dir = restored_dir  # older GFPGAN versions

    # 3. Get original fps
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", str(input_video)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    fps = "25"
    if probe.returncode == 0 and "/" in probe.stdout.strip():
        num, den = probe.stdout.strip().split("/")
        fps = f"{int(num) // int(den)}" if int(den) != 0 else "25"

    # 4. Re-encode frames + original audio back to video
    print("[LipSync/GFPGAN] Re-encoding enhanced video...")
    r = subprocess.run(
        [
            "ffmpeg", "-y",
            "-framerate", fps,
            "-i", str(restored_frames_dir / "frame_%05d.png"),
            "-i", str(input_video),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-c:a", "copy",
            "-pix_fmt", "yuv420p",
            str(output_video),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"GFPGAN re-encode failed: {r.stderr or r.stdout}")

    # Cleanup work dir
    shutil.rmtree(work_dir, ignore_errors=True)
    print(f"[LipSync/GFPGAN] Enhanced video: {output_video.name}")


# ---------------------------------------------------------------------------
# BGM remix (after lipsync, mix in background music)
# ---------------------------------------------------------------------------

def _remix_with_bgm(lipsync_video: Path, bgm_path: Path, output_path: Path) -> Path:
    """Mix lipsync video audio with background music. Returns output_path."""
    from lipsync.run_uvr5 import remix_bgm_with_tts

    # Extract audio from lipsync video
    tts_audio = output_path.parent / "_tts_from_lipsync.wav"
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(lipsync_video),
         "-vn", "-acodec", "pcm_s16le", "-ar", "44100", str(tts_audio)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"Audio extract for BGM remix failed: {r.stderr}")

    mixed_audio = output_path.parent / "_mixed_audio.wav"
    remix_bgm_with_tts(tts_audio, bgm_path, mixed_audio)
    prepared_mixed_audio = output_path.parent / "_mixed_audio_prepared.wav"
    _prepare_audio_for_video_duration(lipsync_video, mixed_audio, prepared_mixed_audio)

    # Replace lipsync video audio with mixed audio
    r = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(lipsync_video),
            "-i", str(prepared_mixed_audio),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"BGM final mux failed: {r.stderr}")

    tts_audio.unlink(missing_ok=True)
    mixed_audio.unlink(missing_ok=True)
    prepared_mixed_audio.unlink(missing_ok=True)
    return output_path


# ---------------------------------------------------------------------------
# Orchestrator: try SadTalker → Wav2Lip → ffmpeg, then optionally GFPGAN + BGM
# ---------------------------------------------------------------------------

def _wav2lip_preflight_ok() -> bool:
    return _env_true("VIDIOLINGUA_WAV2LIP_PREFLIGHT_OK")


def _summary_error(value: object, limit: int = 500) -> str:
    text = str(value or "")
    text = " ".join(text.split())
    return text[:limit]


def _legacy_process_lipsync_auto(video_path: Path, audio_path: Path, output_path: Path) -> dict:
    """
    Run the selected lipsync mode, then apply GFPGAN face restoration if available.
    Finally, remix with BGM if UVR5 was used.
    """
    raw_output = output_path.with_stem(output_path.stem + "_raw")
    lipsync_method = "ffmpeg"

    # Step 1: Lipsync (SadTalker â†’ Wav2Lip â†’ ffmpeg)
    engine = os.environ.get("VIDIOLINGUA_LIPSYNC_ENGINE", "auto").strip().lower()
    musetalk_dir = os.environ.get("VIDIOLINGUA_MUSETALK_DIR", "").strip()
    sadtalker_dir = os.environ.get("VIDIOLINGUA_SADTALKER_DIR", "").strip()
    wav2lip_dir = os.environ.get("VIDIOLINGUA_WAV2LIP_DIR", "").strip()
    gfpgan_dir = os.environ.get("VIDIOLINGUA_GFPGAN_DIR", "").strip()
    require_gfpgan = _env_true("VIDIOLINGUA_REQUIRE_GFPGAN")
    require_visual_lipsync = _env_true("VIDIOLINGUA_REQUIRE_VISUAL_LIPSYNC") or engine in {
        "musetalk",
        "sadtalker",
        "wav2lip",
    }

    if engine == "sadtalker" and sadtalker_dir:
        try:
            run_sadtalker(video_path, audio_path, raw_output)
            lipsync_method = "sadtalker"
        except Exception as e:
            print(f"[LipSync] SadTalker failed, trying Wav2Lip: {e}", file=sys.stderr)
            if wav2lip_dir:
                try:
                    run_wav2lip(video_path, audio_path, raw_output)
                    lipsync_method = "wav2lip"
                except Exception as e2:
                    if require_visual_lipsync:
                        raise RuntimeError(f"Wav2Lip is required but failed: {e2}") from e2
                    print(f"[LipSync] Wav2Lip failed, using ffmpeg: {e2}", file=sys.stderr)
                    replace_audio_with_ffmpeg(video_path, audio_path, raw_output)
            else:
                replace_audio_with_ffmpeg(video_path, audio_path, raw_output)
    elif musetalk_dir:
        try:
            run_musetalk(video_path, audio_path, raw_output)
            lipsync_method = "musetalk"
        except Exception as e:
            print(f"[LipSync] MuseTalk failed, trying Wav2Lip: {e}", file=sys.stderr)
            if wav2lip_dir:
                try:
                    run_wav2lip(video_path, audio_path, raw_output)
                    lipsync_method = "wav2lip"
                except Exception as e2:
                    if require_visual_lipsync:
                        raise RuntimeError(f"Wav2Lip is required but failed: {e2}") from e2
                    print(f"[LipSync] Wav2Lip failed, using ffmpeg: {e2}", file=sys.stderr)
                    replace_audio_with_ffmpeg(video_path, audio_path, raw_output)
            else:
                replace_audio_with_ffmpeg(video_path, audio_path, raw_output)
    elif wav2lip_dir:
        try:
            run_wav2lip(video_path, audio_path, raw_output)
            lipsync_method = "wav2lip"
        except Exception as e:
            if require_visual_lipsync:
                raise RuntimeError(f"Wav2Lip is required but failed: {e}") from e
            print(f"[LipSync] Wav2Lip failed, using ffmpeg: {e}", file=sys.stderr)
            replace_audio_with_ffmpeg(video_path, audio_path, raw_output)
    else:
        replace_audio_with_ffmpeg(video_path, audio_path, raw_output)

    print(f"[LipSync] Method used: {lipsync_method}")

    # Step 2: GFPGAN face restoration (optional post-processing)
    post_output = output_path.with_stem(output_path.stem + "_gfpgan")
    if gfpgan_dir and lipsync_method in ("musetalk", "sadtalker", "wav2lip", "ffmpeg"):
        try:
            run_gfpgan(raw_output, post_output)
            lipsync_source = post_output
        except Exception as e:
            if require_gfpgan:
                raise RuntimeError(f"GFPGAN is required but failed: {e}") from e
            print(f"[LipSync] GFPGAN failed (skipping): {e}", file=sys.stderr)
            lipsync_source = raw_output
    elif require_gfpgan:
        raise RuntimeError("GFPGAN is required but VIDIOLINGUA_GFPGAN_DIR is not set")
    else:
        lipsync_source = raw_output

    # Step 3: BGM remix (optional, if UVR5 was used)
    bgm_path_str = os.environ.get("VIDIOLINGUA_BGM_PATH", "").strip()
    if bgm_path_str and Path(bgm_path_str).is_file():
        try:
            _remix_with_bgm(lipsync_source, Path(bgm_path_str), output_path)
            print("[LipSync] BGM remix complete.")
        except Exception as e:
            print(f"[LipSync] BGM remix failed (using lipsync audio): {e}", file=sys.stderr)
            shutil.copy2(lipsync_source, output_path)
    else:
        shutil.copy2(lipsync_source, output_path)

    # Cleanup intermediate files
    raw_output.unlink(missing_ok=True)
    post_output.unlink(missing_ok=True)


def process_lipsync(video_path: Path, audio_path: Path, output_path: Path) -> dict:
    """
    Run the selected lipsync mode, then apply GFPGAN face restoration if available.
    This definition intentionally supersedes the legacy auto-fallback implementation above.
    """
    raw_output = output_path.with_stem(output_path.stem + "_raw")
    mode = _lipsync_mode()
    visual_requested = mode in {"wav2lip_optional", "wav2lip_required"}
    fallback_used = False
    wav2lip_error = ""
    warnings: list[str] = []
    errors: list[str] = []
    result_meta: dict = {
        "method": "ffmpeg",
        "mode": mode,
        "visual_sync_requested": visual_requested,
        "visual_sync_applied": False,
        "fallback_used": False,
        "wav2lip_error": None,
        "warnings": warnings,
        "errors": errors,
    }

    wav2lip_dir = os.environ.get("VIDIOLINGUA_WAV2LIP_DIR", "").strip()
    wav2lip_checkpoint = os.environ.get("VIDIOLINGUA_WAV2LIP_CHECKPOINT", "").strip()
    wav2lip_preflight_ok = _wav2lip_preflight_ok()
    preflight_error = os.environ.get("VIDIOLINGUA_WAV2LIP_ERROR", "").strip()
    gfpgan_dir = os.environ.get("VIDIOLINGUA_GFPGAN_DIR", "").strip()
    require_gfpgan = _env_true("VIDIOLINGUA_REQUIRE_GFPGAN")

    if mode == "ffmpeg_mux":
        result_meta.update(replace_audio_with_ffmpeg(video_path, audio_path, raw_output))
    elif mode in {"wav2lip_optional", "wav2lip_required"}:
        checkpoint_exists = bool(wav2lip_checkpoint and Path(wav2lip_checkpoint).is_file())
        ready = bool(wav2lip_dir and checkpoint_exists and wav2lip_preflight_ok)
        if not ready:
            reason = preflight_error or "Wav2Lip directory, checkpoint, or runtime preflight is not ready."
            wav2lip_error = _summary_error(reason)
            errors.append(wav2lip_error)
            if mode == "wav2lip_required":
                raise RuntimeError(f"Wav2Lip required mode failed before generation: {wav2lip_error}")
            fallback_used = True
            warnings.append("Wav2Lip was requested but preflight failed; ffmpeg audio mux fallback was used.")
            print(f"[LipSync] Wav2Lip preflight failed, using ffmpeg: {wav2lip_error}", file=sys.stderr)
            result_meta.update(replace_audio_with_ffmpeg(video_path, audio_path, raw_output))
        else:
            try:
                run_wav2lip(video_path, audio_path, raw_output)
                video_duration = _probe_duration(video_path)
                final_duration = _probe_duration(raw_output)
                result_meta.update(
                    {
                        "method": "wav2lip",
                        "output_path": str(raw_output),
                        "visual_sync_applied": True,
                        "final_mp4_duration_s": round(final_duration, 3),
                        "duration_delta_s": round(final_duration - video_duration, 3),
                        "source_video_duration_s": round(video_duration, 3),
                        "generated_audio_duration_s": round(_probe_duration(audio_path), 3),
                    }
                )
            except Exception as exc:
                wav2lip_error = _summary_error(exc)
                errors.append(wav2lip_error)
                if mode == "wav2lip_required":
                    raise RuntimeError(f"Wav2Lip required mode failed: {wav2lip_error}") from exc
                fallback_used = True
                warnings.append("Wav2Lip failed during generation; ffmpeg audio mux fallback was used.")
                print(f"[LipSync] Wav2Lip failed, using ffmpeg: {wav2lip_error}", file=sys.stderr)
                result_meta.update(replace_audio_with_ffmpeg(video_path, audio_path, raw_output))
    else:
        warnings.append(f"Unknown lipsync mode '{mode}'; ffmpeg audio mux fallback was used.")
        result_meta.update(replace_audio_with_ffmpeg(video_path, audio_path, raw_output))

    lipsync_method = str(result_meta.get("method") or "ffmpeg")
    result_meta["mode"] = mode
    result_meta["visual_sync_requested"] = visual_requested
    result_meta["visual_sync_applied"] = lipsync_method in {"wav2lip", "musetalk", "sadtalker"}
    result_meta["fallback_used"] = fallback_used or bool(result_meta.get("fallback_used"))
    result_meta["wav2lip_error"] = wav2lip_error or None
    result_meta["warnings"] = warnings
    result_meta["errors"] = errors
    print(f"[LipSync] Method used: {lipsync_method}")

    post_output = output_path.with_stem(output_path.stem + "_gfpgan")
    if gfpgan_dir:
        try:
            run_gfpgan(raw_output, post_output)
            lipsync_source = post_output
        except Exception as exc:
            if require_gfpgan:
                raise RuntimeError(f"GFPGAN is required but failed: {exc}") from exc
            print(f"[LipSync] GFPGAN failed (skipping): {exc}", file=sys.stderr)
            lipsync_source = raw_output
    elif require_gfpgan:
        raise RuntimeError("GFPGAN is required but VIDIOLINGUA_GFPGAN_DIR is not set")
    else:
        lipsync_source = raw_output

    bgm_path_str = os.environ.get("VIDIOLINGUA_BGM_PATH", "").strip()
    if bgm_path_str and Path(bgm_path_str).is_file():
        try:
            _remix_with_bgm(lipsync_source, Path(bgm_path_str), output_path)
            print("[LipSync] BGM remix complete.")
        except Exception as exc:
            print(f"[LipSync] BGM remix failed (using lipsync audio): {exc}", file=sys.stderr)
            shutil.copy2(lipsync_source, output_path)
    else:
        shutil.copy2(lipsync_source, output_path)

    result_meta["output_path"] = str(output_path)
    result_meta["final_mp4_duration_s"] = round(_probe_duration(output_path), 3)
    source_duration = _probe_duration(video_path)
    result_meta["duration_delta_s"] = round(result_meta["final_mp4_duration_s"] - source_duration, 3)

    raw_output.unlink(missing_ok=True)
    post_output.unlink(missing_ok=True)
    return result_meta


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main entry point for lip synchronization processing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    video_files = (
        list(INPUT_DIR.glob("*.mp4"))
        + list(INPUT_DIR.glob("*.avi"))
        + list(INPUT_DIR.glob("*.mov"))
    )
    audio_files = list(INPUT_DIR.glob("*.wav")) + list(INPUT_DIR.glob("*.mp3"))

    if not video_files:
        print(f"No video files found in {INPUT_DIR}")
        return
    if not audio_files:
        print(f"No audio files found in {INPUT_DIR}")
        return

    original_video = video_files[0]
    print(f"Using original video: {original_video.name}")

    had_error = False
    summaries = []
    for audio_file in audio_files:
        print(f"Processing audio: {audio_file.name}")
        language_code = audio_file.stem.split("_")[-1]
        output_file = OUTPUT_DIR / f"{original_video.stem}_dubbed_{language_code}.mp4"
        try:
            summary = process_lipsync(original_video, audio_file, output_file)
            summaries.append(summary)
            print(f"Dubbed video saved: {output_file.name}")
        except Exception as e:
            print(f"Error processing {audio_file.name}: {e}", file=sys.stderr)
            summaries.append(
                {
                    "input_audio": str(audio_file),
                    "output_path": str(output_file),
                    "mode": _lipsync_mode(),
                    "method": "failed",
                    "visual_sync_requested": _lipsync_mode() in {"wav2lip_optional", "wav2lip_required"},
                    "visual_sync_applied": False,
                    "fallback_used": False,
                    "errors": [_summary_error(e)],
                    "warnings": [],
                }
            )
            had_error = True
    summary_path = OUTPUT_DIR / "lipsync_summary.json"
    summary_path.write_text(
        json.dumps({"outputs": summaries}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
