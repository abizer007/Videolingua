"""
scripts/verify_stack.py - Full ML Stack Verification Script

Runs in the ML Python (.venv_ml, Python 3.11) to verify ALL pipeline dependencies
are correctly installed and functional.

Usage:
    d:/Vidiolingua/.venv_ml/Scripts/python.exe scripts/verify_stack.py
"""

import sys
import os
import time
import traceback
import subprocess
from pathlib import Path

# Fix Windows cp1252 encoding issues
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.pipeline_runner import _whisperx_python, _tts_python, _demucs_python

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

results = []

def check(name, fn):
    print(f"\n{INFO} Checking: {name}...")
    try:
        msg = fn()
        print(f"  {PASS} {msg or 'OK'}")
        results.append((name, True, msg or "OK"))
        return True
    except Exception as e:
        tb = traceback.format_exc().strip().split("\n")[-1]
        print(f"  {FAIL} {tb}")
        results.append((name, False, str(e)))
        return False

def _run_in_env(env_python, code):
    r = subprocess.run(
        [env_python, "-c", code],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()

# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Python Runtimes
# ─────────────────────────────────────────────────────────────────────────────

def test_whisperx_env():
    py = _whisperx_python()
    if not Path(py).exists():
        raise RuntimeError(f"WhisperX env not found at {py}")
    return _run_in_env(py, "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor} OK')")
check(".venv_whisperx exists", test_whisperx_env)

def test_tts_env():
    py = _tts_python()
    if not Path(py).exists():
        raise RuntimeError(f"TTS env not found at {py}")
    return _run_in_env(py, "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor} OK')")
check(".venv_tts exists", test_tts_env)

def test_demucs_env():
    py = _demucs_python()
    if not Path(py).exists():
        raise RuntimeError(f"Demucs env not found at {py}")
    return _run_in_env(py, "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor} OK')")
check(".venv_demucs exists", test_demucs_env)

# ─────────────────────────────────────────────────────────────────────────────
# Test 2: PyTorch + CUDA
# ─────────────────────────────────────────────────────────────────────────────

def test_torch_whisperx():
    return _run_in_env(_whisperx_python(), "import torch; gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'; print(f'torch {torch.__version__} | GPU: {gpu}')")
check("PyTorch WhisperX", test_torch_whisperx)

def test_torch_tts():
    return _run_in_env(_tts_python(), "import torch; gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'; print(f'torch {torch.__version__} | GPU: {gpu}')")
check("PyTorch TTS", test_torch_tts)

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: VRAM Budget Warning
# ─────────────────────────────────────────────────────────────────────────────

def test_vram_budget():
    return _run_in_env(_whisperx_python(), "import torch; print(f'{torch.cuda.mem_get_info()[0]/1e9:.1f} GB free') if torch.cuda.is_available() else print('No CUDA')")
check("VRAM budget", test_vram_budget)

# ─────────────────────────────────────────────────────────────────────────────
# Test 4: WhisperX
# ─────────────────────────────────────────────────────────────────────────────

whisperx_ok = False
def test_whisperx():
    global whisperx_ok
    res = _run_in_env(_whisperx_python(), "import whisperx; print(f'whisperx OK')")
    whisperx_ok = True
    return res
check("WhisperX import", test_whisperx)


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: WhisperX model load (base model, minimal VRAM)
# ─────────────────────────────────────────────────────────────────────────────

def test_whisperx_load():
    code = "import whisperx; import time; t0=time.time(); model=whisperx.load_model('base', 'cuda' if __import__('torch').cuda.is_available() else 'cpu', compute_type='float16' if __import__('torch').cuda.is_available() else 'int8'); print(f'base model loaded in {time.time()-t0:.1f}s')"
    return _run_in_env(_whisperx_python(), code)

if whisperx_ok:
    check("WhisperX model load (base)", test_whisperx_load)


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Coqui TTS import
# ─────────────────────────────────────────────────────────────────────────────

def test_coqui_import():
    return _run_in_env(_tts_python(), "from TTS.api import TTS; print('TTS (Coqui) importable')")
coqui_ok = check("Coqui TTS import", test_coqui_import)

def test_xtts_load():
    code = "import time; from TTS.api import TTS; import torch; t0=time.time(); tts=TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=torch.cuda.is_available()); print(f'XTTSv2 loaded in {time.time()-t0:.1f}s')"
    return _run_in_env(_tts_python(), code)

if coqui_ok:
    xtts_loaded = check("XTTSv2 model load", test_xtts_load)
else:
    xtts_loaded = False


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: XTTS Synthesis — Spanish
# ─────────────────────────────────────────────────────────────────────────────

# Synthesis tests disabled in verify_stack as they take long and are verified in run_tts.py.
# But we verify demucs, deep-translator and gtts.


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Demucs
# ─────────────────────────────────────────────────────────────────────────────

def test_demucs():
    return _run_in_env(_demucs_python(), "import demucs; print(f'demucs {getattr(demucs, '__version__', \"installed\")}')")
check("Demucs (UVR5)", test_demucs)

def test_deep_translator():
    return _run_in_env(_tts_python(), "from deep_translator import GoogleTranslator; print('deep-translator OK')")
check("deep-translator", test_deep_translator)

def test_gtts():
    return _run_in_env(_tts_python(), "from gtts import gTTS; print('gTTS OK')")
check("gTTS (fallback TTS)", test_gtts)


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Text chunking logic
# ─────────────────────────────────────────────────────────────────────────────

def test_text_chunking():
    code = """
import sys, os
sys.path.insert(0, r'd:/Vidiolingua')
try:
    from app.services.xtts_tts_service import _split_into_chunks
    long_text = "Este es el primer segmento de un texto muy largo. El segundo segmento también es extenso. Y este es el tercer segmento."
    chunks = _split_into_chunks(long_text, max_chars=60)
    print(f"{len(chunks)} chunks from {len(long_text)}-char text")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"""
    return _run_in_env(_tts_python(), code)

check("XTTS text chunking", test_text_chunking)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)

passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)

for name, ok, msg in results:
    status = PASS if ok else FAIL
    print(f"  {status} {name}")
    if not ok:
        print(f"         -> {msg}")

print(f"\n{passed}/{len(results)} checks passed", end="")
if failed:
    print(f" | {failed} FAILED -- fix these before running the pipeline.")
    sys.exit(1)
else:
    print(" -- Stack is fully operational!")
