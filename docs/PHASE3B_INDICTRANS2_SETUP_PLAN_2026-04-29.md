# Phase 3B IndicTrans2 Setup Plan

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

This phase is planning only. Do not install dependencies, download models, mutate existing working virtual environments, or run the full video pipeline until the user explicitly approves the commands.

## 1. Current Scaffold Status

Already present:

- `translation/router.py` routes supported IndicTrans2 pairs to `indictrans2` in `auto` mode.
- `translation/base.py` defines the supported IndicTrans2 language policy and normalizes common language aliases.
- `translation/engines/indictrans2_engine.py` shells out to a separate worker Python at `.venv_indictrans2\Scripts\python.exe` by default.
- `workers/indictrans2_worker.py` accepts request/response JSON paths and fails loudly when dependencies or real model invocation are unavailable.
- `tools/validate_translation_router.py` supports policy-only dry-runs that do not load models.
- `tools/validate_indictrans2_translation.py` exercises real execution and should fail until the env/model path is approved and installed.
- `tools/inspect_pipeline_config.py` reports the configured IndicTrans2 Python path and whether it exists.
- `.env.example` already includes `VIDIOLINGUA_INDICTRANS2_ENABLED=true` and `VIDIOLINGUA_INDICTRANS2_PYTHON=D:/Vidiolingua/.venv_indictrans2/Scripts/python.exe`.

Missing:

- `.venv_indictrans2` does not exist.
- `requirements-indictrans2.txt` was not present before Phase 3B.
- No model files are downloaded.
- `workers/indictrans2_worker.py` does not load `AutoTokenizer`, `AutoModelForSeq2SeqLM`, or `IndicProcessor` yet.
- ISO-to-FLORES script-code mapping is not implemented in the worker yet.

Current worker behavior:

- The worker is scaffold-only.
- It first checks for `torch` and `transformers`.
- It then intentionally raises: `IndicTrans2 model invocation is scaffolded but not activated.`
- This is the desired failure mode until install/model activation is approved.

One current config detail to fix in the implementation phase:

- `translation/engines/indictrans2_engine.py` currently defaults `VIDIOLINGUA_INDICTRANS2_MODEL` to `ai4bharat/indictrans2-distilled`, which is not the exact recommended Hugging Face checkpoint. After approval, prefer explicit env configuration and/or a code default of `ai4bharat/indictrans2-en-indic-dist-200M`.

## 2. Recommended Environment

Exact venv path:

```text
D:\Vidiolingua\.venv_indictrans2
```

Recommended Python:

- Safest native Windows choice: Python 3.11 x64.
- Acceptable fallback: Python 3.10 x64.
- Avoid for this phase: Python 3.12 unless Python 3.11 is unavailable, because the broader ML stack is usually better tested on 3.10/3.11.
- Avoid: current system Python 3.13.1 at `C:\Python313\python.exe`; it is too new for this isolated ML dependency stack and the local `py` launcher is not installed.

Why Python 3.11:

- PyTorch CUDA wheels are available.
- It is compatible with the modern `transformers`/`huggingface_hub` stack.
- It avoids the sharper dependency edge around Python 3.13 while staying newer than Python 3.9.

## 3. Exact Proposed Setup Commands

These commands are proposed only. Do not run them until approved.

First install Python 3.11 x64 if it is not already installed:

```powershell
winget install --id Python.Python.3.11 -e
```

Then open a new PowerShell session and verify:

```powershell
python --version
where.exe python
```

If `python` still points to `C:\Python313\python.exe`, use the explicit Python 3.11 path from `where.exe python` or the Python install directory.

Create the venv:

```powershell
cd D:\Vidiolingua
C:\Path\To\Python311\python.exe -m venv .venv_indictrans2
```

Upgrade packaging tools:

```powershell
.\.venv_indictrans2\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
```

Install PyTorch CUDA for RTX 4050:

