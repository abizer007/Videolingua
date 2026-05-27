# Phase 3B IndicTrans2 Install Report

Date: 2026-04-29
Workspace: `D:\Vidiolingua`

## Scope

Approved scope was IndicTrans2 only:

- Created and installed `.venv_indictrans2`.
- Installed dependencies only into `.venv_indictrans2`.
- Attempted to download only `ai4bharat/indictrans2-en-indic-dist-200M` into `models\indictrans2\en-indic-dist-200M`.
- Did not work on IndicF5.
- Did not touch `.venv_tts`, `.venv_api`, `.venv_asr`, `.venv_bgm`, or `models\xtts_v2`.
- Did not run the full video pipeline.

## Python Used

`py -3.11` was unavailable and PATH `python` points to Python 3.13.1:

```text
C:\Python313\python.exe
3.13.1
```

The valid Python 3.11 interpreter was discovered from `.venv_api\pyvenv.cfg` and used to create `.venv_indictrans2`:

```text
D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe
3.11.11 (main, Jan 5 2025, 05:35:58) [MSC v.1942 64 bit (AMD64)]
```

## Commands Run

Environment inspection:

```powershell
py -3.11 -c "import sys; print(sys.executable); print(sys.version)"
python -c "import sys; print(sys.executable); print(sys.version)"
.\.venv_api\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"
Get-Content .venv_api\pyvenv.cfg
```

Venv creation and pip bootstrap:

```powershell
D:\Vidiolingua\.uv_python\cpython-3.11.11-windows-x86_64-none\python.exe -m venv .venv_indictrans2
.\.venv_indictrans2\Scripts\python.exe -m ensurepip --upgrade --default-pip
.\.venv_indictrans2\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
```

The first venv command failed only at the internal `ensurepip` step because the sandbox blocked `%LOCALAPPDATA%\Temp`. Running the same `ensurepip` step with approved escalation succeeded.

CUDA PyTorch install:

```powershell
.\.venv_indictrans2\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
```

IndicTrans2 dependency install:

```powershell
.\.venv_indictrans2\Scripts\python.exe -m pip install -r requirements-indictrans2.txt
```

HF CLI checks and model download attempt:

```powershell
.\.venv_indictrans2\Scripts\hf.exe --help
.\.venv_indictrans2\Scripts\python.exe -m huggingface_hub.commands.huggingface_cli --help
.\.venv_indictrans2\Scripts\hf.exe download ai4bharat/indictrans2-en-indic-dist-200M --local-dir models\indictrans2\en-indic-dist-200M
```

Validation and safety checks:

```powershell
.\.venv_indictrans2\Scripts\python.exe -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('cuda version:', torch.version.cuda); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
.\.venv_indictrans2\Scripts\python.exe -c "import torch; import transformers; import sentencepiece; import indicnlp; import numpy; print('IndicTrans2 base imports OK'); print('numpy:', numpy.__version__)"
.\.venv_indictrans2\Scripts\python.exe -m pip show torch transformers sentencepiece sacremoses mosestokenizer indic-nlp-library indictranstoolkit huggingface_hub numpy
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_tts\Scripts\python.exe -c "from transformers import BeamSearchScorer; print('BeamSearchScorer import OK')"
.\.venv_tts\Scripts\python.exe -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('cuda version:', torch.version.cuda); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
Get-ChildItem models\xtts_v2
Get-ChildItem outputs\french_official_test
```

## Installed Package Status

Key installed versions:

```text
torch: 2.5.1+cu121
torchvision: 0.20.1+cu121
torchaudio: 2.5.1+cu121
transformers: 4.51.3
sentencepiece: 0.2.1
sacremoses: 0.1.1
mosestokenizer: 1.2.1
indic-nlp-library: 0.92
indictranstoolkit: 1.1.1
huggingface_hub: 0.36.2
numpy: 2.2.6
```

The requirements install succeeded on Windows, including a locally built `indictranstoolkit` wheel.

## Torch / CUDA Result

`.venv_indictrans2` CUDA check:

```text
torch: 2.5.1+cu121
cuda: True
cuda version: 12.1
gpu: NVIDIA GeForce RTX 4050 Laptop GPU
```

CUDA is available for the IndicTrans2 env.

## Model Download Status

Approved model:

```text
ai4bharat/indictrans2-en-indic-dist-200M
```

Target directory:

```text
D:\Vidiolingua\models\indictrans2\en-indic-dist-200M
```

Initial download did not complete because Hugging Face returned a gated-repository authentication error:

