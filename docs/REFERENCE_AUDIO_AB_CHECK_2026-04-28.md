# Reference Audio A/B Check - 2026-04-28

Reference file: `test_speaker_ref.wav`

This check was done for XTTS A/B testing only. The reference WAV was inspected but not modified.

## Objective Metrics

| Metric | Value |
| --- | ---: |
| Duration | 10.000 s |
| Sample rate | 22050 Hz |
| Channels | 1 |
| Peak amplitude | 0.539337 |
| RMS | 0.028087 |
| RMS dBFS approx | -31.03 dBFS |
| Silence ratio | 0.519520 |
| Clipping ratio | 0.000000 |
| Dropout ratio | 0.381381 |
| Leading silence | 2.148 s |
| Trailing silence | 0.313 s |

## Suitability For XTTS

The file is technically suitable for the current XTTS validation path:

- Duration is within the accepted 6 to 60 second range.
- Sample rate is above the minimum 16000 Hz threshold.
- It is mono audio.
- Peak and RMS are non-zero.
- No clipping was detected.
- Silence ratio is below the current maximum validation threshold of 0.65.

## Warnings

The reference has notable leading silence, about 2.148 seconds, and an overall silence ratio of about 51.95%. This does not fail the existing validator, but a cleaner reference with less leading/trailing silence and more continuous speech may improve XTTS speaker conditioning and reduce voice instability.

## Recommendation

Keep `test_speaker_ref.wav` preserved as-is for reproducibility. For a future comparison, create an additional trimmed reference WAV with:

- 8 to 15 seconds of clean, continuous speech.
- Minimal background noise.
- Minimal leading and trailing silence.
- No music, effects, or overlapping voices.
- No clipping or aggressive noise reduction.
