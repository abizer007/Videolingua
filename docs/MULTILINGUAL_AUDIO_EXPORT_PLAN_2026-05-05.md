# Multilingual Audio Export Plan - 2026-05-05

## 1. Current Single-Language Output Structure

The current pipeline still produces one dubbed MP4 per target language. Each run
has stage folders and a legacy result contract:

```text
outputs\<job_id>\
  asr\input\
  asr\output\
  translation\input\
  translation\output\
  tts\input\
  tts\output\
  lipsync\input\
  lipsync\output\
  results\
    input_video.mp4
    <source_stem>_dubbed_<language>.mp4
  logs\
  evaluation\
  pipeline_result.json
```

The API result shape remains:

```text
originalVideo
localizedVideos[]
metrics
analysis
metricsReport
manifestSummary
```

The new multilingual export layer must not replace this shape or change how
single-language jobs run.

## 2. Available Known-Good French/Kannada Artifacts

Protected French XTTS proof run:

```text
outputs\french_official_test
outputs\french_official_test\tts\output\Vidiolingua_Test_Official_transcription_fr.wav
outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4
```

Protected Kannada IndicTrans2 + Sarvam proof run:

```text
outputs\kannada_sarvam_practical_test_clipfix
outputs\kannada_sarvam_practical_test_clipfix\tts\output\Vidiolingua_Test_Official_transcription_kn.wav
outputs\kannada_sarvam_practical_test_clipfix\results\Vidiolingua_Test_Official_dubbed_kn.mp4
```

Shared source video for the first proof export:

```text
Vidiolingua_Test_Official.mp4
```

These artifacts are inputs only. The export tool must never overwrite, delete,
move, regenerate, normalize, or retrofit them.

## 3. Proposed Multi-Language Export Architecture

Add a packaging-only layer:

```text
existing single-language artifacts
-> validate source video and TTS WAV tracks
-> ffprobe source and tracks
-> encode per-language AAC copies into a new export folder
-> create optional HLS alternate-audio package
-> create optional multi-audio MP4
-> write multilingual_manifest.json and validation_report.json
```

The layer does not call ASR, translation, TTS, lip-sync, voice routing, or model
loading. It only packages already generated media.

Target folder:

```text
outputs\multilingual_exports\<export_id>\
  source\
    source_video.mp4
  audio\
    fr.aac
    kn.aac
  hls\
    master.m3u8
    video.m3u8
    audio_fr.m3u8
    audio_kn.m3u8
    segments\
  mp4\
    multilingual_muxed.mp4
  metadata\
    multilingual_manifest.json
    ffprobe_source.json
    ffprobe_multilingual_mp4.json
    validation_report.json
  logs\
    packaging.log
```

To avoid unnecessary file churn, the manifest records original source paths.
For test exports, copying the source video into `source\source_video.mp4` is
acceptable because the output is a new folder and leaves protected artifacts
untouched.

## 4. HLS Export Strategy

Minimum HLS target:

- one video rendition playlist;
- one audio rendition playlist per language;
- `master.m3u8` with `EXT-X-MEDIA` alternate audio entries;
- language/name tags for each audio track;
- audio AAC segments under `hls\segments`;
- video segments under `hls\segments`.

Implementation approach:

1. Use ffmpeg to segment copied source video into `video.m3u8` without audio.
2. Use ffmpeg to segment each packaged AAC track into `audio_<lang>.m3u8`.
3. Write `master.m3u8` with alternate-audio declarations.
4. Validate that the referenced playlists and segment files exist.

The first version is a packaging proof, not adaptive bitrate streaming. It will
document player compatibility limits and avoid claiming universal playback.

## 5. Multi-Audio MP4 Strategy

Optional MP4 target:

```text
mp4\multilingual_muxed.mp4
```

Use ffmpeg to map:

- `0:v:0` from source video;
- one audio stream per packaged language AAC;
- no source overwrite;
- language metadata such as `fra` and `kan`;
- default disposition on the first selected language;
- `-shortest` to avoid long-tail duration mismatch.

The first version will not include original English audio unless explicitly
provided as a track. This keeps the CLI simple and avoids guessing whether
source audio should be treated as an export track.

## 6. Manifest Schema

`metadata\multilingual_manifest.json` will include:

