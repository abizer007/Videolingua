# Abizer Reference Analysis - 2026-04-29

Input file: `C:\Users\abize\Downloads\Abizer.wav`

## Result

The raw downloaded WAV is not suitable as-is for XTTS reference conditioning because it fails the current reference validator for excessive silence. A non-destructive trimmed and normalized candidate was created and used successfully.

Candidate used:

`outputs/reference_audio_tuning_2026-04-29/Abizer_reference_candidate.wav`

Regression output:

`outputs/french_quality_abizer_reference_test/results/Vidiolingua_Test_Official_dubbed_fr.mp4`

## Raw Input Metrics

| Metric | Value |
| --- | ---: |
| Duration | 17.150 s |
| Sample rate | 16000 Hz |
| Channels | 1 |
| Peak | 0.142029 |
| RMS | 0.008680 |
| Silence ratio | 0.653240 |
| Clipping ratio | 0.000000 |
| Dropout ratio | 0.387040 |
| XTTS validation | Failed |

Failure reason: audio is mostly silence by the current 30 ms frame threshold.

## Candidate Metrics

The candidate was created by trimming edge silence, resampling to 24000 Hz mono WAV, and applying moderate peak gain. No denoising or robotic cleanup was applied.

| Metric | Value |
| --- | ---: |
| Duration | 14.457 s |
| Sample rate | 24000 Hz |
| Channels | 1 |
| Peak | 0.525482 |
| RMS | 0.035999 |
| Silence ratio | 0.338877 |
| Clipping ratio | 0.000000 |
| Dropout ratio | 0.209979 |
| XTTS validation | Passed |

## Regression Metrics

Final TTS WAV:

`outputs/french_quality_abizer_reference_test/tts/output/Vidiolingua_Test_Official_transcription_fr.wav`

| Metric | Value |
| --- | ---: |
| Duration | 30.673 s |
| Sample rate | 22050 Hz |
| Peak | 0.976410 |
| RMS | 0.115522 |
| Silence ratio | 0.294233 |
| Clipping ratio | 0.000000 |

Duration diagnostics:

- Original video: 30.67 s.
- Generated audio: 30.67 s.
- Final MP4: 30.67 s.
- Lip-sync mux speedup applied: false.
- TTS per-segment atempo applied: true.
- One segment still required speedup ratio about 1.60, so speech may still feel rushed in that segment.

## Recommendation

Use `Abizer_reference_candidate.wav` instead of the raw downloaded WAV if you want to compare this reference against the prior `test_speaker_ref.wav` run. Manual listening is still required to judge whether it sounds closer to the target speaker.

Exact speaker replication still cannot be guaranteed without better reference audio, fine-tuning, or a stronger voice-cloning model.
