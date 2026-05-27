# Speaker Analysis and Diarization Plan - 2026-05-06

## 1. Current failure root cause

The frontend error comes from `asr/run_asr.py`. The WhisperX diarization path currently calls:

```python
diarize_model = diarize_pipeline(use_auth_token=hf_token, device=device)
```

The ASR runtime is `.venv_asr`, where local inspection found:

- `pyannote.audio 4.0.4`
- `whisperx 3.8.5`
- `torch 2.8.0`

The current pyannote Community-1 model card shows modern loading through:

```python
Pipeline.from_pretrained("pyannote/speaker-diarization-community-1", token="...")
```

The installed stack therefore receives `use_auth_token` in a place where the active diarization constructor/API does not accept it, causing:

```text
DiarizationPipeline.__init__() got an unexpected keyword argument 'use_auth_token'
```

This must be fixed in backend code, not hidden in the UI.

## 2. Current speaker analysis flow

Current flow:

1. `backend/pipeline_runner.py` runs ASR through `asr/run_asr.py` in `.venv_asr`.
2. `asr/run_asr.py` transcribes with WhisperX, attempts inline diarization, and writes transcription JSON.
3. `asr/speaker_analysis.py` scans ASR JSON files for existing `segment.speaker` labels.
4. If labels exist, it returns `status="computed"` and `speakers_detected=<count>`.
5. If labels do not exist, it returns `status="not_run"` and `speakers_detected=None`.
6. The frontend reads `analysis.speaker_analysis`.

This is honest enough to avoid fake zero counts, but it is not yet a real speaker-analysis stage. It depends on inline WhisperX diarization labels and does not produce durable diarization turns, speaker-to-segment mapping, voice assignment plans, visual analysis, or reference-candidate metadata.

## 3. Current pyannote version/API

Local runtime inspection:

- `.venv_asr`: `pyannote.audio 4.0.4`
- `.venv_api`: `pyannote.audio` not installed
- `.venv_tts`: `pyannote.audio` not installed

The implementation should load diarization with version-compatible logic:

1. Prefer `pyannote.audio.Pipeline.from_pretrained(model_id, token=token)`.
2. Fall back to `use_auth_token=token` only if the installed API signature supports it.
3. Never pass `use_auth_token` blindly to a constructor.
4. Log version, model id, token-present boolean, device, and elapsed time without logging the token.
5. Set `PYANNOTE_METRICS_ENABLED=0` by default.

## 4. Current ASR segment format

Current ASR payload shape:

```json
{
  "video_file": "...",
  "segments": [
    {
      "start": 3.05,
      "end": 30.68,
      "text": "...",
      "speaker": null,
      "words": []
    }
  ],
  "language": "en",
  "language_confidence": 0.0,
  "diarization": {
    "enabled": true,
    "status": "failed",
    "reason": "..."
  }
}
```

Translation already preserves `speaker` and `words` fields in `translation/run_translate.py`, so adding a canonical `speaker_id` while keeping `speaker` for compatibility is low-risk.

## 5. Proposed diarization architecture

Create a first-class `speaker_analysis` package:

- `speaker_analysis/diarization.py`
- `speaker_analysis/speaker_segments.py`
- `speaker_analysis/speaker_mapping.py`
- `speaker_analysis/speaker_profiles.py`
- `speaker_analysis/visual_speaker_analysis.py`
- `speaker_analysis/sarvam_voice_selection.py`
- `speaker_analysis/report.py`

Pipeline integration:

1. ASR remains responsible for transcript creation.
2. After ASR, `backend/pipeline_runner.py` runs speaker analysis as a distinct backend stage inside the ASR phase.
3. Diarization writes durable artifacts under `outputs/<job>/speaker_analysis`.
4. If diarization fails, the stage writes `status="failed"` with exact errors and fix instructions. It does not emit fake `speaker_count=0`.
5. Pipeline can continue in report-only mode, but the report must clearly say speaker-aware dubbing was not performed.

## 6. Proposed speaker-to-segment mapping

For each ASR segment:

1. Compute overlap duration with every diarized speaker turn.
2. Select the speaker with maximum overlap.
3. If max overlap ratio is below threshold, assign `speaker_id="unknown"`.
4. If multiple speakers overlap materially, set `ambiguous=true` and list candidate speakers.
5. Preserve original segment order, timestamps, text, words, and existing `speaker` compatibility field.

