# VidioLingua Project Repair Plan

Created: 2026-04-29
Workspace: `D:\Vidiolingua`

This plan is the Phase 1 gate for the safe repair effort. Runtime source code must not be edited until this file exists. The current known-good XTTS practical pipeline and `outputs\french_official_test` are protected artifacts.

## 1. Current Repository Structure

Top-level runtime areas:

- `backend/`: FastAPI job orchestration and `pipeline_runner.py`.
- `asr/`: WhisperX/faster-whisper transcription stage.
- `translation/`: current segment translation script.
- `tts/`: current segment TTS assembly script.
- `voice/`: strict XTTS cloning, reference audio prep, and audio validation helpers.
- `app/`: FastAPI routers and service wrappers for TTS engines.
- `lipsync/`: MuseTalk/Wav2Lip/SadTalker/ffmpeg mux stage plus UVR/BGM helpers.
- `tools/`: existing preflight and XTTS validation utilities.
- `docs/`: working-state and XTTS repair documents.
- `models/xtts_v2/`: local Coqui XTTS v2 model directory.
- `outputs/french_official_test/`: known-good French XTTS practical output.
- `_snapshots/`: previous safe snapshots and backups.
- `ml/Wav2Lip/` and `ml/IndicF5/`: local ML asset/source folders.

Important gaps:

- No `workers/` package currently exists.
- No structured `translation/base.py`, `translation/router.py`, or translation engine package exists.
- `voice/` exists but does not yet contain the requested shared voice contracts/router/engine structure.
- Several docs requested for Phase 2 do not yet exist.

## 2. Current Active Virtual Environments

Observed local environments:

| Environment | Python | Role | Notes |
| --- | --- | --- | --- |
| `.venv_api` | 3.11.11 | FastAPI/orchestration | Lightweight; no torch/TTS/deep-translator installed. |
| `.venv_asr` | 3.11.11 | ASR | WhisperX stack with torch 2.8.0. |
| `.venv_tts` | 3.11.11 | Known-good XTTS CPU TTS | Must not be mutated. |
| `.venv_bgm` | 3.11.11 | Demucs/BGM | Separate torch 2.11.0 environment. |
| `.venv_indicf5` | 3.12.13 | Intended IndicF5 | Currently incomplete: torch, transformers, huggingface-hub, soundfile, vocos, cached-path, datasets, numpy missing. |
| `.venv`, `.venv311` | present | legacy/unknown | Not part of the current known-good split. |

## 3. Current Dependency Versions For Key Envs

`.venv_api`:

- `fastapi 0.136.1`
- `uvicorn 0.46.0`
- `requests 2.33.1`
- `deep-translator`, `torch`, `transformers`, `TTS`, `whisperx`, `faster-whisper`, `soundfile`, `numpy`: not installed

`.venv_tts` known-good XTTS baseline:

- `torch 2.5.1+cpu`
- `torchaudio 2.5.1+cpu`
- `TTS 0.22.0`
- `transformers 4.46.3`
- `tokenizers 0.20.3`
- `deep-translator 1.11.4`
- `gTTS 2.5.4`
- `soundfile 0.13.1`
- `numpy 1.26.4`
- `safetensors 0.7.0`
- `huggingface-hub`: not installed

`.venv_asr`:

- `torch 2.8.0`
- `torchaudio 2.8.0`
- `whisperx 3.8.5`
- `faster-whisper 1.2.1`
- `numpy 2.4.4`
- `soundfile 0.13.1`

`.venv_bgm`:

- `torch 2.11.0`
- `torchaudio 2.11.0`
- `demucs 4.0.1`
- `numpy 2.4.4`
- `soundfile 0.13.1`

`.venv_indicf5`:

- `torchaudio 2.11.0`
- `safetensors 0.7.0`
- Key IndicF5 runtime dependencies missing. This environment should be repaired separately only after approval.

## 4. Current Pipeline Map

The current practical path is:

