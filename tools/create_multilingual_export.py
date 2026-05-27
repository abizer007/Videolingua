"""Package existing single-language VideoLingua outputs as multilingual media.

This tool is intentionally packaging-only. It validates and repackages existing
audio/video artifacts; it does not call ASR, translation, TTS, lip-sync, or any
model backend.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "kn": "Kannada",
    "hi": "Hindi",
    "ta": "Tamil",
    "bn": "Bengali",
    "te": "Telugu",
    "ml": "Malayalam",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "or": "Odia",
    "od": "Odia",
    "es": "Spanish",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese",
    "pt": "Portuguese",
    "it": "Italian",
    "ko": "Korean",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "tr": "Turkish",
    "cs": "Czech",
    "hu": "Hungarian",
    "ar": "Arabic",
}

ISO_639_2 = {
    "en": "eng",
    "fr": "fra",
    "kn": "kan",
    "hi": "hin",
    "ta": "tam",
    "bn": "ben",
    "te": "tel",
    "ml": "mal",
    "mr": "mar",
    "gu": "guj",
    "pa": "pan",
    "or": "ori",
    "od": "ori",
    "es": "spa",
    "de": "deu",
    "ja": "jpn",
    "zh": "zho",
    "pt": "por",
    "it": "ita",
    "ko": "kor",
    "nl": "nld",
    "pl": "pol",
    "ru": "rus",
    "tr": "tur",
    "cs": "ces",
    "hu": "hun",
    "ar": "ara",
}

XTTS_LANGS = {"ar", "cs", "de", "en", "es", "fr", "hu", "it", "ja", "ko", "nl", "pl", "pt", "ru", "tr", "zh"}
SARVAM_LANGS = {"bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}
INDICTRANS2_LANGS = {"as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "od", "pa", "ta", "te"}


class ExportError(RuntimeError):
    """Raised for clear user-facing packaging failures."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _display_path(path: str | Path, *, base: Path | None = None) -> str:
    p = Path(path)
    base = base or PROJECT_ROOT
    try:
        return str(p.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(p)


def _run(cmd: list[str], *, log_file: Path, cwd: Path = PROJECT_ROOT) -> subprocess.CompletedProcess[str]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    command_text = " ".join(_quote_for_log(part) for part in cmd)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(f"\n[{_utc_now()}] $ {command_text}\n")
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    with log_file.open("a", encoding="utf-8") as handle:
        if result.stdout:
            handle.write(result.stdout)
        if result.stderr:
            handle.write(result.stderr)
        handle.write(f"\n[exit_code={result.returncode}]\n")
    if result.returncode != 0:
        raise ExportError(f"Command failed ({result.returncode}): {command_text}\n{result.stderr or result.stdout}")
    return result


def _quote_for_log(value: str) -> str:
    if not value or any(char.isspace() for char in value):
        return f'"{value}"'
    return value


def _ffprobe(path: Path, *, log_file: Path) -> dict[str, Any]:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        log_file=log_file,
    )
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ExportError(f"ffprobe returned invalid JSON for {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExportError(f"ffprobe returned an unexpected payload for {path}")
    return data


def _media_duration(data: dict[str, Any]) -> float | None:
    duration = (data.get("format") or {}).get("duration")
    try:
        return round(float(duration), 3)
    except (TypeError, ValueError):
        return None


def _first_stream(data: dict[str, Any], codec_type: str) -> dict[str, Any] | None:
    for stream in data.get("streams") or []:
        if isinstance(stream, dict) and stream.get("codec_type") == codec_type:
            return stream
    return None


def _audio_summary(data: dict[str, Any]) -> dict[str, Any]:
    stream = _first_stream(data, "audio") or {}
    sample_rate = stream.get("sample_rate")
    try:
        sample_rate_value: int | None = int(sample_rate) if sample_rate else None
    except (TypeError, ValueError):
        sample_rate_value = None
    channels = stream.get("channels")
    try:
        channels_value: int | None = int(channels) if channels else None
    except (TypeError, ValueError):
        channels_value = None
    return {
        "duration_sec": _media_duration(data),
        "sample_rate": sample_rate_value,
        "channels": channels_value,
        "codec": stream.get("codec_name"),
    }


def _video_summary(data: dict[str, Any]) -> dict[str, Any]:
    stream = _first_stream(data, "video") or {}
    return {
        "duration_sec": _media_duration(data),
        "codec": stream.get("codec_name"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "bit_rate": (data.get("format") or {}).get("bit_rate") or stream.get("bit_rate"),
    }


def _sha256(path: Path, max_bytes: int = 512 * 1024 * 1024) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
    except OSError:
        return None


def _parse_track(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--track must use language=path, for example fr=outputs\\job\\tts\\output\\voice.wav")
    language, raw_path = value.split("=", 1)
    language = language.strip().lower().replace("_", "-").split("-")[0]
    if not language:
        raise argparse.ArgumentTypeError("--track language cannot be empty")
    return language, _resolve_path(raw_path.strip())


def _source_result_folder(audio_path: Path) -> Path | None:
    parts = [part.lower() for part in audio_path.parts]
    if "tts" in parts:
        index = parts.index("tts")
        if index > 0:
            return Path(*audio_path.parts[:index])
    return None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _nested_get(data: dict[str, Any] | None, *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _infer_route(language: str, source_folder: Path | None) -> dict[str, Any]:
    metrics = _read_json(source_folder / "evaluation" / "metrics_report.json") if source_folder else None
    pipeline_result = _read_json(source_folder / "pipeline_result.json") if source_folder else None

    translation_backend = (
        _nested_get(metrics, "operational", "translation_backend")
        or _nested_get(pipeline_result, "analysis", "run_evidence", "translation_backend")
        or _nested_get(pipeline_result, "metrics", "translation_backend")
    )
    voice_backend = (
        _nested_get(metrics, "operational", "voice_backend")
        or _nested_get(pipeline_result, "analysis", "run_evidence", "voice_backend")
        or _nested_get(pipeline_result, "metrics", "voice_backend")
    )

    lang = language.lower()
    if not translation_backend:
        translation_backend = "indictrans2" if lang in INDICTRANS2_LANGS else "google"
    if not voice_backend:
        if lang in SARVAM_LANGS and lang not in XTTS_LANGS:
            voice_backend = "sarvam"
        elif lang in XTTS_LANGS:
            voice_backend = "xtts"
        else:
            voice_backend = "unknown"

    voice_backend_normalized = str(voice_backend).strip().lower()
    if voice_backend_normalized == "sarvam":
        voice_mode = "managed-indian-tts"
        is_exact_clone = False
    elif voice_backend_normalized == "xtts":
        voice_mode = "speaker-reference voice"
        is_exact_clone = False
    else:
        voice_mode = "unknown"
        is_exact_clone = False

    return {
        "translation_backend": str(translation_backend).strip().lower(),
        "voice_backend": voice_backend_normalized,
        "voice_mode": voice_mode,
        "is_exact_clone": is_exact_clone,
        "route_metadata_source": "metrics_report" if metrics else "pipeline_result" if pipeline_result else "inferred_from_language",
    }


def _prepare_dirs(output_dir: Path) -> dict[str, Path]:
    dirs = {
        "source": output_dir / "source",
        "audio": output_dir / "audio",
        "hls": output_dir / "hls",
        "segments": output_dir / "hls" / "segments",
        "mp4": output_dir / "mp4",
        "metadata": output_dir / "metadata",
        "logs": output_dir / "logs",
    }
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def _convert_audio_to_aac(language: str, audio_path: Path, output_path: Path, *, log_file: Path) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output_path),
        ],
        log_file=log_file,
    )
    if not output_path.is_file():
        raise ExportError(f"AAC conversion did not create audio track for {language}: {output_path}")


def _create_hls(source_video: Path, language_tracks: list[dict[str, Any]], dirs: dict[str, Path], *, log_file: Path) -> dict[str, Any]:
    hls_dir = dirs["hls"]
    segments_dir = dirs["segments"]
    video_playlist = hls_dir / "video.m3u8"
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_video),
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "copy",
            "-f",
            "hls",
            "-hls_time",
            "6",
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            str(segments_dir / "video_%03d.ts"),
            str(video_playlist),
        ],
        log_file=log_file,
    )

    for track in language_tracks:
        language = track["language"]
        playlist = hls_dir / f"audio_{language}.m3u8"
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(track["aac_path_abs"]),
                "-map",
                "0:a:0",
                "-c:a",
                "copy",
                "-f",
                "hls",
                "-hls_time",
                "6",
                "-hls_playlist_type",
                "vod",
                "-hls_segment_filename",
                str(segments_dir / f"audio_{language}_%03d.aac"),
                str(playlist),
            ],
            log_file=log_file,
        )
        track["hls_playlist_abs"] = playlist

    master_path = hls_dir / "master.m3u8"
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    for index, track in enumerate(language_tracks):
        default = "YES" if index == 0 else "NO"
        language = track["language"]
        name = track["display_name"]
        lines.append(
            f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",LANGUAGE="{language}",'
            f'NAME="{name}",DEFAULT={default},AUTOSELECT=YES,URI="audio_{language}.m3u8"'
        )
    lines.append('#EXT-X-STREAM-INF:BANDWIDTH=6000000,CODECS="avc1.640028,mp4a.40.2",AUDIO="audio"')
    lines.append("video.m3u8")
    master_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    missing = [path for path in [master_path, video_playlist] + [track["hls_playlist_abs"] for track in language_tracks] if not path.is_file()]
    if missing:
        raise ExportError("HLS export is incomplete; missing: " + ", ".join(str(path) for path in missing))
    return {
        "master": master_path,
        "video_playlist": video_playlist,
        "audio_playlists": {track["language"]: track["hls_playlist_abs"] for track in language_tracks},
    }


