# XTTS Quality A/B Hybrid Application - 2026-04-28

## Summary

Applied one conservative global XTTS quality improvement based on manual A/B feedback:

- Preset A had better naturalness/energy.
- Preset B had better stability/consistency.
- The chosen hybrid keeps more of A's liveliness while moving toward B's safer generation behavior.

This is an inference-time quality preset only. No training, fine-tuning, dependency changes, CUDA enablement, model replacement, or large A/B batch was performed.

## Files Changed

Source/config files changed:

- `voice/xtts_cloner.py`
- `app/services/xtts_tts_service.py`
- `tts/run_tts.py`
- `lipsync/run_lipsync.py`
- `backend/pipeline_runner.py`
- `backend/.env`

Docs created:

- `docs/REFERENCE_AUDIO_FINAL_RECOMMENDATION_2026-04-28.md`
- `docs/DURATION_AND_SPEED_DIAGNOSTICS_2026-04-28.md`
- `docs/XTTS_QUALITY_AB_HYBRID_APPLICATION_2026-04-28.md`

Audio/output created:

- `outputs/reference_audio_tuning_2026-04-28/reference_best_candidate.wav`
- `outputs/french_quality_ab_hybrid_test/results/Vidiolingua_Test_Official_dubbed_fr.mp4`
- `outputs/french_quality_ab_hybrid_test_052/results/Vidiolingua_Test_Official_dubbed_fr.mp4`

Note: `outputs/french_quality_ab_hybrid_test` was the first regression run. It preserved an existing `backend/.env` temperature value of `0.65`. After updating config to the intended hybrid temperature, the corrected regression was written to `outputs/french_quality_ab_hybrid_test_052` to avoid overwriting the first new output.

## Backups Created

Backups were created before editing:

- `_snapshots/quality_ab_hybrid_20260428_source_backups/voice__xtts_cloner.py`
- `_snapshots/quality_ab_hybrid_20260428_source_backups/tts__run_tts.py`
- `_snapshots/quality_ab_hybrid_20260428_source_backups/lipsync__run_lipsync.py`
- `_snapshots/quality_ab_hybrid_20260428_source_backups/backend__pipeline_runner.py`
- `_snapshots/quality_ab_hybrid_20260428_source_backups/app__services__xtts_tts_service.py`
- `_snapshots/quality_ab_hybrid_20260428_source_backups/backend__.env`

## Settings

| Setting | Old default / baseline | Preset A | Preset B | New A/B hybrid |
| --- | ---: | ---: | ---: | ---: |
| Temperature | 0.65 | 0.65 | 0.45 | 0.52 |
| Repetition penalty | 10.0 | 10.0 | 8.0 | 8.5 |
| Max chars | 200 | 200 | 180 | 180 |
| Crossfade ms | 12.0 | 12.0 | 25.0 | 25.0 |

The active global defaults are now env/configurable:

```text
VIDIOLINGUA_XTTS_TEMP=0.52
VIDIOLINGUA_XTTS_REPETITION_PENALTY=8.5
VIDIOLINGUA_XTTS_MAX_CHARS=180
VIDIOLINGUA_XTTS_CROSSFADE_MS=25.0
```

Rollback values:

```text
VIDIOLINGUA_XTTS_TEMP=0.65
VIDIOLINGUA_XTTS_REPETITION_PENALTY=10.0
VIDIOLINGUA_XTTS_MAX_CHARS=200
VIDIOLINGUA_XTTS_CROSSFADE_MS=12.0
```

## Reference Audio Changes

`test_speaker_ref.wav` was not overwritten.

An optional tuned reference was created at:

`outputs/reference_audio_tuning_2026-04-28/reference_best_candidate.wav`

It trims obvious leading/trailing silence and applies gentle peak gain only. It passes XTTS reference validation:

| Metric | Original | Tuned candidate |
| --- | ---: | ---: |
| Duration | 10.000 s | 7.859 s |
| Sample rate | 22050 Hz | 24000 Hz |
| Peak | 0.539337 | 0.638611 |
| RMS | 0.028087 | 0.037490 |
| Silence ratio | 0.519520 | 0.356322 |
| Clipping ratio | 0.000000 | 0.000000 |

The corrected regression still used `test_speaker_ref.wav` to stay comparable with the known-good command.

## Chunking And Crossfade

Changes:

- Global `max_chars` fallback is now 180.
- Global `crossfade_ms` fallback is now 25.0.
- Tiny internal chunks are merged with the previous chunk when it fits within `max_chars`.
- Chunk logs now include chunk index, text length, generated duration, peak, and RMS.

No broad sentence restructuring was added.

## Post-Processing

Existing safe cleanup remains:

- Decode generated audio.
- Remove NaN/inf.
- Gentle peak normalization only when peak exceeds the safe ceiling.
- Crossfade joins.
- Strict final validation.

Added optional loudness normalization behind disabled-by-default env flags:

```text
VIDIOLINGUA_AUDIO_LOUDNESS_NORMALIZE=false
VIDIOLINGUA_AUDIO_TARGET_LUFS=-16
```

This was not enabled for the regression.

## Duration And Speed Diagnostics

Diagnostics were added to TTS, lipsync, and pipeline runner logs.

Corrected regression observations:

- Original video duration: 30.67 s.
- Generated TTS duration: 30.68 s.
- Final MP4 duration: 30.67 s.
- Final MP4/video difference: +0.00 s.
- Lipsync ffmpeg mux speedup applied: false.
- TTS per-segment atempo applied: true.

Warning observed:

- One translated TTS segment required speedup ratio about 1.69. This can make speech feel rushed even when final duration aligns.

## Validation Results

Passed:

- `.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app`
- `.\.venv_tts\Scripts\python.exe -c "from transformers import BeamSearchScorer; print('BeamSearchScorer import OK')"`
- Torch check: `torch 2.5.1+cpu`, CUDA false, CUDA version none, GPU none.
- XTTS model file check: `models/xtts_v2` contains `model.pth`, `config.json`, `vocab.json`, `hash.md5`, and `speakers_xtts.pth`.
- Corrected one-language practical regression passed.

Corrected final test MP4:

`outputs/french_quality_ab_hybrid_test_052/results/Vidiolingua_Test_Official_dubbed_fr.mp4`

Corrected final TTS WAV objective metrics:

| Metric | Value |
| --- | ---: |
| Duration | 30.675692 s |
| Sample rate | 22050 Hz |
| Peak | 0.968506 |
| RMS | 0.092091 |
| Silence ratio | 0.317693 |
| Clipping ratio | 0.000000 |

## Preservation Confirmations

- No dependency installs were run.
- No venvs were replaced or modified.
- `models/xtts_v2` was not modified.
- `outputs/french_official_test/results/Vidiolingua_Test_Official_dubbed_fr.mp4` was preserved, length `78499361`, timestamp `2026-04-28 18:55:26`.
- Known-good output folder `outputs/french_official_test` was not deleted.
- No full multi-language pipeline run was performed.
- No training or fine-tuning was performed.
- CUDA was not enabled.

## Final Note

Exact speaker replication cannot be guaranteed with this XTTS inference-only pipeline. Meaningful further gains in speaker similarity likely require better reference audio, model fine-tuning, or a stronger voice-cloning model.

This change is intended to improve consistency, clarity, and stability while preserving the current working pipeline shape.
