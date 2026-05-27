"""IndicTrans2 worker entry point.

This worker is intentionally explicit: until the separate IndicTrans2
environment is installed, it fails loudly instead of falling back.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "ai4bharat/indictrans2-en-indic-dist-200M"
LOCAL_MODEL_PATHS = {
    "ai4bharat/indictrans2-en-indic-dist-200M": PROJECT_ROOT / "models" / "indictrans2" / "en-indic-dist-200M",
}
FLORES_CODES = {
    "as": "asm_Beng",
    "bn": "ben_Beng",
    "brx": "brx_Deva",
    "doi": "doi_Deva",
    "en": "eng_Latn",
    "gom": "gom_Deva",
    "gu": "guj_Gujr",
    "hi": "hin_Deva",
    "kn": "kan_Knda",
    "ks": "kas_Arab",
    "mai": "mai_Deva",
    "ml": "mal_Mlym",
    "mni": "mni_Beng",
    "mr": "mar_Deva",
    "ne": "npi_Deva",
    "or": "ory_Orya",
    "pa": "pan_Guru",
    "sa": "san_Deva",
    "sat": "sat_Olck",
    "sd": "snd_Arab",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "ur": "urd_Arab",
}

os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".hf_cache"))
os.environ.setdefault("HF_MODULES_CACHE", str(PROJECT_ROOT / ".hf_cache" / "modules"))
os.environ.setdefault("TRANSFORMERS_CACHE", str(PROJECT_ROOT / ".hf_cache" / "transformers"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one IndicTrans2 translation request.")
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    return parser.parse_args()


def _model_name(request: dict) -> str:
    return (
        str(request.get("model_name") or "").strip()
        or os.environ.get("VIDIOLINGUA_INDICTRANS2_MODEL", "").strip()
        or DEFAULT_MODEL
    )


def _model_path(model_name: str) -> str:
    local = LOCAL_MODEL_PATHS.get(model_name)
    if local and local.is_dir():
        return str(local)
    return model_name


def _device(request: dict, torch_module) -> str:
    requested = str(request.get("device") or os.environ.get("VIDIOLINGUA_INDICTRANS2_DEVICE", "auto")).lower()
    if requested == "auto":
        return "cuda" if torch_module.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch_module.cuda.is_available():
        raise RuntimeError("VIDIOLINGUA_INDICTRANS2_DEVICE=cuda was requested, but CUDA is not available")
    if requested not in {"cuda", "cpu"}:
        raise RuntimeError(f"Unsupported IndicTrans2 device '{requested}'")
    return requested


def _flores(language: str) -> str:
    code = FLORES_CODES.get(str(language or "").strip().lower())
    if not code:
        raise RuntimeError(f"IndicTrans2 language code is not mapped to a FLORES/script code: {language}")
    return code


def _translate(request: dict) -> dict:
    import torch
    from IndicTransToolkit.processor import IndicProcessor
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    source_language = str(request.get("source_language") or "").strip().lower()
    target_language = str(request.get("target_language") or "").strip().lower()
    source_text = str(request.get("source_text") or "").strip()
    if not source_text:
        raise RuntimeError("IndicTrans2 request source_text is empty")

    source_flores = _flores(source_language)
    target_flores = _flores(target_language)
    model_name = _model_name(request)
    model_path = _model_path(model_name)
    device = _device(request, torch)
    dtype = torch.float16 if device == "cuda" else torch.float32
    batch_size = int(request.get("batch_size") or os.environ.get("VIDIOLINGUA_INDICTRANS2_BATCH_SIZE", "1"))
    if batch_size != 1:
        raise RuntimeError("Phase 3B IndicTrans2 worker only supports batch_size=1")

    attention = str(request.get("attention") or os.environ.get("VIDIOLINGUA_INDICTRANS2_ATTENTION", "default")).strip()
    load_kwargs = {"trust_remote_code": True, "torch_dtype": dtype}
    if attention and attention != "default":
        load_kwargs["attn_implementation"] = attention

    tokenizer = None
    model = None
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_path, **load_kwargs).to(device)
        model.eval()
        processor = IndicProcessor(inference=True)
        preprocessed = processor.preprocess_batch([source_text], src_lang=source_flores, tgt_lang=target_flores)
        inputs = tokenizer(
            preprocessed,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(device)
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=int(os.environ.get("VIDIOLINGUA_INDICTRANS2_MAX_LENGTH", "256")),
                num_beams=int(os.environ.get("VIDIOLINGUA_INDICTRANS2_NUM_BEAMS", "5")),
                num_return_sequences=1,
            )
        decoded = tokenizer.batch_decode(
            generated,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        translations = processor.postprocess_batch(decoded, lang=target_flores)
        translated_text = (translations[0] if translations else "").strip()
        if not translated_text:
            raise RuntimeError("IndicTrans2 model returned empty translation")
        return {
            "ok": True,
            "translated_text": translated_text,
            "model_name": model_name,
            "model_path": model_path,
            "source_language": source_language,
            "target_language": target_language,
            "source_flores_code": source_flores,
            "target_flores_code": target_flores,
            "device": device,
            "dtype": "float16" if dtype == torch.float16 else "float32",
            "batch_size": batch_size,
            "segment_id": request.get("segment_id"),
        }
    finally:
        del model
        del tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def main() -> int:
    args = parse_args()
    request_path = Path(args.request)
    response_path = Path(args.response)
    request = json.loads(request_path.read_text(encoding="utf-8"))

    try:
        response_path.write_text(json.dumps(_translate(request), ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:
        response_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "model_name": _model_name(request),
                    "source_language": request.get("source_language"),
                    "target_language": request.get("target_language"),
                    "device": request.get("device") or os.environ.get("VIDIOLINGUA_INDICTRANS2_DEVICE", "auto"),
                    "segment_id": request.get("segment_id"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
