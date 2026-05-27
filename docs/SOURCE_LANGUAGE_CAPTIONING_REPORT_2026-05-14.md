# Source-Language Captioning Report - 2026-05-14

## Feature summary

VideoLingua now supports optional original/source-language caption sidecars for translated and dubbed video runs. When enabled at upload time, the backend formats the original ASR transcript segments into WebVTT and SRT files. The caption text is not translated.

## Checkbox UI behavior

The upload page includes an unchecked-by-default checkbox:

- Label: Add original-language captions
- Description: Captions are generated from the original ASR transcript and shown over the translated video.

When checked, the frontend sends `includeCaptions=true`. When unchecked, it sends `includeCaptions=false`, and the pipeline keeps the existing no-caption behavior.

## Backend request field

The upload endpoint accepts the optional multipart field:

```text
includeCaptions: "true" | "false"
```

For compatibility with the existing run options contract, the value is also mirrored into `voiceOptions.includeCaptions` and `voiceOptions.captionsRequested`. Missing values default to `false`.

## Caption artifact paths

For API jobs, caption sidecars are written under:

```text
jobs\<job_id>\captions\source_original.vtt
jobs\<job_id>\captions\source_original.srt
```

They are registered in `job_manifest.json` as:

```text
source_original_vtt
source_original_srt
```

## Result payload shape

New result payloads expose the request flag and caption metadata:

```json
{
  "jobId": "...",
  "captionsRequested": true,
  "captions": [
    {
      "kind": "subtitles",
      "format": "vtt",
      "languageCode": "en",
      "label": "Original-language captions",
      "source": "asr_original",
      "url": "http://localhost:8000/api/result/<job_id>/file/source_original.vtt"
    },
    {
      "kind": "subtitles",
      "format": "srt",
      "languageCode": "en",
      "label": "Original-language captions download",
      "source": "asr_original",
      "url": "http://localhost:8000/api/result/<job_id>/file/source_original.srt"
    }
  ],
  "localizedVideos": [
    {
      "language": "French",
      "url": "http://localhost:8000/api/result/<job_id>/file/<dubbed>.mp4",
      "captions": [
        {
          "kind": "subtitles",
          "format": "vtt",
          "languageCode": "en",
          "label": "Original-language captions",
          "source": "asr_original",
          "url": "http://localhost:8000/api/result/<job_id>/file/source_original.vtt"
        }
      ]
    }
  ]
}
```

Each localized video receives the same caption metadata when captions are available.

## Files changed

- `NEW_Frontend/app/upload/page.tsx`
- `NEW_Frontend/lib/api.ts`
- `NEW_Frontend/lib/types.ts`
- `NEW_Frontend/components/vidiolingua/result-video-card.tsx`
- `NEW_Frontend/app/results/page.tsx`
- `backend/main.py`
- `backend/pipeline_runner.py`
- `backend/job_store.py`
- `backend/job_manifest.py`
- `backend/captions.py`
- `tools/validate_source_captions.py`
- `COMMAND_LOG.md`

## Validation commands

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend tools
.\.venv_api\Scripts\python.exe -m tools.validate_source_captions --report outputs\validation\source_language_captioning_2026-05-14.json
corepack pnpm run lint
corepack pnpm run build
```

Validation status:

- Backend/tools compile passed.
- Source-caption validator passed.
- Frontend lint passed.
- Frontend build passed.
- Browser smoke confirmed the upload page renders the caption checkbox unchecked by default.
- A no-backend fake result-page browser preview was not completed because the in-app browser blocked the localStorage seeding URL under its security policy.

## Limitations

- Captions are ASR-derived and may contain recognition errors.
- Captions are original/source-language captions, not translated subtitles.
- Captions are shown as frontend video subtitle tracks and downloadable sidecar files.
- Captions are not burned into the MP4 by default.
- Caption accuracy is not human-verified.

## Future option

Burn captions into MP4 can be a later setting if needed. That mode would require FFmpeg subtitle rendering and should create a separate output file rather than overwrite the normal dubbed MP4.
