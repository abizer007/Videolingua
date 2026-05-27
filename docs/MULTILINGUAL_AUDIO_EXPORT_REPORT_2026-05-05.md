# Multilingual Audio Export Report - 2026-05-05

## 1. What Was Added

Added an additive multilingual packaging layer for existing VideoLingua outputs:

- `tools\create_multilingual_export.py`
- safe FastAPI endpoints under `/api/multilingual-export`
- `NEW_Frontend\app\multilingual-export\page.tsx`
- homepage and architecture-page OTT export sections
- results-page multilingual export discovery card
- proof export under `outputs\multilingual_exports\official_fr_kn_test`

This phase packages existing media only. It does not run ASR, translation, TTS,
lip-sync, XTTS loading, Sarvam generation, IndicF5, or batch generation.

## 2. Why Multi-Language Audio Export Matters

The previous delivery shape was one dubbed MP4 per language. The new export
layer moves VideoLingua toward OTT-style localization:

- one source video;
- multiple selectable localized audio tracks;
- HLS alternate-audio packaging;
- optional multi-audio MP4;
- manifest-backed route and validation evidence per language.

## 3. HLS Export Structure

Proof export:

```text
outputs\multilingual_exports\official_fr_kn_test\hls\
  master.m3u8
  video.m3u8
  audio_fr.m3u8
  audio_kn.m3u8
  segments\
```

`master.m3u8` includes alternate audio entries:

```text
LANGUAGE="fr", NAME="French", URI="audio_fr.m3u8"
LANGUAGE="kn", NAME="Kannada", URI="audio_kn.m3u8"
```

Limit: this is a single-video-rendition HLS proof, not an adaptive bitrate
ladder. Playback should be validated in a compatible HLS player.

## 4. Multi-Audio MP4 Structure

Proof MP4:

```text
outputs\multilingual_exports\official_fr_kn_test\mp4\multilingual_muxed.mp4
```

ffprobe summary:

```text
duration=30.603900
size=79,235,808 bytes
stream 0: video h264 language=und
stream 1: audio aac language=fra
stream 2: audio aac language=kan
```

The source video is copied into the export folder and never overwritten.

## 5. Manifest Schema

Manifest:

```text
outputs\multilingual_exports\official_fr_kn_test\metadata\multilingual_manifest.json
```

Top-level sections:

- `schema_version`
- `export_id`
- `created_at`
- `source_video`
- `languages`
- `exports`
- `commands`
- `warnings`
- `errors`

Per-language records include:

- language and display name;
- packaged AAC path;
- original source audio path;
- source result folder;
- translation backend;
- voice backend;
- voice mode;
- exact-clone boolean;
- validation status;
- duration, sample rate, channels, codec.

XTTS is labeled as `speaker-reference voice` with `is_exact_clone=false`.
Sarvam is labeled as `managed-indian-tts` with `is_exact_clone=false`.

## 6. Tool Command

Command used:

```powershell
.\.venv_api\Scripts\python.exe -m tools.create_multilingual_export --source-video Vidiolingua_Test_Official.mp4 --track fr=outputs\french_official_test\tts\output\Vidiolingua_Test_Official_transcription_fr.wav --track kn=outputs\kannada_sarvam_practical_test_clipfix\tts\output\Vidiolingua_Test_Official_transcription_kn.wav --output-dir outputs\multilingual_exports\official_fr_kn_test --create-hls --create-mp4
```

Result:

```text
export created
languages=fr, kn
hls_master=hls\master.m3u8
multi_audio_mp4=mp4\multilingual_muxed.mp4
```

## 7. Test Export Result

Created:

```text
outputs\multilingual_exports\official_fr_kn_test\audio\fr.aac
outputs\multilingual_exports\official_fr_kn_test\audio\kn.aac
outputs\multilingual_exports\official_fr_kn_test\hls\master.m3u8
outputs\multilingual_exports\official_fr_kn_test\mp4\multilingual_muxed.mp4
outputs\multilingual_exports\official_fr_kn_test\metadata\multilingual_manifest.json
outputs\multilingual_exports\official_fr_kn_test\metadata\validation_report.json
```

Validation report:

```text
passed=true
hls.master_exists=true
hls.video_playlist_exists=true
hls.audio_fr=true
hls.audio_kn=true
mp4.video_stream_count=1
mp4.audio_stream_count=2
mp4.language_tags=fra, kan
```

## 8. ffprobe Summary

Source video:

```text
duration=30.667s
codec=h264
resolution=1920x1080
fps=30/1
```

French packaged track:

```text
duration=30.574s
sample_rate=44100
channels=2
codec=aac
translation_backend=google
voice_backend=xtts
voice_mode=speaker-reference voice
is_exact_clone=false
```

Kannada packaged track:

```text
duration=30.655s
sample_rate=44100
channels=2
codec=aac
translation_backend=indictrans2
voice_backend=sarvam
voice_mode=managed-indian-tts
is_exact_clone=false
```

Note: per-track duration is measured from the source WAV because ffprobe can
report unreliable durations for raw ADTS AAC files.

## 9. Included Languages

Included proof tracks:

- French: XTTS speaker-reference voice route.
- Kannada: IndicTrans2 translation + Sarvam managed Indian-language TTS.

## 10. Backend Used Per Language

| Language | Translation backend | Voice backend | Voice mode | Exact clone | Validation |
| --- | --- | --- | --- | --- | --- |
| French | google | xtts | speaker-reference voice | false | passed |
| Kannada | indictrans2 | sarvam | managed-indian-tts | false | passed |

## 11. Limitations

- HLS is a single-rendition alternate-audio proof, not adaptive bitrate.
- HLS alternate-audio behavior depends on player support.
- Browser playback of multi-track MP4 audio selection is limited.
- The packaging tool infers route metadata from existing reports when present,
  or from known language/backend policy when historical metadata is sparse.
- The API endpoint runs packaging synchronously for now.
- No job picker UI was added yet.

## 12. Roadmap

- Generate multiple languages in one batch.
- Add hls.js preview player with audio-track selection.
- Package source and translated WebVTT subtitles/captions.
- Upload HLS/MP4 artifacts to object storage.
- Serve master playlists through CDN/signed URLs.
- Add adaptive bitrate HLS ladders.
- Add provenance and generated-media disclosure per language track.
- Improve multi-track MP4 player compatibility notes.

## Validation

Backend:

```text
.\.venv_api\Scripts\python.exe -m compileall backend app asr translation tts voice workers tools evaluation
passed

.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
passed; Sarvam key masked, IndicF5 false/local_disabled, XTTS model ready

.\.venv_api\Scripts\python.exe -m tools.create_multilingual_export --help
passed
```

Frontend:

```text
corepack pnpm run build
passed; /multilingual-export generated
```

Frontend lint:

```text
corepack pnpm run lint
blocked by Corepack cache EPERM in sandbox; escalation request was rejected by
the app usage limit. No workaround was attempted.
```

Safety:

- No ASR/translation/TTS/lip-sync rerun.
- Existing French output untouched.
- Existing Kannada output untouched.
- `models\xtts_v2` untouched.
- No venv mutation.
- No dependency install.
- No local IndicF5 load.
- No secrets exposed.
- No generic fallback added.
- No Indic Parler used.
## 2026-05-06 Responsible AI Note

The multilingual export layer remains packaging-only. Responsible AI provenance is generated at job level through the new compliance package and can be referenced by future export manifests. This phase does not rewrite protected multilingual proof output and does not claim signed C2PA for exported packages.
