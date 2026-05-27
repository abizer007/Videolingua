# Reference Audio Final Recommendation - 2026-04-28

Reference source inspected: `test_speaker_ref.wav`

Optional tuned candidate created: `outputs/reference_audio_tuning_2026-04-28/reference_best_candidate.wav`

The original reference file was not overwritten.

## Current Reference Assessment

`test_speaker_ref.wav` is good enough to pass the current XTTS reference validation, but it is not ideal. It is 10.000 seconds long, mono, unclipped, and has usable signal, but it also has about 2.148 seconds of leading silence and an overall silence ratio of about 51.95%.

That amount of silence can reduce the quality of XTTS speaker conditioning. It may contribute to weaker speaker similarity or unstable tone between chunks.

## Tuned Candidate

`reference_best_candidate.wav` was created by:

- Trimming obvious leading and trailing silence only.
- Applying a gentle peak gain of about 1.205x.
- Resampling to 24000 Hz mono PCM WAV.
- Avoiding denoising, robotic cleanup, or aggressive loudness processing.

| Metric | Original | Tuned candidate |
| --- | ---: | ---: |
| Duration | 10.000 s | 7.859 s |
| Sample rate | 22050 Hz | 24000 Hz |
| Channels | 1 | 1 |
| Peak | 0.539337 | 0.638611 |
| RMS | 0.028087 | 0.037490 |
| Silence ratio | 0.519520 | 0.356322 |
| Clipping ratio | 0.000000 | 0.000000 |
| Dropout ratio | 0.381381 | 0.214559 |

The tuned candidate passes XTTS reference validation. It is optional and can be tested by passing it as the pipeline reference:

```powershell
.\.venv_api\Scripts\python.exe -m backend.pipeline_runner --video Vidiolingua_Test_Official.mp4 --target-language fr --reference outputs\reference_audio_tuning_2026-04-28\reference_best_candidate.wav --model-path models\xtts_v2 --mode practical --output-dir outputs\french_quality_reference_candidate_test
```

## Recommendation

Use the original `test_speaker_ref.wav` for the immediate regression test to preserve comparability with the known-good run. If voice similarity remains weak, the single best next test is to rerun once with `reference_best_candidate.wav`, not to run a large settings matrix.

For the best chance of stronger speaker similarity, record a better reference:

- 10-20 seconds.
- Single speaker.
- Clean room.
- No music or background noise.
- Natural speaking tone.
- No whispering or shouting.
- WAV preferred.
- Consistent distance from the microphone.

## Technical Reality

This can improve XTTS conditioning, but exact speaker replication cannot be guaranteed without better reference audio, model fine-tuning, or a stronger voice-cloning model.