```powershell
.\.venv_indictrans2\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
```

Install the IndicTrans2 HF inference dependencies:

```powershell
.\.venv_indictrans2\Scripts\python.exe -m pip install -r requirements-indictrans2.txt
```

Optional CPU-only torch fallback if CUDA wheels fail:

```powershell
.\.venv_indictrans2\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
```

Hugging Face login, required if gated model access has not already been granted:

```powershell
.\.venv_indictrans2\Scripts\hf.exe auth login
```

Proposed model download after approval:

```powershell
.\.venv_indictrans2\Scripts\hf.exe download ai4bharat/indictrans2-en-indic-dist-200M --local-dir models\indictrans2\en-indic-dist-200M
```

Optional later downloads, only if reverse or Indic-to-Indic pairs are approved:

```powershell
.\.venv_indictrans2\Scripts\hf.exe download ai4bharat/indictrans2-indic-en-dist-200M --local-dir models\indictrans2\indic-en-dist-200M
.\.venv_indictrans2\Scripts\hf.exe download ai4bharat/indictrans2-indic-indic-dist-320M --local-dir models\indictrans2\indic-indic-dist-320M
```

Set the runtime variables after install:

```powershell
$env:VIDIOLINGUA_INDICTRANS2_PYTHON="D:/Vidiolingua/.venv_indictrans2/Scripts/python.exe"
$env:VIDIOLINGUA_INDICTRANS2_MODEL="ai4bharat/indictrans2-en-indic-dist-200M"
$env:VIDIOLINGUA_INDICTRANS2_DEVICE="cuda"
$env:VIDIOLINGUA_INDICTRANS2_BATCH_SIZE="1"
$env:VIDIOLINGUA_INDICTRANS2_TIMEOUT_SECONDS="180"
```

Package choices:

- Required for HF inference: `torch`, `transformers`, `accelerate`, `safetensors`, `sentencepiece`, `sacremoses`, `mosestokenizer`, `nltk`, `indic-nlp-library`, `indictranstoolkit`, `huggingface_hub[cli]`.
- Not recommended initially: `fairseq`; the HF-compatible checkpoints avoid fairseq for inference.
- Not recommended on Windows initially: `flash-attn`; use eager attention first.
- Not needed for supported IndicTrans2 pairs: Llama/Ollama and deep-translator.

## 4. CUDA/GPU Strategy For RTX 4050

Recommendation:

- Use CUDA first, but conservatively.
- Start with the distilled En-Indic model, `batch_size=1`, and eager attention.
- Use fp16 on CUDA after the first import sanity check succeeds.
- Do not install `flash-attn` during the first Windows setup attempt.

Expected GPU impact:

- Distilled En-Indic checkpoint has about 275M parameters.
- fp16 model weights alone are roughly 0.6 GB, but tokenizer, activations, generation beams, PyTorch CUDA context, and memory fragmentation can raise practical VRAM use into the low single-digit GB range.
- RTX 4050 laptop VRAM is usually tight enough that `batch_size=1` is the safest default.

Expected CPU/RAM impact:

- CPU fallback should work functionally but may be slow enough to be painful for full video segment batches.
- Expect several GB of system RAM use while loading model/tokenizer and generating.

Fallback behavior if CUDA fails:

- Worker should catch CUDA initialization/OOM errors, unload model objects, call `torch.cuda.empty_cache()` when available, and fail loudly with device, model, and segment metadata.
- Do not silently fall back to CPU during production unless `VIDIOLINGUA_INDICTRANS2_ALLOW_CPU_FALLBACK=true` is explicitly added later.

## 5. Model Choice

Primary model for current `en -> kn` / `en -> hi` needs:

```text
ai4bharat/indictrans2-en-indic-dist-200M
```

Why:

- It is the smallest recommended En-to-Indic HF-compatible IndicTrans2 checkpoint.
- It is manageable on an i5 + RTX 4050 when run with batch size 1.
- It supports English to scheduled Indic languages including Hindi and Kannada.
- It avoids the 1B checkpoint during first setup.

