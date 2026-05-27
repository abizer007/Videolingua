# Reference Audio Auto-Extract and Sarvam Voice Profile Fix - 2026-05-06

## What Was Broken

The upload form treated the reference-audio section as if every selected route needed an uploaded reference file. That blocked Sarvam Indian-language managed TTS jobs and disabled the auto-extract option that should be available for XTTS and Sarvam profile analysis.

## Why Sarvam Does Not Require Reference Audio

Sarvam is managed Indian-language TTS for Hindi, Tamil, Bengali, Telugu, Kannada, Malayalam, Marathi, Gujarati, Punjabi, and Odia. It is not exact speaker cloning, so a user can run Kannada, Hindi, and other Sarvam routes with `reference_mode=none`.

Reference audio can still be uploaded, or speaker-profile auto-analysis can be requested, but these are profile/voice-fit hints only.

## XTTS Reference Upload and Auto-Extract

XTTS speaker-reference languages still require either:

- `reference_mode=uploaded` with a user-provided clean reference audio file.
- `reference_mode=auto_extract`, where the backend extracts and validates a speech-heavy WAV from the uploaded video before XTTS runs.

If neither is provided for XTTS, upload validation fails with:

```text
XTTS speaker-reference dubbing needs either a reference audio file or auto-extract from the uploaded video.
```

If extraction fails, the backend tells the user to upload a clean 6-30 second reference clip.

## Backend Representation

The API and pipeline now normalize reference mode to:

```text
uploaded | auto_extract | none
```

Legacy values such as `auto_extracted` and `not_required` are accepted internally and normalized, but new frontend requests use the new values.

XTTS auto-extract writes the validated candidate under:

```text
jobs\<job_id>\speaker_analysis\references\auto_reference_candidate.wav
```

Speaker-analysis reference candidates are also recorded in:

```text
jobs\<job_id>\speaker_analysis\references\speaker_reference_candidates.json
```

## Sarvam Speaker-Aware Voice Selection

For Sarvam runs, speaker analysis can build:

```text
jobs\<job_id>\speaker_analysis\sarvam_voice_plan.json
jobs\<job_id>\speaker_analysis\voice_assignment_plan.json
```

The plan uses:

- `voice_profile_hint`: `masculine_voice_fit`, `feminine_voice_fit`, `neutral`, or `unknown`
- `confidence`: `low`, `medium`, or `high`
- `hint_source`: `visual_heuristic`, `audio_heuristic`, `user_override`, or `unknown`

The current example mapping keeps all hints on the verified default Sarvam speaker `shubh` until a supported Sarvam speaker list is explicitly verified.

## Visual Analysis Limits

If OpenCV is available, the local visual analyzer uses Haar cascades only for face/person presence. It does not infer identity, presentation, or voice profile. If no reliable local model exists, the visual report stays `unavailable_without_model` or leaves `voice_profile_hint=unknown`.

## Why Voice Profile Hint, Not Gender Identity

The UI and reports say `voice profile hint` because the signal is only a voice-fit routing hint for managed TTS voice selection. It must not be presented as identity, demographic certainty, or exact cloning.

## Validation Results

Validation was run with a mocked background pipeline so no full heavy pipeline was started:

- Sarvam Kannada with `reference_mode=none`: accepted.
- Sarvam Kannada with `reference_mode=auto_extract`: accepted and recorded as auto-analysis mode.
- XTTS French with `reference_mode=none`: blocked with the required clear error.
- XTTS French with `reference_mode=auto_extract`: accepted and would attempt backend extraction during ASR.

Frontend lint/build and backend compile results are recorded in `COMMAND_LOG.md`.

## Remaining Limitations

- Sarvam speaker IDs beyond `shubh` still need provider-list verification before mapping.
- Visual analysis reports presence only unless a reliable local model is explicitly added and reviewed.
- XTTS auto-extract quality depends on source-video speech quality and ASR timing.
