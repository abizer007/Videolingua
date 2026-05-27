# Kannada Sarvam Full Pipeline Run - 2026-04-29

## Summary

The first full practical Kannada pipeline run did not complete. ASR and
IndicTrans2 translation succeeded, and the TTS router selected Sarvam for
Kannada. The run failed in TTS because the first Sarvam-generated segment WAV
was rejected by the shared generated-audio validator as clipped.

Sarvam remains the approved managed Indian-language TTS backend. It is not exact
voice cloning and does not provide exact speaker preservation.

## Command

```powershell
.\.venv_api\Scripts\python.exe -m backend.pipeline_runner --video Vidiolingua_Test_Official.mp4 --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --model-path models\xtts_v2 --mode practical --output-dir outputs\kannada_sarvam_practical_test
```

The command was run exactly once.

## Output Folder

```text
outputs\kannada_sarvam_practical_test
```

## Pre-Run Validation

- Compile passed.
- Config inspection showed Sarvam enabled, the key masked, Indic voice backend
  `sarvam`, IndicF5 `false/local_disabled`, XTTS ready, and IndicTrans2 paths
  present.
- Kannada voice router dry-run selected `sarvam`.
- Translation validation selected `indictrans2` and produced Kannada output.
- XTTS `BeamSearchScorer` import passed.
- `models\xtts_v2` files remained present.

## Stage Results

Observed from the pipeline output:

- ASR: succeeded, elapsed about 67.6 seconds.
- Translation: succeeded, elapsed about 99.1 seconds.
- TTS: failed after selecting Sarvam.
- Lipsync/mux: not reached.

## Translation

Translation backend used:

```text
indictrans2
```

Translation output:

```text
outputs\kannada_sarvam_practical_test\translation\output\Vidiolingua_Test_Official_transcription_kn.json
```

Log evidence:

```text
selected_engine=indictrans2
engine=indictrans2
fallback_used=False
```

IndicTrans2 succeeded.

## Voice

Voice backend selected:

```text
sarvam
```

TTS log evidence:

```text
selected_engine=sarvam
xtts_supported=False
sarvam_supported=True
indicf5_supported=True
fallback_used=false
managed_tts=true
exact_voice_clone=false
speaker_preservation=not_supported
```

Sarvam API returned audio for the first segment, but the segment failed
generated-audio validation:

```text
Invalid XTTS generated audio '...\tts\output\tmpqyst3qcy\raw_0000.wav':
generated audio is clipped (peak=1.000, clipped=0.000%)
```

The error text says `XTTS generated audio` because it comes from the shared
generated-audio validator; the selected backend for this Kannada run was Sarvam.

No final TTS WAV was created:

```text
outputs\kannada_sarvam_practical_test\tts\output\Vidiolingua_Test_Official_transcription_kn.wav
```

The transient raw segment path was inside a temporary directory and was removed
after the failed TTS stage.

## Artifacts

Pipeline result:

```text
outputs\kannada_sarvam_practical_test\pipeline_result.json
```

ASR output:

```text
outputs\kannada_sarvam_practical_test\asr\output\Vidiolingua_Test_Official_transcription.json
```

Translation JSON:

```text
outputs\kannada_sarvam_practical_test\translation\output\Vidiolingua_Test_Official_transcription_kn.json
```

Final MP4:

```text
not created
```

Expected final MP4 path, if the pipeline had completed:

```text
outputs\kannada_sarvam_practical_test\results\Vidiolingua_Test_Official_dubbed_kn.mp4
```

Only the copied input video exists under `results`:

```text
outputs\kannada_sarvam_practical_test\results\input_video.mp4
```

## ffprobe

No final dubbed MP4 exists, so `ffprobe` was not run on a final output. Audio
and video stream details are unavailable for the final Kannada dub.

## Safety Checks

- No local IndicF5 load was used.
- No generic TTS fallback was used.
- No Indic Parler was used.
- XTTS was not selected for Kannada.
- `models\xtts_v2` was not modified.
- `outputs\french_official_test` was not overwritten.
- `outputs\french_after_phase3a_router_integration_test` was not overwritten.
- No batch language run was performed.

## Errors And Warnings

Main blocker:

```text
Sarvam managed Indian-language TTS is required but failed:
generated audio is clipped (peak=1.000, clipped=0.000%)
```

This should be treated as a validation-policy or audio-normalization issue for
Sarvam segment WAVs, not as a routing failure. The router selected the correct
backend and did not fall back.