def _create_mp4(source_video: Path, language_tracks: list[dict[str, Any]], dirs: dict[str, Path], *, log_file: Path) -> Path:
    output_path = dirs["mp4"] / "multilingual_muxed.mp4"
    cmd = ["ffmpeg", "-y", "-i", str(source_video)]
    for track in language_tracks:
        cmd.extend(["-i", str(track["aac_path_abs"])])
    cmd.extend(["-map", "0:v:0"])
    for index in range(len(language_tracks)):
        cmd.extend(["-map", f"{index + 1}:a:0"])
    cmd.extend(["-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart"])
    for index, track in enumerate(language_tracks):
        iso = ISO_639_2.get(track["language"], track["language"])
        cmd.extend([f"-metadata:s:a:{index}", f"language={iso}"])
        cmd.extend([f"-metadata:s:a:{index}", f"title={track['display_name']}"])
        cmd.extend([f"-disposition:a:{index}", "default" if index == 0 else "0"])
    cmd.append(str(output_path))
    _run(cmd, log_file=log_file)
    if not output_path.is_file():
        raise ExportError(f"Multi-audio MP4 was not created: {output_path}")
    return output_path


def _validate_mp4_probe(probe: dict[str, Any], expected_audio_count: int) -> dict[str, Any]:
    streams = [stream for stream in (probe.get("streams") or []) if isinstance(stream, dict)]
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    language_tags = [
        (stream.get("tags") or {}).get("language")
        for stream in audio_streams
    ]
    return {
        "video_stream_count": len(video_streams),
        "audio_stream_count": len(audio_streams),
        "expected_audio_stream_count": expected_audio_count,
        "language_tags": language_tags,
        "passed": bool(video_streams) and len(audio_streams) >= expected_audio_count,
        "duration_sec": _media_duration(probe),
    }


