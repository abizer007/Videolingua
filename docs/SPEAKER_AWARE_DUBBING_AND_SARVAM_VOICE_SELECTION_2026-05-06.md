# Speaker-Aware Dubbing and Sarvam Voice Selection - 2026-05-06

## What is implemented

Speaker analysis is now a backend artifact stage. It writes:

- `speaker_analysis\speaker_diarization.json`
- `speaker_analysis\speaker_segment_map.json`
- `speaker_analysis\speaker_profiles.json`
- `speaker_analysis\sarvam_voice_plan.json`
- `speaker_analysis\voice_assignment_plan.json`
- `speaker_analysis\visual_speaker_report.json`
- `speaker_analysis\speaker_analysis_report.json`
- `speaker_analysis\references\speaker_reference_candidates.json`

## Sarvam strategy

Sarvam is managed Indian-language TTS. It is not exact voice cloning.

For each detected speaker, Vidiolingua builds a voice assignment entry:

```json
{
  "speaker_id": "SPEAKER_00",
  "voice_profile_hint": "unknown",
  "voice_profile_confidence": "low",
  "selected_tts_voice": "shubh",
  "selection_reason": "Sarvam managed TTS voice chosen using current default because no profile-specific supported voice is configured.",
  "override_supported": true,
  "managed_tts": true,
  "exact_voice_clone": false
}
```

Voice profile hints are voice-fit suggestions only:

- masculine voice fit
- feminine voice fit
- neutral
- unknown

They are not gender identity detection.

## Sarvam profile config

Example config:

```text
config\sarvam_voice_profiles.example.json
```

The local codebase only proves `shubh` as the configured Sarvam speaker. The example therefore maps every profile to `shubh` until a verified supported Sarvam voice list is configured. Manual overrides can be provided later through:

```text
VIDIOLINGUA_SARVAM_SPEAKER_OVERRIDES_JSON={"SPEAKER_00":"shubh"}
```

## XTTS strategy

XTTS remains the primary speaker-reference backend for supported global languages.

Behavior:

- one speaker: existing uploaded or extracted reference can be used
- multiple speakers with per-speaker references: route per segment
- multiple speakers without per-speaker references: fail clearly in strict cloning paths
- extracted references are not auto-used unless `VIDIOLINGUA_AUTO_USE_EXTRACTED_REFERENCES_FOR_XTTS=true`

## Reference candidates

When enabled, reference extraction uses diarized turns to create:

```text
speaker_analysis\references\SPEAKER_00_reference_candidate.wav
```

Metadata records duration, source time ranges, quality status, and usability:

- `usable_for_xtts`
- `usable_for_sarvam_profile`

## Frontend behavior

The pipeline and results pages now distinguish:

- computed
- failed
- unavailable
- not run

They show speaker count only when computed. They also show unknown/ambiguous segment counts, reference candidates, voice assignment status, visual analysis status, errors, warnings, and fix instructions.

Sarvam copy remains explicit:

```text
Managed TTS voice selected per detected speaker profile when available. Not exact voice cloning.
```

## Protected routing

This work does not enable IndicF5, does not use Indic Parler, does not add generic fallback, and does not weaken IndicTrans2 routing. XTTS and Sarvam routing remain separate and explicit.

## Real Sarvam speaker-plan validation - 2026-05-07

After pyannote access was available, the validation speaker map produced one
detected speaker:

```text
speaker_id=SPEAKER_00
segment_count=1
total_speech_sec=27.63
```

Sarvam voice-plan command:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_speaker_plan --speaker-map outputs\validation\speaker_segment_map_real_test.json --target-language kn --output outputs\validation\sarvam_speaker_voice_plan_real_test.json
```

Result:

```text
status=computed
target_language=kn
voice_backend=sarvam
managed_tts=true
exact_voice_clone=false
speaker_count=1
selected_tts_voice=shubh
voice_profile_hint=unknown
voice_profile_confidence=low
```

The selected voice came from the configured Kannada profile/default mapping.
This remains a managed TTS voice-fit selection, not identity preservation and
not gender identity detection.