```text
401 Client Error: Unauthorized
Cannot access gated repo
Access to model ai4bharat/indictrans2-en-indic-dist-200M is restricted.
You must have access to it and be authenticated to access it. Please log in.
```

After the user manually completed Hugging Face authentication/access, `hf auth whoami` reported:

```text
user: Abizer007
```

The approved model download was retried once and completed successfully:

```powershell
.\.venv_indictrans2\Scripts\hf.exe download ai4bharat/indictrans2-en-indic-dist-200M --local-dir models\indictrans2\en-indic-dist-200M
```

Required files now present include:

```text
config.json
configuration_indictrans.py
dict.SRC.json
dict.TGT.json
generation_config.json
LICENSE
model.SRC
model.TGT
model.safetensors
modeling_indictrans.py
pytorch_model.bin
README.md
special_tokens_map.json
tokenization_indictrans.py
tokenizer_config.json
```

Approximate model directory size:

```text
2,205,182,153 bytes
```

No optional IndicTrans2 models were downloaded.

## Real Translation Status

Real `en -> kn` IndicTrans2 translation now works.

Output:

```text
outputs\validation\indictrans2_en_kn_real_phase3b.json
outputs\validation\router_translation_en_kn_real_phase3b.json
```

Translated text:

```text
ಇದು ಅನುವಾದ ವ್ಯವಸ್ಥೆಯ ಒಂದು ಪರೀಕ್ಷೆಯಾಗಿದೆ.
```

The worker implementation was completed for the Phase 3B En-Indic path:

- `workers\indictrans2_worker.py` loads the local downloaded model with `AutoTokenizer`, `AutoModelForSeq2SeqLM`, and `IndicProcessor`.
- `translation\engines\indictrans2_engine.py` still shells out to `.venv_indictrans2` and now uses a workspace-local temp directory and workspace-local HF module cache.
- Batch size is fixed at 1 for Phase 3B.
- CUDA is used when available.
- fp16 is used only on CUDA.
- Fallback engines were not used.

## Router / Fallback Status

`tools.inspect_pipeline_config` confirms:

- `indictrans2_python` now exists.
- Translation policy still reports IndicTrans2 as primary for supported Indic pairs.
- LLM fallback is false.
- deep-translator fallback is false.

Router validation confirms:

```text
selected_engine: indictrans2
used_indictrans2: true
used_llm: false
used_deep_translator: false
fallback_used: false
device: cuda
dtype: float16
batch_size: 1
```

## XTTS Protection Checks

`.venv_tts` checks:

```text
BeamSearchScorer import OK
torch: 2.5.1+cpu
cuda: False
cuda version: None
gpu: none
```

`models\xtts_v2` still contains the known XTTS files:

```text
model.pth
config.json
vocab.json
hash.md5
speakers_xtts.pth
```

Known-good French output remains present and was not overwritten:

```text
outputs\french_official_test\pipeline_result.json
outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4
```

## Windows-Specific Issues

- `py` launcher is not installed.
- PATH `python` is Python 3.13.1 and was not used.
- Venv creation hit a sandbox permission error during `ensurepip` because Python tried to write temporary wheels under `%LOCALAPPDATA%\Temp`.
- Escalated `ensurepip` completed successfully.
- `indictranstoolkit` built successfully on Windows for Python 3.11.
- First real validation attempt failed because API-side temp files were created under `%LOCALAPPDATA%\Temp`; `translation\engines\indictrans2_engine.py` now uses `outputs\validation\indictrans2_worker_tmp`.
- The next model-load attempt failed because Transformers tried to cache trusted remote-code modules under `C:\Users\abize\.cache`; the worker environment now points Hugging Face caches to `D:\Vidiolingua\.hf_cache`.
- Kannada stdout printing initially failed on the Windows console code page; validation scripts now write UTF-8 JSON files as before but print ASCII-escaped JSON to stdout.

## Output Paths

Created/changed during this phase:

```text
.venv_indictrans2
models\indictrans2\en-indic-dist-200M
docs\PHASE3B_INDICTRANS2_INSTALL_REPORT_2026-04-29.md
outputs\validation\indictrans2_en_kn_real_phase3b.json
outputs\validation\router_translation_en_kn_real_phase3b.json
```

Successful real translation JSON was produced.

## Next Recommended Step

Phase 3B En-to-Kannada translation is validated. The next recommended step is a small Phase 3B follow-up to make model selection explicit/configurable for the optional 1B model, or to proceed to Phase 3C only after separate approval.