```json
{
  "export_id": "official_fr_kn_test",
  "created_at": "2026-05-05T00:00:00+00:00",
  "source_video": {
    "path": "source/source_video.mp4",
    "original_path": "Vidiolingua_Test_Official.mp4",
    "duration_sec": 30.5,
    "hash": "sha256:..."
  },
  "languages": [
    {
      "language": "fr",
      "display_name": "French",
      "audio_track_path": "audio/fr.aac",
      "source_audio_path": "outputs/french_official_test/tts/output/Vidiolingua_Test_Official_transcription_fr.wav",
      "source_result_folder": "outputs/french_official_test",
      "translation_backend": "google",
      "voice_backend": "xtts",
      "voice_mode": "speaker-reference voice",
      "is_exact_clone": false,
      "validation_status": "passed",
      "duration_sec": 30.5,
      "sample_rate": 44100,
      "channels": 2
    },
    {
      "language": "kn",
      "display_name": "Kannada",
      "audio_track_path": "audio/kn.aac",
      "source_audio_path": "outputs/kannada_sarvam_practical_test_clipfix/tts/output/Vidiolingua_Test_Official_transcription_kn.wav",
      "source_result_folder": "outputs/kannada_sarvam_practical_test_clipfix",
      "translation_backend": "indictrans2",
      "voice_backend": "sarvam",
      "voice_mode": "managed-indian-tts",
      "is_exact_clone": false,
      "validation_status": "passed",
      "duration_sec": 30.5,
      "sample_rate": 44100,
      "channels": 2
    }
  ],
  "exports": {
    "hls_master": "hls/master.m3u8",
    "multi_audio_mp4": "mp4/multilingual_muxed.mp4"
  },
  "commands": [],
  "warnings": [],
  "errors": []
}
```

XTTS wording must stay cautious: it is a speaker-reference voice route, not a
guaranteed exact identity clone. Sarvam must always be labeled managed
Indian-language TTS with `is_exact_clone=false`.

## 7. Files To Add/Modify

Add:

- `tools\create_multilingual_export.py`
- `docs\MULTILINGUAL_AUDIO_EXPORT_PLAN_2026-05-05.md`
- `docs\MULTILINGUAL_AUDIO_EXPORT_REPORT_2026-05-05.md`
- `NEW_Frontend\app\multilingual-export\page.tsx`

Likely modify:

- `backend\main.py` for safe additive export endpoints, if small enough.
- `NEW_Frontend\lib\api.ts` and `NEW_Frontend\lib\types.ts` for optional API
  types.
- `NEW_Frontend\components\vidiolingua\site-navigation.tsx` for `OTT Export`.
- `NEW_Frontend\app\page.tsx` and/or `NEW_Frontend\app\architecture\page.tsx`
  to surface the differentiator.
- `NEW_Frontend\app\results\page.tsx` to show export metadata when present.
- `docs\PROJECT_PIPELINE.md`
- `docs\FRONTEND_BACKEND_INTEGRATION_READINESS_2026-04-29.md`
- `docs\JOB_MANIFEST_ORCHESTRATION_REPORT_2026-05-05.md`
- `README.md`
- `COMMAND_LOG.md`

## 8. How This Stays Additive

- Existing single-language CLI/API runs keep their current stage order.
- No ASR, translation, TTS, lip-sync, model loading, or batch generation is
  invoked by the packaging tool.
- All generated files go under `outputs\multilingual_exports\<export_id>`.
- Protected source outputs are read-only inputs.
- The manifest records paths and warnings rather than changing legacy
  `pipeline_result.json` files.
- API endpoints, if added, are new `/api/multilingual-export` routes.

## 9. Validation Plan

Light backend validation:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app asr translation tts voice workers tools evaluation
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.create_multilingual_export --help
```

Packaging proof:

```powershell
.\.venv_api\Scripts\python.exe -m tools.create_multilingual_export --source-video Vidiolingua_Test_Official.mp4 --track fr=outputs\french_official_test\tts\output\Vidiolingua_Test_Official_transcription_fr.wav --track kn=outputs\kannada_sarvam_practical_test_clipfix\tts\output\Vidiolingua_Test_Official_transcription_kn.wav --output-dir outputs\multilingual_exports\official_fr_kn_test --create-hls --create-mp4
```

Expected checks:

- manifest exists;
- `audio\fr.aac` and `audio\kn.aac` exist;
- `hls\master.m3u8` exists when HLS is requested;
- `mp4\multilingual_muxed.mp4` exists when MP4 is requested;
- ffprobe sees one video stream and at least two audio streams in the MP4;
- language tags are present where ffmpeg writes them.

Frontend validation:

```powershell
cd D:\Vidiolingua\NEW_Frontend
corepack pnpm run lint
corepack pnpm run build
```

## 10. Risks And Rollback Notes

Risks:

- Alternate-audio HLS support varies by player.
- MP4 audio-track language tags are container/player dependent.
- Source video and TTS WAV durations may drift slightly.
- Historical proof jobs have limited `pipeline_result.json` route metadata, so
  the tool may infer route labels from known folder/language conventions.

Rollback:

- Delete the new export folder under `outputs\multilingual_exports`.
- Remove the new tool and frontend route.
- Existing single-language outputs and model files require no restoration
  because they are not mutated.

## 11. What Will Not Be Implemented In This Phase

- No multi-language generation batch runner.
- No ASR/translation/TTS/lip-sync reruns.
- No local IndicF5 load or enablement.
- No Indic Parler integration.
- No generic fallback.
- No dependency installation.
- No cloud storage/CDN upload.
- No adaptive bitrate ladder.
- No hls.js preview player yet.
- No subtitles/captions packaging yet.
- No automatic player compatibility guarantee.
