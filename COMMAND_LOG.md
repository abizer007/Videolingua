# Command Log

## 2026-05-14 - Optional source-language captions

Commands run:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend tools
.\.venv_api\Scripts\python.exe -m tools.validate_source_captions --report outputs\validation\source_language_captioning_2026-05-14.json
corepack pnpm run lint
corepack pnpm run build
```

Results:

- Backend/tools compile passed.
- Source-caption validator passed and wrote `outputs\validation\source_language_captioning_2026-05-14.json`.
- Frontend lint passed.
- Frontend build passed.
- Browser smoke confirmed the upload page renders the captions checkbox and it is unchecked by default.
- Browser result-page seeding through a `javascript:` URL was blocked by the in-app browser security policy, so no browser-side fake-result preview was performed.

Safety notes:

- No dependency install is required.
- No Python virtual environment was mutated.
- No full video pipeline was run.
- Protected outputs were not overwritten.

## 2026-05-07 - Job lifecycle cache and cleanup hardening

Commands run:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend translation workers tools
.\.venv_api\Scripts\python.exe -m tools.validate_job_lifecycle_cleanup --output outputs\validation\job_lifecycle_cleanup_report.json
.\.venv_api\Scripts\python.exe -m tools.validate_indictrans2_translation --source-language en --target-language kn --text "This is a test of the translation system." --output outputs\validation\indictrans2_after_lifecycle_fix.json
.\.venv_api\Scripts\python.exe -m tools.validate_translation_router --source-language en --target-language kn --text "This is a test of the translation system." --output outputs\validation\router_translation_after_lifecycle_fix.json
corepack pnpm run lint
corepack pnpm run build
```

Results:

- Backend compile passed.
- Lifecycle validation passed.
- IndicTrans2 smoke passed with `engine=indictrans2`, `used_indictrans2=true`, `fallback_used=false`.
- Translation router smoke passed with `selected_engine=indictrans2`, `fallback_blocked=true`.
- Frontend lint passed after rerun with permission to read Corepack pnpm cache.
- Frontend build passed.

Safety notes:

- No dependency install was run.
- No Python virtual environment was mutated.
- No full video pipeline was run.
- Local IndicF5 was not run.
- Protected outputs and `models\xtts_v2` were not touched.

## 2026-05-13 - Visual lip-sync / Wav2Lip safe routing fix

Commands run:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend lipsync tts tools evaluation
.\.venv_api\Scripts\python.exe -m tools.validate_wav2lip_runtime --output outputs\validation\wav2lip_runtime_preflight.json
ffmpeg -y -f lavfi -i sine=frequency=440:duration=1 -acodec pcm_s16le -ar 22050 -ac 1 outputs\validation\test_speaker_ref.wav
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference outputs\validation\test_speaker_ref.wav --cloning-required true --output outputs\validation\wav2lip_safe_router_fr.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "<Kannada test text>" --target-language kn --reference outputs\validation\test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\wav2lip_safe_router_kn.wav --dry-run
corepack pnpm run lint
corepack pnpm run build
```

Additional lightweight mux validation generated synthetic media under:

```text
outputs\validation\wav2lip_mux_validation_20260513
```

Results:

- Backend/lipsync/TTS/tools/evaluation compile passed.
- Wav2Lip preflight passed and selected `.venv_tts\Scripts\python.exe`.
- Wav2Lip checkpoint was found at `ml\Wav2Lip\checkpoints\wav2lip_gan.pth`.
- Required imports were available: numpy, torch, cv2, scipy.
- Torch version was `2.5.1+cpu`; CUDA was not available.
- French router dry-run selected XTTS.
- Kannada router dry-run selected Sarvam.
- IndicF5 was not selected.
- Generic fallback was not selected.
- ffmpeg mux-only smoke preserved 3.0s video duration by padding 1.0s audio to 3.0s.
- Frontend lint passed.
- Frontend build passed.

Safety notes:

- No dependency install was run.
- No Python virtual environment was mutated.
- No full video pipeline was run.
- No real Wav2Lip generation was run.
- Local IndicF5 was not run.
- Protected outputs and `models\xtts_v2` were not touched.
- No secrets were exposed.

## 2026-05-08 - Reference audio auto-extract and Sarvam voice profile fix

Commands run:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend tts voice speaker_analysis tools
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Router dry run" --target-language fr --cloning-required true --output outputs\validation\router_fr_missing_reference_policy.wav --policy-only
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_speaker_plan --speaker-map jobs\04d211c5-81cc-4324-b2b8-eb18df0eac63\speaker_analysis\speaker_segment_map.json --target-language kn --output outputs\validation\sarvam_voice_plan_reference_mode_fix_computed.json
corepack pnpm run lint
corepack pnpm run build
```

Additional focused API validation called the FastAPI upload endpoint directly
with the background pipeline mocked, covering `kn` with `reference_mode=none`,
`kn` with `reference_mode=auto_extract`, `fr` with `reference_mode=none`, and
`fr` with `reference_mode=auto_extract`. FastAPI `TestClient` was not used
because the local API venv does not have optional `httpx` installed.

Results:

- Sarvam Kannada accepted `reference_mode=none`.
- Sarvam Kannada accepted `reference_mode=auto_extract`.
- XTTS French blocked `reference_mode=none` with the expected clear error.
- XTTS French accepted `reference_mode=auto_extract` for later extraction.
- Voice router policy-only validation also blocked French XTTS with no
  reference path, as expected.
- Sarvam voice-plan validation produced a computed Kannada plan with
  `voice_profile_hint=unknown`, `hint_source=unknown`, and selected voice
  `shubh`.
- Frontend lint passed after rerun with permission to read Corepack pnpm cache.
- Frontend build passed.
- Backend compile passed.

Safety notes:

- No dependency install was run.
- No Python virtual environment was mutated.
- No full video pipeline was run.
- Local IndicF5 was not run.
- Protected outputs and `models\xtts_v2` were not touched.