1. `backend.pipeline_runner` creates a job directory and copies the input video.
2. Optional UVR/Demucs BGM separation runs when enabled.
3. ASR stage calls `.venv_asr` and `asr/run_asr.py`.
4. ASR extracts 16 kHz mono WAV with ffmpeg, runs WhisperX, and may fall back to faster-whisper.
5. Pipeline creates ASR-guided speaker reference WAVs, or uses the user-provided reference.
6. Translation stage calls `.venv_tts` and `translation/run_translate.py`.
7. Translation writes per-language translated JSON while preserving segment timestamps.
8. TTS stage calls `.venv_tts` and `tts/run_tts.py`.
9. TTS synthesizes each segment, time-stretches to the source segment duration, concatenates WAV segments, and validates final WAV.
10. Lip-sync stage calls API/MuseTalk runtime and `lipsync/run_lipsync.py`.
11. Lip-sync tries MuseTalk/SadTalker/Wav2Lip/ffmpeg depending on env config, then optionally GFPGAN/BGM remix.
12. Final MP4 and `pipeline_result.json` are written under the job output folder.

## 5. Current Translation Flow

Current `translation/run_translate.py`:

- Defaults to `VIDIOLINGUA_TRANSLATION_ENGINE=llama3` unless env overrides it.
- Accepts only `llama3` or `google`.
- Uses Ollama/Llama for segment-level translation when selected.
- Uses `deep_translator.GoogleTranslator` for Google/deep-translator translation.
- Allows Google fallback from Llama only when `VIDIOLINGUA_TRANSLATION_ALLOW_GOOGLE_FALLBACK=true`.
- Preserves segment `start`, `end`, `speaker`, and `words`.

Current `backend/.env` sets `VIDIOLINGUA_TRANSLATION_ENGINE=google`, so the known-good French run used the Google/deep-translator path through `.venv_tts`.

## 6. Where Llama/Ollama Is Used

- `translation/run_translate.py` defines `_translate_llama3()`.
- It calls `POST {OLLAMA_BASE_URL}/api/generate` with model `OLLAMA_MODEL` defaulting to `llama3`.
- It is currently a translation engine, not only a reasoning/planning backend.

## 7. Where deep-translator Is Used

- `translation/run_translate.py` imports `deep_translator.GoogleTranslator` inside `_translate_google()`.
- `backend/main.py` health check probes `deep_translator` in the API env.
- `.venv_tts` has `deep-translator 1.11.4`.
- `requirements-tts.txt` and `requirements-indicf5.txt` include deep-translator.

## 8. Translation Bypass Risk

Risk is present:

- IndicTrans2 does not exist in the current runtime path.
- Supported Indic pairs would currently go to Google/deep-translator if env is `google`.
- If env is unset, supported Indic pairs would currently go to Llama/Ollama.
- There is no central supported-language/pair policy preventing Llama or deep-translator from bypassing IndicTrans2.

## 9. Current TTS / Voice Cloning Flow

Current TTS path:

- `backend.pipeline_runner` sets cloning-required env flags in practical/strict modes.
- `tts/run_tts.py` selects engine based on env, target language, and reference availability.
- For XTTS-supported languages with cloning required, `tts/run_tts.py` calls `app.services.xtts_tts_service`.
- `app.services.xtts_tts_service` calls `voice.xtts_cloner.clone_voice()`.
- `voice.xtts_cloner` loads local XTTS model files and passes `speaker_wav` and `language` to Coqui.
- `app.services.indicf5_tts_service` already exists as a direct service, but it is not isolated in a separate worker and `.venv_indicf5` is not ready.
- Legacy Hume, ElevenLabs, and gTTS paths remain in `tts/run_tts.py` and `app/routers/tts_router.py`.

## 10. Where XTTS Is Used

- `voice/xtts_cloner.py`
- `app/services/xtts_tts_service.py`
- `tts/run_tts.py`
- `backend/pipeline_runner.py`
- `tools/validate_xtts_voice_cloning.py`
- `tests/test_xtts_voice_cloning.py`

## 11. Whether XTTS Receives `speaker_wav`

Yes in the strict clone path:

- `app/services/xtts_tts_service.py` requires `SPEAKER_REFERENCE_AUDIO`, `VIDIOLINGUA_VOICE_SAMPLE`, or a passed `speaker_wav`.
- `voice/xtts_cloner.py` calls `tts.tts_to_file(..., speaker_wav=str(cleaned_reference), language=lang, ...)`.
- Tests assert `speaker_wav` and `language` are passed.