Secondary models for later approval:

- `ai4bharat/indictrans2-indic-en-dist-200M` for Indic-to-English.
- `ai4bharat/indictrans2-indic-indic-dist-320M` for Indic-to-Indic.

Supported language policy currently declared by the project:

```text
as, bn, brx, doi, en, gom, gu, hi, kn, ks, mai, ml, mni, mr, ne, or, pa, sa, sat, sd, ta, te, ur
```

Worker implementation will also need exact FLORES/script codes, for example:

- `en` -> `eng_Latn`
- `hi` -> `hin_Deva`
- `kn` -> `kan_Knda`
- `bn` -> `ben_Beng`
- `ta` -> `tam_Taml`
- `te` -> `tel_Telu`
- `ml` -> `mal_Mlym`
- `mr` -> `mar_Deva`
- `gu` -> `guj_Gujr`
- `pa` -> `pan_Guru`
- `ur` -> `urd_Arab`

## 6. Worker Integration

Current subprocess call shape from `translation/engines/indictrans2_engine.py`:

```text
D:\Vidiolingua\.venv_indictrans2\Scripts\python.exe -m workers.indictrans2_worker --request <request.json> --response <response.json>
```

Current request JSON shape:

```json
{
  "source_text": "This is a test.",
  "source_language": "en",
  "target_language": "kn",
  "segment_id": "0",
  "model_name": "ai4bharat/indictrans2-en-indic-dist-200M"
}
```

Recommended response JSON shape:

```json
{
  "ok": true,
  "translated_text": "...",
  "model_name": "ai4bharat/indictrans2-en-indic-dist-200M",
  "source_language": "en",
  "target_language": "kn",
  "source_flores_code": "eng_Latn",
  "target_flores_code": "kan_Knda",
  "device": "cuda",
  "dtype": "float16",
  "batch_size": 1,
  "segment_id": "0"
}
```

Recommended error response JSON shape:

```json
{
  "ok": false,
  "error": "clear failure message",
  "model_name": "ai4bharat/indictrans2-en-indic-dist-200M",
  "source_language": "en",
  "target_language": "kn",
  "device": "cuda",
  "segment_id": "0"
}
```

Timeout handling:

- Keep `VIDIOLINGUA_INDICTRANS2_TIMEOUT_SECONDS=180` for one segment initially.
- If full segment batches are later routed one subprocess per segment, raise only after measuring.
- Worker failures should surface stderr/stdout and response JSON error details.

Memory cleanup strategy:

- Keep the model inside the worker process so process exit releases memory.
- For future multi-segment batching inside one worker, explicitly delete model/tokenizer tensors and call `torch.cuda.empty_cache()` in a `finally` block.
- Keep `batch_size=1` until VRAM behavior is measured.

How the main pipeline calls the worker:

- `translation/run_translate.py` builds a `TranslationRequest`.
- `translation/router.py` selects `indictrans2` for supported pairs such as `en -> kn`.
- `translation/engines/indictrans2_engine.py` writes temporary request JSON, invokes `workers.indictrans2_worker` in `.venv_indictrans2`, reads response JSON, and returns `TranslationResult`.
- Fallback to Llama/deep-translator remains blocked for supported IndicTrans2 pairs unless explicitly configured in a later approved mode.

## 7. Validation Commands After Install

Light checks before install, already allowed:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend asr translation tts lipsync tools voice app workers
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_translation_router --source-language en --target-language kn --text "This is a test of the translation system." --output outputs\validation\router_translation_en_kn_phase3b_plan.json --dry-run
rg -n "from .*parler|import .*parler|parler-tts|Indic Parler|indic-parler" backend asr translation tts voice app workers tools requirements*.txt pyproject.toml setup.py
```

After approved install, config inspect:

```powershell
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
```

After approved install, English to Kannada:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_indictrans2_translation --source-language en --target-language kn --text "This is a test of the translation system." --output outputs\validation\indictrans2_en_kn_phase3b.json
```