The enriched ASR JSON copied into translation input should include both:

- `speaker`
- `speaker_id`

## 7. Proposed multi-speaker TTS routing

Create `voice_assignment_plan.json` for every job where speaker analysis reaches a usable state or a clear unavailable state.

For XTTS:

- One speaker: use the existing validated `speaker_wav`.
- Multiple speakers with extracted or uploaded per-speaker references: route each segment to its speaker reference.
- Multiple speakers with only one reference: do not silently reuse one reference for all speakers unless explicitly configured. In report-only mode, warn. In strict cloning mode, fail with:
  `Multiple speakers detected but per-speaker references are missing.`

For Sarvam:

- Mark as managed TTS, not cloning.
- Select a supported preset voice per speaker using the speaker profile hint, language, and eventual user override.
- Do not claim exact speaker identity preservation.

## 8. Proposed Sarvam voice preset mapping

Add `config/sarvam_voice_profiles.example.json`.

Initial real supported speakers are taken from current code/config. The current default is `shubh`; existing docs and config do not prove a full supported list. If `anushka` is configured by users or confirmed later, it can be mapped as a feminine voice fit. Until confirmed by local config or official Sarvam docs, production selection should fall back to the current supported default and record that the profile-specific mapping is pending.

Voice profile labels must be:

- `masculine`
- `feminine`
- `neutral`
- `unknown`

They represent apparent voice-fit hints, not gender identity.

## 9. Proposed XTTS multi-speaker reference strategy

Implement safe reference candidates:

1. Use diarized turns to find clean speech windows per speaker.
2. Prefer 5-20 seconds combined, non-overlapping, non-silent speech.
3. Extract WAV files with ffmpeg into `speaker_analysis/references`.
4. Write metadata with duration, source ranges, quality, and usability flags.
5. Do not automatically use extracted references for XTTS unless `VIDIOLINGUA_AUTO_USE_EXTRACTED_REFERENCES_FOR_XTTS=true`.

Defaults:

```text
VIDIOLINGUA_AUTO_EXTRACT_SPEAKER_REFERENCES=true
VIDIOLINGUA_AUTO_USE_EXTRACTED_REFERENCES_FOR_XTTS=false
```

## 10. Frontend updates

Update pipeline and results views so speaker analysis shows:

- status: computed / failed / unavailable / not run
- speaker count only when computed
- assigned speaker segments
- unknown and ambiguous segment counts
- selected voice per speaker
- Sarvam voice plan
- reference candidates
- exact error reason and fix instructions

For Sarvam copy:

```text
Managed TTS voice selected per detected speaker profile. Not exact voice cloning.
```

For profile hints:

```text
Voice profile hint
masculine voice fit / feminine voice fit / neutral / unknown
```

Do not use `gender detected`.

## 11. Validation plan

Add validation tools:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_diarization --audio Vidiolingua_Test_Official.mp4 --output outputs\validation\speaker_diarization_test.json
.\.venv_api\Scripts\python.exe -m tools.validate_speaker_mapping --asr-json outputs\kannada_sarvam_practical_test_clipfix\asr\output\Vidiolingua_Test_Official_transcription.json --diarization-json outputs\validation\speaker_diarization_test.json --output outputs\validation\speaker_segment_map_test.json
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_speaker_plan --speaker-map outputs\validation\speaker_segment_map_test.json --target-language kn --output outputs\validation\sarvam_speaker_voice_plan_test.json
```

Then run compile/config/router/frontend validations without running the full pipeline.

## 12. Risks and rollback notes

Risks:

- `.venv_asr` has pyannote 4.0.4 but `.venv_api` does not, so validation tools must spawn the ASR Python for real diarization.
- Pyannote model access may require a Hugging Face token and accepted model terms.
- Community-1 may be unavailable without network/cache/token; this should be reported as unavailable/failed, not converted to zero speakers.
- Sarvam supported voice IDs are not fully enumerated in current local docs, so unsupported IDs must not be invented.
- Multi-speaker XTTS can degrade or become misleading if one reference is reused for every speaker; default behavior should warn or fail clearly.

Rollback:

- The implementation is additive under `speaker_analysis`, validation tools, config examples, docs, and narrow pipeline hooks.
- Existing ASR, translation, XTTS, IndicTrans2, and Sarvam routes remain intact.
- Protected outputs, `.env` files, venvs, and `models/xtts_v2` are not modified.