## 12. Whether XTTS Uses Correct Language Code

Mostly yes:

- `voice.xtts_cloner.normalize_xtts_language()` normalizes and validates the base language code.
- `backend.pipeline_runner` sets `XTTS_LANGUAGE` to the target language.
- `tts/run_tts.py` reads target language from translated transcription JSON.

Potential issue:

- There are duplicate XTTS supported-language sets in `tts/run_tts.py`, `app/routers/tts_router.py`, and `voice/xtts_cloner.py`. They should be centralized.

## 13. Whether XTTS Silently Falls Back To Generic Voice

Mostly blocked in practical/strict flow:

- `backend.pipeline_runner` sets `ALLOW_GENERIC_TTS_FALLBACK=false` when cloning is required.
- `voice.xtts_cloner.clone_voice()` rejects `allow_generic_tts_fallback=True`.
- `tts.run_tts.synthesize_segment()` raises when cloning is required and XTTS fails.

Remaining risk:

- `tts/run_tts.py` still contains Hume, ElevenLabs, and gTTS fallback code.
- Some auto/config paths can return `legacy` when cloning is not required.
- `app/routers/tts_router.py` currently rejects non-XTTS cloning languages instead of routing Kannada/Hindi cloning to IndicF5.

## 14. Whether Old Cached Generic Audio Can Be Reused

Current risk is low in the known practical CLI because `VIDIOLINGUA_FORCE_VOICE_REGENERATE` defaults to true in `backend.pipeline_runner`.

But the architecture does not yet have a shared voice cache with keys that include:

- engine name
- model name
- target language
- target text hash
- reference audio hash
- reference text hash for IndicF5
- XTTS speaker WAV hash
- voice settings
- preprocessing version

This must be added before relying on reusable voice cache artifacts.

## 15. Current Audio Preprocessing Flow

- ASR extracts audio with ffmpeg at 16 kHz mono.
- Pipeline can extract clean voice samples using Demucs when enabled.
- ASR-guided speaker references are trimmed from video and concatenated.
- `voice/reference_audio.py` conservatively converts reference audio to mono PCM WAV and validates it.
- `voice/audio_validation.py` validates existence, decoding, duration, sample rate, peak/rms, silence, clipping, dropouts, and NaN/inf.
- `voice/xtts_cloner.py` writes raw XTTS WAV, normalizes near-clipped raw output, writes clean WAV, and validates final WAV.

## 16. Current Video / Lip-sync Flow

- `lipsync/run_lipsync.py` supports MuseTalk, SadTalker, Wav2Lip, ffmpeg mux, GFPGAN, and BGM remix.
- If no lip-sync model is configured, ffmpeg replaces the audio track.
- Failures in MuseTalk/SadTalker/Wav2Lip currently fall back to ffmpeg.
- BGM remix is optional through UVR/Demucs output.

## 17. SadTalker / MuseTalk / Wav2Lip Usage

- `VIDIOLINGUA_MUSETALK_DIR` activates MuseTalk.
- `VIDIOLINGUA_SADTALKER_DIR` activates SadTalker only when engine is `sadtalker`.
- `VIDIOLINGUA_WAV2LIP_DIR` activates Wav2Lip fallback.
- Current known-good run appears to use ffmpeg mux because Wav2Lip/MuseTalk dirs are blank.

## 18. Component Tangling Risk

Translation, TTS, and muxing are mostly stage-separated by subprocesses, but policy is tangled inside stage scripts:

- Translation routing and engine implementation are in one file.
- TTS routing, legacy fallback, per-segment timing, and engine implementation are in one file.
- Lip-sync includes mux, model fallback, GFPGAN, and BGM remix in one file.

The safe repair should add routers/contracts around existing functions before any large rewrite.

## 19. Where IndicF5 Should Be Integrated

Phase 2/3 target:

- `voice/base.py`: shared request/result contract.
- `voice/router.py`: strict voice selection policy.
- `voice/engines/indicf5_engine.py`: main-process adapter that validates request and calls a worker.
- `workers/indicf5_worker.py`: isolated IndicF5 subprocess entry point.
- `tools/validate_indicf5_voice.py` and `tools/validate_voice_router.py`: light validation commands.

Do not install IndicF5 packages into `.venv_tts`. Use `.venv_indicf5` after approval.