After approved install, English to Hindi:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_indictrans2_translation --source-language en --target-language hi --text "This is a test of the translation system." --output outputs\validation\indictrans2_en_hi_phase3b.json
```

Unsupported pair failure:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_translation_router --source-language en --target-language fr --text "This is a test." --output outputs\validation\router_translation_en_fr_blocked_phase3b.json --dry-run
```

Confirmation that supported IndicTrans2 pairs do not use Llama/deep-translator:

```powershell
.\.venv_api\Scripts\python.exe -m tools.validate_translation_router --source-language en --target-language kn --text "This is a test." --output outputs\validation\router_translation_en_kn_no_fallback_phase3b.json --dry-run
```

Expected JSON fields:

- `selected_engine`: `indictrans2`
- `llama_used`: `false`
- `deep_translator_used`: `false`
- `policy_only`: `true`

## 8. Rollback Plan

Disable IndicTrans2 routing for testing only:

```powershell
$env:VIDIOLINGUA_INDICTRANS2_ENABLED="false"
```

Current router code does not yet read `VIDIOLINGUA_INDICTRANS2_ENABLED`, so the implementation phase should either wire that flag or document that rollback means deleting/unsetting the worker path and using unsupported-pair fallbacks only.

Remove the isolated env if needed:

```powershell
Remove-Item -LiteralPath D:\Vidiolingua\.venv_indictrans2 -Recurse -Force
```

Remove downloaded IndicTrans2 models if needed:

```powershell
Remove-Item -LiteralPath D:\Vidiolingua\models\indictrans2 -Recurse -Force
```

Preserve current French compatibility:

- Leave `VIDIOLINGUA_TRANSLATION_ENGINE=google` behavior for unsupported non-Indic pairs.
- Keep deep-translator limited to explicit/unsupported fallback policy.
- Do not mutate `.venv_tts`, `.venv_api`, `.venv_asr`, `.venv_bgm`, `models\xtts_v2`, or known-good French outputs.

## 9. Risks

Dependency conflicts:

- Isolated `.venv_indictrans2` avoids collisions with XTTS and the API env.
- Do not install IndicTrans2 packages into `.venv_tts`, `.venv_api`, `.venv_asr`, or `.venv_bgm`.

Model access and download size:

- The AI4Bharat HF models are gated and may require login/terms acceptance.
- Distilled checkpoints are smaller than 1B models but still non-trivial downloads plus HF cache metadata.

CUDA/OOM:

- RTX 4050 should start with CUDA + fp16 + batch size 1.
- OOM should fail loudly, not fall back silently.

Unsupported language codes:

- Project ISO codes must be mapped to IndicTrans2 FLORES/script codes.
- Some languages with multiple scripts need deliberate mapping choices before production use.

Windows compatibility:

- `indictranstoolkit` notes Linux/MacOS as its tested target and may require source build behavior on Windows.
- Avoid `flash-attn` on Windows in the first pass.
- If native Windows fails, the next decision is either WSL2 for IndicTrans2 only or a small compatibility shim, not contaminating existing venvs.

Slow CPU fallback:

- CPU fallback is useful for debugging only.
- It is likely too slow for a full video pipeline without batching and careful timeout tuning.

## 10. Decision Point

Awaiting user approval before installing `.venv_indictrans2` or downloading models.

## Sources Checked

- AI4Bharat IndicTrans2 HF interface: https://github.com/AI4Bharat/IndicTrans2/tree/main/huggingface_interface
- En-Indic distilled model card: https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M
- IndicTransToolkit PyPI package: https://pypi.org/project/indictranstoolkit/
- PyTorch previous versions install matrix: https://pytorch.org/get-started/previous-versions/
