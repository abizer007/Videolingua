# Speaker Analysis and Diarization Report - 2026-05-06

## Root cause

The failure shown by the frontend was real backend breakage:

```text
PyAnnote diarization failed: DiarizationPipeline.__init__() got an unexpected keyword argument 'use_auth_token'
```

`asr/run_asr.py` was passing `use_auth_token` to WhisperX diarization unconditionally. The installed ASR runtime has `pyannote.audio 4.0.4` and `whisperx 3.8.5`, whose diarization constructor accepts `token`, not `use_auth_token`.

## Fixed pyannote token/API handling

The ASR inline diarization path now inspects the diarization constructor signature and passes only the supported token argument:

- `token` when available
- `use_auth_token` only for older compatible APIs
- `auth_token` only if explicitly supported

The new speaker-analysis backend uses `pyannote.audio.Pipeline.from_pretrained(...)` and prefers:

```python
Pipeline.from_pretrained(model_id, token=token)
```

It logs:

- pyannote version
- model id
- token-present boolean
- device
- elapsed time

It does not log token values.

## Diarization backend

Default backend:

```text
VIDIOLINGUA_DIARIZATION_BACKEND=pyannote
VIDIOLINGUA_PYANNOTE_MODEL=pyannote/speaker-diarization-community-1
```

The implementation disables pyannote telemetry by default with:

```text
PYANNOTE_METRICS_ENABLED=0
```

## Speaker mapping algorithm

For each ASR segment, the backend computes overlap with every diarized speaker turn. It assigns the speaker with maximum overlap when the overlap ratio meets the threshold; otherwise it assigns `unknown`. Segments with material overlap from more than one speaker are marked ambiguous and retain candidate speaker overlap data.

## Multi-speaker TTS strategy

Translation now preserves speaker metadata:

- `speaker`
- `speaker_id`
- overlap metadata
- ambiguity metadata

TTS reads `voice_assignment_plan.json`.

For XTTS, multiple speakers no longer silently share one reference. If more than one speaker is detected and no per-speaker references exist, the backend fails clearly unless `VIDIOLINGUA_ALLOW_SINGLE_REFERENCE_FOR_ALL_SPEAKERS=true` is explicitly set.

For Sarvam, the plan records managed preset voice selection per detected speaker. It remains not exact cloning.

## Visual analysis limitations

OpenCV is not installed in the current API/TTS/ASR runtimes. Visual speaker analysis therefore reports:

```text
status=unavailable_without_model
```

No gender identity or apparent voice-profile classification is faked. If OpenCV is available later, Haar cascades are used only for face presence, not gender or identity.

## Validation result

Command:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_diarization --audio Vidiolingua_Test_Official.mp4 --output outputs\validation\speaker_diarization_test.json
```

Result:

```text
status=failed
speaker_count=null
turns=0
```

The failure is now explicit and actionable. Pyannote reported that it could not download/load `pyannote/speaker-diarization-community-1`, likely because the model terms/access are not accepted for the configured token.

Output:

```text
outputs\validation\speaker_diarization_test.json
```

Mapping validation:

```text
outputs\validation\speaker_segment_map_test.json
status=failed
speaker_count=null
```

Sarvam voice-plan validation:

```text
outputs\validation\sarvam_speaker_voice_plan_test.json
status=failed
speakers=0
```

This is expected while diarization access is blocked. No fake `speaker_count=0` was emitted.

## Real access retry - 2026-05-07

After Hugging Face access was accepted for the configured account, real
diarization validation succeeded.

Config evidence:

- Model used: `pyannote/speaker-diarization-community-1`
- Token configured: yes, sourced from `backend\.env` through `HUGGINGFACE_TOKEN`
- Token value: not printed, not logged, not exposed to frontend
- pyannote version: `4.0.4`
- Device: `cpu` from `VIDIOLINGUA_PYANNOTE_DEVICE=auto`
- Telemetry: validation sets `PYANNOTE_METRICS_ENABLED=0`

Diarization command:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_diarization --audio Vidiolingua_Test_Official.mp4 --output outputs\validation\speaker_diarization_real_test.json
```

Result:

```text
status=computed
speaker_count=1
turn_count=11
duration_sec=30.656
output=outputs\validation\speaker_diarization_real_test.json
```

Speaker mapping command:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_mapping --asr-json outputs\kannada_sarvam_practical_test_clipfix\asr\output\Vidiolingua_Test_Official_transcription.json --diarization-json outputs\validation\speaker_diarization_real_test.json --output outputs\validation\speaker_segment_map_real_test.json
```

Result:

```text
status=computed
segment_count=1
speaker_count=1
unknown_segment_count=0
ambiguous_segment_count=0
assigned speaker=SPEAKER_00
speaker_overlap_ratio=0.872
output=outputs\validation\speaker_segment_map_real_test.json
```

Reference candidate extraction was checked in a validation-only folder:

```text
outputs\validation\speaker_references_real_test\SPEAKER_00_reference_candidate.wav
duration_sec=20.0
quality_status=usable
usable_for_xtts=true
usable_for_sarvam_profile=true
```

The candidate was not automatically used for XTTS.

## Remaining limitations

- Pyannote model terms/access must be accepted for the configured token before speaker turns can compute.
- OpenCV is unavailable, so visual analysis is limited to a clear unavailable report.
- Sarvam profile mapping uses the known local default speaker `shubh` until a verified supported Sarvam speaker list is configured.
- Automatic XTTS reference extraction records candidates but does not auto-use them unless explicitly enabled.

## Roadmap

- true active-speaker detection
- stronger face tracking
- speaker embedding clustering
- user voice override UI
- per-speaker reference upload
- lip-sync per visible speaker
- multi-speaker XTTS cloning with separate references
