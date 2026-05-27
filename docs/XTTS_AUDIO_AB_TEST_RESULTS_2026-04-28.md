# XTTS Audio A/B Test Results - 2026-04-28

This A/B test was run before changing pipeline defaults. The goal was to generate a small set of French XTTS-only WAV samples from existing translated text so the final choice can be made by manual listening.

No ASR, translation, lipsync, muxing, or full video pipeline run was performed.

## Source Artifacts

| Artifact | Path |
| --- | --- |
| Translation JSON | `outputs/french_official_test/translation/output/Vidiolingua_Test_Official_transcription_fr.json` |
| ASR JSON | `outputs/french_official_test/asr/output/Vidiolingua_Test_Official_transcription.json` |
| TTS input JSON | `outputs/french_official_test/tts/input/Vidiolingua_Test_Official_transcription_fr.json` |
| Current generated TTS WAV | `outputs/french_official_test/tts/output/Vidiolingua_Test_Official_transcription_fr.wav` |
| Pipeline result | `outputs/french_official_test/pipeline_result.json` |
| Preserved known-good video | `outputs/french_official_test/results/Vidiolingua_Test_Official_dubbed_fr.mp4` |

## Presets

| Preset | Temperature | Repetition penalty | Max chars | Crossfade ms |
| --- | ---: | ---: | ---: | ---: |
| A - current baseline | 0.65 | 10.0 | 200 | 12.0 |
| B - more stable voice | 0.45 | 8.0 | 180 | 25.0 |
| C - clearer articulation | 0.50 | 7.0 | 160 | 30.0 |
| D - smoother longer prosody | 0.55 | 8.5 | 240 | 35.0 |
| E - low drift | 0.35 | 6.5 | 140 | 40.0 |

## Output Paths

| Preset | Combined WAV | Report JSON | Chunks |
| --- | --- | --- | --- |
| A | `outputs/audio_quality_ab_2026-04-28/fr/preset_A/combined.wav` | `outputs/audio_quality_ab_2026-04-28/fr/preset_A/report.json` | `outputs/audio_quality_ab_2026-04-28/fr/preset_A/chunks/` |
| B | `outputs/audio_quality_ab_2026-04-28/fr/preset_B/combined.wav` | `outputs/audio_quality_ab_2026-04-28/fr/preset_B/report.json` | `outputs/audio_quality_ab_2026-04-28/fr/preset_B/chunks/` |
| C | `outputs/audio_quality_ab_2026-04-28/fr/preset_C/combined.wav` | `outputs/audio_quality_ab_2026-04-28/fr/preset_C/report.json` | `outputs/audio_quality_ab_2026-04-28/fr/preset_C/chunks/` |
| D | `outputs/audio_quality_ab_2026-04-28/fr/preset_D/combined.wav` | `outputs/audio_quality_ab_2026-04-28/fr/preset_D/report.json` | `outputs/audio_quality_ab_2026-04-28/fr/preset_D/chunks/` |
| E | `outputs/audio_quality_ab_2026-04-28/fr/preset_E/combined.wav` | `outputs/audio_quality_ab_2026-04-28/fr/preset_E/report.json` | `outputs/audio_quality_ab_2026-04-28/fr/preset_E/chunks/` |

## Objective Metrics

| Preset | Duration s | Peak | RMS | RMS dBFS approx | Silence ratio | Segment WAVs | Internal text chunks | Generation time s | Clipping warning |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A | 47.751 | 0.97998 | 0.09300 | -20.63 | 0.2929 | 5 | 6 | 199.45 | false |
| B | 46.925 | 0.97998 | 0.10010 | -19.99 | 0.2545 | 5 | 6 | 101.78 | false |
| C | 44.912 | 0.97998 | 0.09613 | -20.34 | 0.2725 | 5 | 6 | 97.22 | false |
| D | 46.149 | 0.97998 | 0.09904 | -20.08 | 0.2789 | 5 | 6 | 99.72 | false |
| E | 57.130 | 0.97998 | 0.08955 | -20.96 | 0.3377 | 5 | 8 | 118.20 | false |

All combined WAV files and per-preset `report.json` files were generated.

## Reference Audio Findings

Reference file: `test_speaker_ref.wav`

| Metric | Value |
| --- | ---: |
| Duration | 10.000 s |
| Sample rate | 22050 Hz |
| Channels | 1 |
| Peak amplitude | 0.539337 |
| RMS | 0.028087 |
| RMS dBFS approx | -31.03 dBFS |
| Silence ratio | 0.519520 |
| Leading silence | 2.148 s |
| Trailing silence | 0.313 s |
| Clipping ratio | 0.000000 |

The reference is technically usable for XTTS under the current validator, but it has substantial leading silence and a high silence ratio. A cleaner trimmed reference may improve stability.

See `docs/REFERENCE_AUDIO_AB_CHECK_2026-04-28.md` for the reference-specific report.

## Objective Recommendation

Final selection requires manual listening. Based only on objective metrics:

- Listen to preset B first: lower temperature than baseline, moderate chunk size, lowest silence ratio, no clipping warning.
- Listen to preset C second: similar stability-oriented settings with shorter chunks and the fastest generation time.
- Listen to preset D third: longer max chars may help prosody while staying close to B/C on loudness and silence metrics.
- Use preset A as the baseline comparison.
- Listen to preset E last: it has the lowest temperature but produced the longest output, highest silence ratio, and more internal text chunks.

No subjective audio quality claims are made here because the files were not manually listened to.

## Validation Notes

Before generation:

- `.\.venv_api\Scripts\python.exe -m compileall voice tts app tools` passed.
- `.\.venv_tts\Scripts\python.exe -c "from transformers import BeamSearchScorer; print('BeamSearchScorer import OK')"` passed.
- Torch check passed with `torch 2.5.1+cpu`, CUDA unavailable, GPU none.

After generation:

- All five `combined.wav` files exist.
- All five `report.json` files exist.
- No project defaults were changed by this A/B harness.
- No dependency files or venvs were intentionally modified.
- `models/xtts_v2` was not modified by this task.
- `outputs/french_official_test/results/Vidiolingua_Test_Official_dubbed_fr.mp4` was not overwritten.

## Technical Warnings

- Generation ran on CPU, so timings are slower than expected on a CUDA setup.
- The XTTS code logged inaccessible fallback cache candidates under `C:\Users\abize\AppData\Local\tts`; the requested local `models/xtts_v2` path was still used successfully.
- Raw XTTS outputs for some presets logged near-clipping before cleanup, but final combined WAV reports show peak-normalized audio and no clipping warnings.
- The reference audio has about 2.148 seconds of leading silence; trimming or recording a cleaner reference is likely worth testing separately.
