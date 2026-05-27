# Final Backend Handoff Before Frontend - 2026-04-29

## What Works

- French practical pipeline with XTTS works.
- Kannada practical pipeline works with ASR -> IndicTrans2 -> Sarvam ->
  lipsync/mux.
- Sarvam AI is integrated as managed Indian-language TTS.
- IndicTrans2 EN->KN works locally.
- Backend CLI validation tools are in place.
- Backend result files can be served through `/api/result/{job_id}/file/{name}`.

## Protected

- `.venv_tts`
- `.venv_indictrans2`
- `models\xtts_v2`
- `outputs\french_official_test`
- `outputs\kannada_sarvam_practical_test_clipfix`
- `backend\.env` secrets

## Disabled

- IndicF5 local execution: `false/local_disabled`
- Indic Parler: forbidden
- Generic fallback when cloning/strict practical behavior is required

## French XTTS Status

Known-good MP4:

```text
outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4
```

ffprobe: H.264 1920x1080 30 fps, AAC 44.1 kHz stereo, duration about 30.57s.

## Kannada Sarvam Status

Known-good MP4:

```text
outputs\kannada_sarvam_practical_test_clipfix\results\Vidiolingua_Test_Official_dubbed_kn.mp4
```

ffprobe: H.264 1920x1080 30 fps, AAC 44.1 kHz stereo, duration about 30.66s.

Sarvam is managed Indian-language TTS. It is not exact voice cloning.

## Security Summary

No confirmed secret leak was found. `backend\.env` is ignored and untracked.
Docs, command log, env example, and output text artifacts did not contain the
full Sarvam key.

## Routing Summary

- `kn -> Sarvam`
- `hi -> Sarvam`
- `fr -> XTTS`
- `en -> kn translation -> IndicTrans2`

## Output Artifact Summary

French and Kannada final MP4s exist and include both audio and video streams.
Kannada TTS WAV, translation JSON, and pipeline result JSON exist.

## Frontend Readiness Summary

Backend has upload/status/result/file-serving endpoints and frontend-next already
has a matching API client, polling hook, upload page, and results page.

Before user-facing frontend testing, update:

- backend upload language allowlist to include Kannada and other Sarvam regional
  languages
- frontend language dropdown to include Sarvam regional languages
- voice option defaults/copy so Sarvam is described honestly as managed TTS

## Validation Commands

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app workers
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\router_kn.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_translation_router --source-language en --target-language kn --text "This is a test." --output outputs\validation\translation_en_kn.json
```

## Commands Not To Run

```text
Do not run local IndicF5 model load/generation.
Do not reinstall torch.
Do not mutate .venv_tts.
Do not mutate .venv_indictrans2.
Do not overwrite protected French/Kannada output folders.
Do not run batch languages without explicit approval.
Do not commit backend\.env or any local .env.
```

## Known Risks

- Frontend upload allowlist currently blocks Kannada via UI/backend upload route.
- Frontend default `cloned=false` may not match strict practical backend policy.
- In-memory job store loses status on backend restart.
- No dedicated supported-language metadata endpoint yet.

## Next Recommended Frontend Tasks

1. Add backend-supported language metadata or update upload allowlist directly.
2. Update frontend language dropdown for XTTS and Sarvam languages.
3. Replace “clone voice” copy for Sarvam with managed-TTS copy.
4. Test real API upload for French and Kannada using new output/job folders.
5. Add frontend display of backend choice: XTTS vs Sarvam.