## 20. Where IndicTrans2 Should Be Integrated

Phase 2/3 target:

- `translation/base.py`: shared request/result contract.
- `translation/router.py`: strict translation selection policy.
- `translation/engines/indictrans2_engine.py`: adapter that validates source/target support and calls a worker.
- `workers/indictrans2_worker.py`: isolated IndicTrans2 subprocess entry point.
- `tools/validate_indictrans2_translation.py` and `tools/validate_translation_router.py`: validation commands.

Use IndicTrans2 for supported language pairs in `auto` mode. Llama/deep-translator must require explicit fallback/config when IndicTrans2 does not support the pair.

## 21. Dependency Isolation Strategy

Do not mutate:

- `.venv_api`
- `.venv_asr`
- `.venv_tts`
- `.venv_bgm`

Recommended future envs:

- `.venv_indictrans2` for IndicTrans2.
- `.venv_indicf5` for IndicF5, repaired/recreated only after approval.
- Optional `.venv_tts_gpu` for future CUDA XTTS experiments, never replacing `.venv_tts`.

Main app should import only light router/contracts at startup. Heavy model libraries should be imported only inside workers.

## 22. RTX 4050 / i5 Manageability

Policy to implement/document:

- Load one major model at a time.
- Keep ASR, translation, TTS, and lip-sync as separate subprocess stages.
- Use batch size 1 by default.
- Use CUDA/fp16 only in new isolated envs, not `.venv_tts`.
- Do not keep IndicTrans2 loaded while TTS/lip-sync runs.
- Prefer worker process exit over manual cleanup.
- Log device, dtype, CUDA availability, GPU name, and VRAM when available.

## 23. Exact Files Proposed For Modification

Phase 2 code scaffolding:

- `translation/__init__.py`
- `translation/base.py`
- `translation/router.py`
- `translation/engines/__init__.py`
- `translation/engines/indictrans2_engine.py`
- `translation/engines/llama_engine.py`
- `translation/engines/deep_translator_engine.py`
- `translation/validation/__init__.py`
- `translation/validation/translation_validation.py`
- `translation/cache/__init__.py`
- `translation/cache/translation_cache.py`
- `voice/base.py`
- `voice/router.py`
- `voice/engines/__init__.py`
- `voice/engines/xtts_engine.py`
- `voice/engines/indicf5_engine.py`
- `voice/validation/__init__.py`
- `voice/validation/audio_validation.py`
- `voice/validation/reference_validation.py`
- `voice/cache/__init__.py`
- `voice/cache/voice_cache.py`
- `workers/__init__.py`
- `workers/indictrans2_worker.py`
- `workers/indicf5_worker.py`
- `workers/xtts_worker.py`
- `tools/inspect_pipeline_config.py`
- `tools/validate_xtts_voice.py`
- `tools/validate_indicf5_voice.py`
- `tools/validate_voice_router.py`
- `tools/validate_indictrans2_translation.py`
- `tools/validate_translation_router.py`
- `tools/validate_full_text_to_voice.py`

Phase 2 docs:

- `docs/PROJECT_PIPELINE.md`
- `docs/VOICE_BACKENDS.md`
- `docs/TRANSLATION_BACKENDS.md`
- `docs/INDICF5_SETUP.md`
- `docs/INDICTRANS2_SETUP.md`
- `docs/RTX4050_LOCAL_SETUP.md`
- `docs/TROUBLESHOOTING.md`

Potential Phase 3 integration:

- `translation/run_translate.py`
- `tts/run_tts.py`
- `app/routers/tts_router.py`
- `backend/main.py`
- `backend/pipeline_runner.py`

Before editing any existing source file, create timestamped backups under `_snapshots/repair_YYYYMMDD_HHMMSS/`.

## 24. Exact Implementation Plan

Phase 2:

1. Add shared language policy constants for XTTS and IndicF5 in voice contracts/router.
2. Add shared translation contracts and IndicTrans2-supported language/pair policy.
3. Add router logic that enforces:
   - supported Indic pair -> IndicTrans2
   - unsupported pair -> explicit LLM/deep-translator fallback or loud failure
   - no silent fallback
