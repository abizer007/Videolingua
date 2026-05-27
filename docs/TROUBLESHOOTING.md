# Troubleshooting

## XTTS `model.pth/model.pth`

Pass the XTTS model directory:

```text
models\xtts_v2
```

Do not pass:

```text
models\xtts_v2\model.pth
```

## PyTorch `weights_only`

The known-good `.venv_tts` stack uses `torch 2.5.1+cpu` with `TTS 0.22.0`. Do not upgrade it without approval.

## `BeamSearchScorer`

Validate the known-good transformers import:

```powershell
.\.venv_tts\Scripts\python.exe -c "from transformers import BeamSearchScorer; print('BeamSearchScorer import OK')"
```

## CPU-only XTTS

The stable `.venv_tts` environment is CPU-only. It is slow but known-good. CUDA XTTS experiments belong in `.venv_tts_gpu`.

## Clipped Raw XTTS Audio

Raw XTTS may be near-clipped before cleanup. Validate the cleaned output, not only the raw intermediate.

## Missing Reference Audio

When XTTS cloning is required, missing reference audio must fail loudly. Sarvam
is different: it is managed Indian-language TTS and does not use a reference
audio file. Do not describe Sarvam output as an exact voice clone.

For XTTS frontend/API jobs, users can either upload a reference audio file or
select backend auto-reference extraction. Auto-reference writes
`reference\auto_reference.wav` in the job folder and validates it before TTS. If
validation fails, ask for a clean manual 6-30 second reference clip; do not fall
back to generic TTS.

If the UI shows speaker analysis as `not_run`, that means ASR did not include
diarization speaker labels. Do not interpret this as zero speakers. Numeric
speaker counts are shown only when ASR/diarization output contains labels.

## Missing Sarvam API Key

Sarvam requires `SARVAM_API_KEY` in a gitignored local env file such as
`backend\.env`.

Do not put the key in docs, `.env.example`, command logs, or test output. Mask
it as `sk_****abcd`.

Dry-run Kannada validation without calling the API:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_voice --text "ಇದು ಪರೀಕ್ಷೆ." --language kn --output outputs\validation\sarvam_kn_dry_run.wav --dry-run
```

Run real Kannada validation only after the dry-run passes:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_sarvam_voice --text "ಇದು ಪರೀಕ್ಷೆ." --language kn --output outputs\validation\sarvam_kn_test.wav
```

## Sarvam Raw Audio Near Full Scale

Sarvam may return otherwise valid WAV audio with a raw peak at or near full
scale. The Sarvam engine now writes a `.sarvam_raw.wav` sidecar, applies
provider-specific peak normalization to a safe target peak when needed, writes a
`.sarvam_clean.wav` sidecar, and validates the cleaned requested output.

This does not relax XTTS validation and does not disable clipping checks for
broken audio. If cleaned audio is still silent, corrupt, too short, invalid-rate,
or heavily clipped, the run still fails loudly.

## Missing IndicF5 Reference Text

IndicF5 requires the exact transcript of the reference audio. Do not guess or substitute target text.

Provide one of:

```text
--reference-text "Exact transcript"
--reference-text-path path\to\reference.txt
VIDIOLINGUA_REFERENCE_TEXT=Exact transcript
VIDIOLINGUA_REFERENCE_TEXT_PATH=path\to\reference.txt
```

## IndicF5 Scaffold Only

IndicF5 remains disabled/local-experimental after Windows local load-only
validation timed out. Do not run local IndicF5 model load or generation while
Sarvam is the approved practical Indian-language backend.

After Phase 3C quarantine, the old failed IndicF5 runtime is archived under:

```text
_legacy\failed_indicf5_attempt_20260429
```

The live IndicF5 files are scaffolding. If real synthesis reports that
IndicF5 is disabled or local execution is not enabled, that is expected.

Dry-run the setup script first:

```powershell
.\scripts\setup_indicf5_env.ps1
```

## IndicF5 `load_model()` API Mismatch

After the fresh install, `ai4bharat/IndicF5` model download succeeded, but real
generation currently fails during model construction:

```text
load_model() missing 1 required positional argument: 'ckpt_path'
```

This indicates that the model repo's `model.py` expects an older `f5_tts`
`load_model` signature than the installed `f5-tts 1.1.20`.

The worker now injects `ckpt_path`, but the next blocker is:

```text
argument of type 'torch.device' is not iterable
```

This happens because AI4Bharat's `model.py` passes a `torch.device` object into
current `f5_tts` loading code, while current `load_checkpoint` checks
`"cuda" in device`. Do not retry unchanged. The next focused source-only fix
should coerce the worker's patched `load_model` `device` argument to a string
while preserving the local `model.safetensors` `ckpt_path`.

The source-only device/ckpt compatibility patch is now in place, but load-only
model validation timed out after 600 seconds. Do not proceed to generation on
this laptop/runtime until the memory/model-load strategy changes.

Use Sarvam for practical Indian-language TTS:

```text
VIDIOLINGUA_INDIC_VOICE_BACKEND=sarvam
VIDIOLINGUA_ENABLE_INDICF5=false
VIDIOLINGUA_INDICF5_EXECUTION_MODE=local_disabled
```

## Unsupported Translation Pair

Supported IndicTrans2 pairs route to IndicTrans2. Unsupported pairs fail unless LLM or deep-translator fallback is explicitly enabled.

If `en -> fr` is configured with the legacy `google` engine, deep-translator is
still allowed for compatibility. If the engine is `auto` with no fallback flags,
the router reports the pair as blocked instead of guessing.

## Fallback Blocked

This is intentional when cloning or strict translation policy is enabled. A clear failure is safer than a generic voice or silent wrong translation backend.

## Indic Parler

Indic Parler-TTS is forbidden in this project.