def create_export(args: argparse.Namespace) -> dict[str, Any]:
    source_video = _resolve_path(args.source_video)
    output_dir = _resolve_path(args.output_dir)
    if not source_video.is_file():
        raise ExportError(f"Source video does not exist: {source_video}")
    if not args.track:
        raise ExportError("At least one --track language=path is required")

    tracks = [_parse_track(value) for value in args.track]
    seen_languages: set[str] = set()
    for language, audio_path in tracks:
        if language in seen_languages:
            raise ExportError(f"Duplicate language track: {language}")
        seen_languages.add(language)
        if not audio_path.is_file():
            raise ExportError(f"Audio track for {language} does not exist: {audio_path}")

    dirs = _prepare_dirs(output_dir)
    log_file = dirs["logs"] / "packaging.log"
    log_file.write_text(f"VideoLingua multilingual export log\ncreated_at={_utc_now()}\n", encoding="utf-8")

    source_copy = dirs["source"] / "source_video.mp4"
    if source_video.resolve() != source_copy.resolve():
        shutil.copy2(source_video, source_copy)

    source_probe = _ffprobe(source_copy, log_file=log_file)
    (dirs["metadata"] / "ffprobe_source.json").write_text(
        json.dumps(source_probe, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if not _first_stream(source_probe, "video"):
        raise ExportError(f"Source video has no video stream: {source_video}")

    language_entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    for language, original_audio in tracks:
        source_audio_probe = _ffprobe(original_audio, log_file=log_file)
        (dirs["metadata"] / f"ffprobe_source_audio_{language}.json").write_text(
            json.dumps(source_audio_probe, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        source_audio_meta = _audio_summary(source_audio_probe)
        aac_path = dirs["audio"] / f"{language}.aac"
        _convert_audio_to_aac(language, original_audio, aac_path, log_file=log_file)
        audio_probe = _ffprobe(aac_path, log_file=log_file)
        (dirs["metadata"] / f"ffprobe_audio_{language}.json").write_text(
            json.dumps(audio_probe, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        audio_meta = _audio_summary(audio_probe)
        if not _first_stream(audio_probe, "audio"):
            raise ExportError(f"Packaged audio for {language} has no audio stream: {aac_path}")
        if not _first_stream(source_audio_probe, "audio"):
            raise ExportError(f"Source audio for {language} has no audio stream: {original_audio}")
        source_folder = _source_result_folder(original_audio)
        route = _infer_route(language, source_folder)
        if route["voice_backend"] == "xtts":
            warnings.append(f"{language}: XTTS is recorded as speaker-reference voice, not guaranteed exact identity.")
        if route["voice_backend"] == "sarvam":
            warnings.append(f"{language}: Sarvam is managed Indian-language TTS and is not exact speaker cloning.")
        language_entries.append(
            {
                "language": language,
                "display_name": LANGUAGE_NAMES.get(language, language.upper()),
                "audio_track_path": _display_path(aac_path, base=output_dir),
                "source_audio_path": _display_path(original_audio),
                "source_result_folder": _display_path(source_folder) if source_folder else None,
                "translation_backend": route["translation_backend"],
                "voice_backend": route["voice_backend"],
                "voice_mode": route["voice_mode"],
                "is_exact_clone": route["is_exact_clone"],
                "validation_status": "passed",
                "duration_sec": source_audio_meta["duration_sec"],
                "sample_rate": audio_meta["sample_rate"],
                "channels": audio_meta["channels"],
                "codec": audio_meta["codec"],
                "source_duration_sec": source_audio_meta["duration_sec"],
                "packaged_duration_note": "Duration is measured from the source WAV because raw ADTS AAC duration can be unreliable in ffprobe.",
                "route_metadata_source": route["route_metadata_source"],
                "aac_path_abs": aac_path,
            }
        )

    exports: dict[str, str | None] = {"hls_master": None, "multi_audio_mp4": None}
    hls_result: dict[str, Any] | None = None
    mp4_probe: dict[str, Any] | None = None
    mp4_validation: dict[str, Any] | None = None

    if args.create_hls:
        hls_result = _create_hls(source_copy, language_entries, dirs, log_file=log_file)
        exports["hls_master"] = _display_path(hls_result["master"], base=output_dir)
        warnings.append("HLS export is a single-video-rendition alternate-audio package; validate playback in a compatible HLS player.")

    if args.create_mp4:
        mp4_path = _create_mp4(source_copy, language_entries, dirs, log_file=log_file)
        exports["multi_audio_mp4"] = _display_path(mp4_path, base=output_dir)
        mp4_probe = _ffprobe(mp4_path, log_file=log_file)
        (dirs["metadata"] / "ffprobe_multilingual_mp4.json").write_text(
            json.dumps(mp4_probe, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        mp4_validation = _validate_mp4_probe(mp4_probe, len(language_entries))
        if not mp4_validation["passed"]:
            raise ExportError("Multi-audio MP4 validation failed: expected video plus all requested audio streams")

    source_video_meta = _video_summary(source_probe)
    manifest_entries = [{key: value for key, value in entry.items() if not key.endswith("_abs")} for entry in language_entries]
    manifest = {
        "schema_version": 1,
        "export_id": output_dir.name,
        "created_at": _utc_now(),
        "source_video": {
            "path": _display_path(source_copy, base=output_dir),
            "original_path": _display_path(source_video),
            "duration_sec": source_video_meta["duration_sec"],
            "hash": _sha256(source_video),
            "codec": source_video_meta["codec"],
            "width": source_video_meta["width"],
            "height": source_video_meta["height"],
            "avg_frame_rate": source_video_meta["avg_frame_rate"],
        },
        "languages": manifest_entries,
        "exports": exports,
        "commands": [
            "See logs/packaging.log for exact ffmpeg/ffprobe commands.",
        ],
        "warnings": sorted(set(warnings)),
        "errors": [],
    }
    manifest_path = dirs["metadata"] / "multilingual_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    validation_report = {
        "export_id": output_dir.name,
        "created_at": _utc_now(),
        "source_video_exists": source_copy.is_file(),
        "audio_tracks": [
            {
                "language": entry["language"],
                "path": entry["audio_track_path"],
                "exists": entry["aac_path_abs"].is_file(),
                "duration_sec": entry["duration_sec"],
                "sample_rate": entry["sample_rate"],
                "channels": entry["channels"],
            }
            for entry in language_entries
        ],
        "hls": {
            "requested": bool(args.create_hls),
            "master_exists": bool(hls_result and hls_result["master"].is_file()),
            "video_playlist_exists": bool(hls_result and hls_result["video_playlist"].is_file()),
            "audio_playlists": {
                language: playlist.is_file()
                for language, playlist in ((hls_result or {}).get("audio_playlists") or {}).items()
            },
        },
        "mp4": {
            "requested": bool(args.create_mp4),
            "validation": mp4_validation,
        },
        "passed": all(entry["aac_path_abs"].is_file() for entry in language_entries)
        and (not args.create_hls or bool(hls_result and hls_result["master"].is_file()))
        and (not args.create_mp4 or bool(mp4_validation and mp4_validation.get("passed"))),
        "warnings": sorted(set(warnings)),
        "errors": [],
    }
    (dirs["metadata"] / "validation_report.json").write_text(
        json.dumps(validation_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "manifest_path": manifest_path,
        "validation_report_path": dirs["metadata"] / "validation_report.json",
        "manifest": manifest,
        "validation_report": validation_report,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Package existing VideoLingua audio artifacts into HLS and/or a multi-audio MP4.",
    )
    parser.add_argument("--source-video", required=True, help="Source video path.")
    parser.add_argument(
        "--track",
        action="append",
        default=[],
        help="Language track in language=path form. Repeat for each language.",
    )
    parser.add_argument("--output-dir", required=True, help="Export output directory.")
    parser.add_argument("--create-hls", action="store_true", help="Create HLS alternate-audio export.")
    parser.add_argument("--create-mp4", action="store_true", help="Create multi-audio MP4 export.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = create_export(args)
    except ExportError as exc:
        print(f"[multilingual-export] ERROR: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"[multilingual-export] ERROR: required executable or file not found: {exc}", file=sys.stderr)
        return 1
    manifest = result["manifest"]
    print("[multilingual-export] export created")
    print(f"manifest={result['manifest_path']}")
    print(f"languages={', '.join(item['language'] for item in manifest['languages'])}")
    print(f"hls_master={manifest['exports'].get('hls_master')}")
    print(f"multi_audio_mp4={manifest['exports'].get('multi_audio_mp4')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