4. Add voice router logic that enforces:
   - XTTS first for XTTS languages
   - IndicF5 for supported Indian languages when XTTS unsupported
   - no generic fallback unless non-cloning debug config explicitly allows it
5. Add cache key helpers for translation and voice.
6. Add validation tools that can run in dry-run/policy mode without downloading/loading huge models.
7. Add docs for pipeline, backend policy, setup, and troubleshooting.

Phase 3:

1. Add isolated IndicTrans2 worker after env commands are reviewed and approved.
2. Add isolated IndicF5 worker after env commands are reviewed and approved.
3. Wire `translation/run_translate.py` to the translation router while preserving segment JSON shape.
4. Wire `tts/run_tts.py` to the voice router while preserving the working XTTS segment assembly path.
5. Run light validation.
6. If XTTS runtime source changed, run a single French practical regression into a new output folder.

## 25. Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Breaking known-good XTTS CPU env | Do not install or upgrade `.venv_tts`; keep XTTS code path strict and backed up. |
| `models/xtts_v2/model.pth/model.pth` regression | Keep normalization in both pipeline and XTTS cloner; validate model directory in tools. |
| IndicF5 dependency conflict | Use `.venv_indicf5` worker, not `.venv_tts`. |
| IndicTrans2 dependency conflict | Use `.venv_indictrans2` worker, not `.venv_tts`. |
| Silent translation fallback | Router returns explicit metadata and raises on unsupported pairs without allowed fallback. |
| Silent generic TTS | Router raises when cloning is required and reference audio/text is missing. |
| Stale voice cache | Include engine/model/language/text/reference/settings hashes. |
| Low VRAM/OOM | One model per worker process, batch size 1, explicit device/dtype config. |
| Existing secrets in local env files | Do not print secret values in docs/logs; consider rotating separately. |

## 26. Validation Commands To Add

Add or preserve equivalents:

```powershell
python -m tools.inspect_pipeline_config
python -m tools.validate_indictrans2_translation --source-language en --target-language kn --text "This is a test of the translation system." --output outputs/validation/indictrans2_en_kn.json
python -m tools.validate_xtts_voice --text "This is a short test of the cloned speaker voice." --reference test_speaker_ref.wav --language en --model-path models\xtts_v2 --output outputs/validation/xtts_en.wav
python -m tools.validate_indicf5_voice --text "Kannada text here" --reference samples/reference_clean.wav --reference-text "Exact transcript of the reference audio." --language kn --output outputs/validation/indicf5_kn.wav
python -m tools.validate_voice_router --text "Kannada text here" --target-language kn --reference samples/reference_clean.wav --reference-text "Exact transcript of the reference audio." --cloning-required true --output outputs/validation/router_kn.wav
python -m tools.validate_translation_router --source-language en --target-language kn --text "This is a test of the translation system." --output outputs/validation/router_translation_en_kn.json
python -m tools.validate_full_text_to_voice --source-language en --target-language kn --text "This is a test of the full text to voice system." --reference samples/reference_clean.wav --reference-text "Exact transcript of the reference audio." --output outputs/validation/full_en_kn_voice.wav
```

Validation tools should support policy/dry-run mode when model envs are not installed.

## 27. How To Verify XTTS Still Works

Light checks:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app workers
.\.venv_tts\Scripts\python.exe -c "from transformers import BeamSearchScorer; print('BeamSearchScorer import OK')"
.\.venv_tts\Scripts\python.exe -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('cuda version:', torch.version.cuda); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
Get-ChildItem -Force models\xtts_v2
```

If runtime XTTS path changes, run one regression only:

```powershell
.\.venv_api\Scripts\python.exe -m backend.pipeline_runner --video Vidiolingua_Test_Official.mp4 --target-language fr --reference test_speaker_ref.wav --model-path models\xtts_v2 --mode practical --output-dir outputs\french_after_router_refactor_test
```

Never overwrite `outputs\french_official_test`.

## 28. How To Verify No Indic Parler Usage Exists

Use:

```powershell
rg -n "parler|Parler|indic-parler|Indic Parler|parler-tts" .
```

Expected after repair:

- No runtime imports.
- No requirements entries.
- Docs only mention it as forbidden/not used.

Current first-pass grep found no positive runtime use of Indic Parler in the inspected core files.
