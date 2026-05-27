"""Production translation stage with strict router enforcement.

Supported IndicTrans2 language pairs are routed to IndicTrans2 first and fail
loudly when the worker/env/model is unavailable. Legacy Llama/Ollama and
deep-translator paths remain available only for unsupported pairs or explicit
configuration. Segment timing and speaker metadata are preserved.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from translation.base import TranslationRequest, indictrans2_supports_pair, normalize_language_code
from translation.router import normalize_engine_name, select_translation_engine, translate
from translation.validation.glossary import load_glossary
from translation.validation.linguistic_integrity import (
    analyze_linguistic_integrity,
    build_linguistic_integrity_summary,
    write_linguistic_integrity_report,
)
from translation.validation.translation_quality import analyze_translation_segments, build_translation_qa_summary

INPUT_DIR = Path(os.environ.get("VIDIOLINGUA_TRANSLATION_INPUT_DIR", Path(__file__).parent / "input"))
OUTPUT_DIR = Path(os.environ.get("VIDIOLINGUA_TRANSLATION_OUTPUT_DIR", Path(__file__).parent / "output"))

_default_languages = ["hi", "es", "fr", "de", "ja", "zh", "ar", "pt"]

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

_LANG_NAMES = {
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Mandarin Chinese",
    "ar": "Arabic",
    "pt": "Portuguese",
    "en": "English",
    "kn": "Kannada",
}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _get_translation_engine() -> str:
    engine = os.environ.get("VIDIOLINGUA_TRANSLATION_ENGINE", "auto").strip().lower()
    return normalize_engine_name(engine)


def _allow_llm_fallback() -> bool:
    return _env_bool("VIDIOLINGUA_ALLOW_LLM_TRANSLATION_FALLBACK") or _env_bool(
        "VIDIOLINGUA_TRANSLATION_ALLOW_LLM_FALLBACK"
    )


def _allow_deep_translator_fallback() -> bool:
    return _env_bool("VIDIOLINGUA_ALLOW_DEEP_TRANSLATOR_FALLBACK") or _env_bool(
        "VIDIOLINGUA_TRANSLATION_ALLOW_GOOGLE_FALLBACK"
    )


def _allow_llm_post_edit() -> bool:
    return _env_bool("VIDIOLINGUA_ENABLE_LLM_POST_EDIT") or _env_bool("VIDIOLINGUA_ALLOW_LLM_POST_EDIT")


def _linguistic_integrity_enabled() -> bool:
    return _env_bool("VIDIOLINGUA_ENABLE_LINGUISTIC_INTEGRITY", True)


def _fail_on_linguistic_errors() -> bool:
    return _env_bool("VIDIOLINGUA_FAIL_ON_LINGUISTIC_ERRORS", True)


def _llm_post_edit_engine() -> str | None:
    engine = os.environ.get("VIDIOLINGUA_LLM_POST_EDIT_ENGINE", "").strip()
    model = os.environ.get("VIDIOLINGUA_LLM_POST_EDIT_MODEL", "").strip()
    if engine and model:
        return f"{engine}:{model}"
    return engine or None


def _get_glossary_path() -> str | None:
    value = os.environ.get("VIDIOLINGUA_TRANSLATION_GLOSSARY", "").strip()
    return value or None


def _load_configured_glossary() -> dict | None:
    path = _get_glossary_path()
    if not path:
        return None
    return load_glossary(path)


def _force_legacy_for_supported_pairs() -> bool:
    return _env_bool("VIDIOLINGUA_FORCE_LEGACY_TRANSLATION_FOR_SUPPORTED_PAIRS")


def _effective_preferred_engine(source_lang: str, target_lang: str) -> str:
    """Honor explicit engine config; use IndicTrans2 only when engine is auto/indictrans2.

    The working backend config uses VIDIOLINGUA_TRANSLATION_ENGINE=google for
    practical runs. Earlier code rewrote explicit google/deep_translator to
    auto on supported IndicTrans2 pairs, which made Kannada jobs enter the
    heavier IndicTrans2 worker even when the manifest/config said google.
    """
    configured = _get_translation_engine()
    supported_pair = indictrans2_supports_pair(source_lang, target_lang)
    if supported_pair and configured == "llama" and not _force_legacy_for_supported_pairs():
        return "auto"
    return configured


def _get_target_languages() -> list[str]:
    raw = os.environ.get("VIDIOLINGUA_TARGET_LANGUAGES", "").strip()
    if not raw:
        return list(_default_languages)
    parts = [x.strip() for x in raw.split(",") if x.strip()]
    return parts if parts else list(_default_languages)


def _build_request(
    *,
    text: str,
    source_lang: str,
    target_lang: str,
    segment_id: str | None = None,
) -> TranslationRequest:
    return TranslationRequest(
        source_text=text,
        source_language=source_lang,
        target_language=target_lang,
        preferred_engine=_effective_preferred_engine(source_lang, target_lang),
        allow_llm_fallback=_allow_llm_fallback(),
        allow_deep_translator_fallback=_allow_deep_translator_fallback(),
        allow_llm_post_edit=_allow_llm_post_edit(),
        segment_id=segment_id,
    )


def _indictrans2_unavailable_error(exc: Exception) -> RuntimeError:
    return RuntimeError(
        "Translation router selected engine: IndicTrans2, but the IndicTrans2 "
        "worker/env/model is unavailable or failed. Create the separate "
        ".venv_indictrans2 runtime, set VIDIOLINGUA_INDICTRANS2_PYTHON, and "
        "install/approve the IndicTrans2 model before retrying. Fallback to "
        "Llama/deep-translator is blocked for IndicTrans2-supported pairs unless "
        f"explicitly configured. Underlying error: {exc}"
    )


def _translate_llama3(text: str, source_lang: str, target_lang: str, duration_s: float | None = None) -> str:
    """Translate via Ollama / Llama-3. Includes optional duration constraint in the prompt."""
    import requests

    tgt_name = _LANG_NAMES.get(target_lang, target_lang)
    src_name = _LANG_NAMES.get(source_lang, source_lang)
    duration_hint = ""
    if duration_s and duration_s > 0:
        duration_hint = (
            f" The translated text, when spoken aloud at a natural pace, "
            f"should fit within approximately {duration_s:.1f} seconds. "
            f"Keep it concise if needed, but preserve the full meaning."
        )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": (
            f"You are a professional translator. Translate the following text from {src_name} "
            f"to {tgt_name}.{duration_hint}\n"
            "Output ONLY the translated text with no preamble, explanation, or quotes.\n\n"
            f"Text to translate:\n{text}"
        ),
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 512},
    }
    try:
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=60)
        resp.raise_for_status()
        translated = resp.json().get("response", "").strip()
        if not translated:
            raise ValueError("Ollama returned empty response")
        return translated
    except Exception as exc:
        if _allow_deep_translator_fallback():
            print(
                f"[Translation] Llama unavailable ({exc}); explicit deep-translator fallback is enabled.",
                file=sys.stderr,
            )
            return _translate_google(text, source_lang, target_lang)
        raise RuntimeError(
            "Llama/Ollama translation failed and fallback is disabled. Start Ollama "
            "and pull/run the configured model, or explicitly enable a fallback."
        ) from exc


def _translate_google(text: str, source_lang: str, target_lang: str) -> str:
    """Translate using deep-translator. Raises clearly on failure."""
    if not text or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator
    except ImportError as exc:
        raise RuntimeError(
            "Translation requires deep-translator for this unsupported pair. "
            "Install it only in the approved translation/TTS runtime, or use another allowed engine."
        ) from exc

    last_err = None
    for attempt in range(2):
        try:
            out = GoogleTranslator(source=source_lang, target=target_lang).translate(text=text)
            if out is None or (isinstance(out, str) and not out.strip()):
                raise ValueError("Translator returned empty")
            return out.strip()
        except Exception as exc:
            last_err = exc
            if attempt == 0:
                time.sleep(0.3)
                continue
            raise RuntimeError(f"Translation failed ({source_lang}->{target_lang}) after retry: {exc}") from last_err
    raise RuntimeError(f"Translation failed: {last_err}") from last_err


def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    duration_s: float | None = None,
    engine: str | None = None,
) -> str:
    """Translate a single segment through the router-selected engine."""
    if not text or not text.strip():
        return text
    source_lang = normalize_language_code(source_lang)
    target_lang = normalize_language_code(target_lang)
    if source_lang == target_lang:
        return text

    request = TranslationRequest(
        source_text=text,
        source_language=source_lang,
        target_language=target_lang,
        preferred_engine=engine or _effective_preferred_engine(source_lang, target_lang),
        allow_llm_fallback=_allow_llm_fallback(),
        allow_deep_translator_fallback=_allow_deep_translator_fallback(),
        allow_llm_post_edit=_allow_llm_post_edit(),
    )
    selected_engine = select_translation_engine(request)
    if selected_engine == "identity":
        return text
    if selected_engine == "indictrans2":
        try:
            return translate(request).translated_text
        except Exception as exc:
            raise _indictrans2_unavailable_error(exc) from exc
    if selected_engine == "llama":
        return _translate_llama3(text, source_lang, target_lang, duration_s)
    if selected_engine == "deep_translator":
        return _translate_google(text, source_lang, target_lang)
    raise RuntimeError(f"Translation router selected unsupported engine: {selected_engine}")


def translate_transcription(
    transcription_data: dict,
    target_lang: str,
    *,
    glossary: dict | None = None,
    qa_report_path: Path | None = None,
    update_translation_memory: bool | None = None,
) -> dict:
    """Translate all segments while preserving downstream TTS JSON shape."""
    source_lang = normalize_language_code(transcription_data.get("language", "en"))
    target_lang = normalize_language_code(target_lang)
    segments = transcription_data.get("segments", [])
    supported_pair = indictrans2_supports_pair(source_lang, target_lang)
    preferred = _effective_preferred_engine(source_lang, target_lang)
    route_probe = _build_request(text="route probe", source_lang=source_lang, target_lang=target_lang)
    selected_engine = select_translation_engine(route_probe)
    fallback_allowed = _allow_llm_fallback() or _allow_deep_translator_fallback()

    print(
        "[Translation] Route: "
        f"source={source_lang} target={target_lang} "
        f"indictrans2_supported={supported_pair} "
        f"configured_engine={_get_translation_engine()} "
        f"preferred_engine={preferred} "
        f"selected_engine={selected_engine} "
        f"allow_llm_fallback={_allow_llm_fallback()} "
        f"allow_deep_translator_fallback={_allow_deep_translator_fallback()} "
        f"allow_llm_post_edit={_allow_llm_post_edit()} "
        f"fallback_used={selected_engine in {'llama', 'deep_translator'}} "
        f"segment_count={len(segments)}"
    )

    translated = {
        "video_file": transcription_data.get("video_file", ""),
        "segments": [],
        "language": target_lang,
        "source_language": source_lang,
        "translation_engine": selected_engine,
        "translation_policy": {
            "indictrans2_supported_pair": supported_pair,
            "fallback_allowed": fallback_allowed,
            "fallback_used": selected_engine in {"llama", "deep_translator"},
        },
    }

    for index, seg in enumerate(segments):
        raw_text = seg.get("text", "")
        duration_s = round(seg.get("end", 0.0) - seg.get("start", 0.0), 2)
        segment_id = str(seg.get("id") or index)
        request = _build_request(
            text=raw_text,
            source_lang=source_lang,
            target_lang=target_lang,
            segment_id=segment_id,
        )
        route_engine = select_translation_engine(request)
        try:
            if route_engine == "identity":
                translated_text = raw_text
            elif route_engine == "indictrans2":
                translated_text = translate(request).translated_text
            elif route_engine == "llama":
                translated_text = _translate_llama3(raw_text, source_lang, target_lang, duration_s)
            elif route_engine == "deep_translator":
                translated_text = _translate_google(raw_text, source_lang, target_lang)
            else:
                raise RuntimeError(f"Unsupported selected translation engine: {route_engine}")
        except Exception as exc:
            if route_engine == "indictrans2":
                raise _indictrans2_unavailable_error(exc) from exc
            raise

        translated["segments"].append(
            {
                "id": seg.get("id", segment_id),
                "start": seg["start"],
                "end": seg["end"],
                "text": translated_text,
                "speaker": seg.get("speaker", None),
                "speaker_id": seg.get("speaker_id", seg.get("speaker", None)),
                "speaker_overlap_sec": seg.get("speaker_overlap_sec"),
                "speaker_overlap_ratio": seg.get("speaker_overlap_ratio"),
                "speaker_ambiguous": seg.get("speaker_ambiguous"),
                "candidate_speakers": seg.get("candidate_speakers", []),
                "words": seg.get("words", []),
            }
        )
        if route_engine == "deep_translator":
            time.sleep(0.05)

    qa_report = analyze_translation_segments(
        segments,
        translated["segments"],
        source_lang,
        target_lang,
        glossary=glossary,
        context_window_size=int(os.environ.get("VIDIOLINGUA_TRANSLATION_CONTEXT_WINDOW", "2")),
        enable_post_edit=_allow_llm_post_edit(),
        post_edit_engine=_llm_post_edit_engine(),
        translation_engine=selected_engine,
        domain=(glossary or {}).get("domain") if isinstance(glossary, dict) else None,
        update_memory=(
            update_translation_memory
            if update_translation_memory is not None
            else _env_bool("VIDIOLINGUA_UPDATE_TRANSLATION_MEMORY")
        ),
    )
    report_payload = qa_report.to_dict()
    report_name = qa_report_path.name if qa_report_path else None
    translated["translation_qa"] = build_translation_qa_summary(report_payload, report_name)
    if qa_report_path:
        qa_report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(qa_report_path, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2, ensure_ascii=False)

    if _linguistic_integrity_enabled():
        integrity_report = analyze_linguistic_integrity(
            segments,
            translated["segments"],
            source_lang,
            target_lang,
            glossary=glossary,
        )
        integrity_report_path = None
        if qa_report_path:
            integrity_report_path = qa_report_path.with_name(
                qa_report_path.name.replace(".translation_qa_report.json", ".linguistic_integrity_report.json")
            )
            if integrity_report_path == qa_report_path:
                integrity_report_path = qa_report_path.with_name(f"{qa_report_path.stem}.linguistic_integrity_report.json")
            write_linguistic_integrity_report(integrity_report, integrity_report_path)
        translated["linguistic_integrity"] = build_linguistic_integrity_summary(
            integrity_report,
            integrity_report_path.name if integrity_report_path else None,
        )
        if integrity_report.status == "failed" and _fail_on_linguistic_errors():
            details = "; ".join(integrity_report.errors) or "critical linguistic integrity failure"
            raise RuntimeError(f"Linguistic integrity failed for {source_lang}->{target_lang}: {details}")
    if qa_report.status == "failed":
        details = "; ".join(qa_report.errors) or "critical translation QA failure"
        raise RuntimeError(f"Translation QA failed for {source_lang}->{target_lang}: {details}")

    return translated


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    transcription_files = list(INPUT_DIR.glob("*_transcription.json"))
    if not transcription_files:
        print(f"Translation error: no transcription files in {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    target_languages = _get_target_languages()
    if not target_languages:
        print("Translation error: no target languages (set VIDIOLINGUA_TARGET_LANGUAGES)", file=sys.stderr)
        sys.exit(1)

    configured_engine = _get_translation_engine()
    print(f"[Translation] Configured engine: {configured_engine.upper()} | Languages: {', '.join(target_languages)}")
    glossary = _load_configured_glossary()
    if glossary:
        print(
            "[Translation] Glossary loaded: "
            f"domain={glossary.get('domain')} terms={len(glossary.get('terms') or [])}"
        )
    if _allow_llm_post_edit():
        print(
            "[Translation] LLM post-edit requested, but post-edit execution is gated after primary translation "
            "and remains disabled unless a post-edit engine is explicitly wired."
        )

    for transcription_file in transcription_files:
        print(f"Processing: {transcription_file.name}")
        with open(transcription_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        qa_reports: dict[str, dict] = {}
        integrity_reports: dict[str, dict] = {}
        for target_lang in target_languages:
            qa_report_path = OUTPUT_DIR / f"{transcription_file.stem}_{target_lang}.translation_qa_report.json"
            translated = translate_transcription(
                data,
                target_lang,
                glossary=glossary,
                qa_report_path=qa_report_path,
            )
            output_file = OUTPUT_DIR / f"{transcription_file.stem}_{target_lang}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(translated, f, indent=2, ensure_ascii=False)
            try:
                qa_reports[target_lang] = json.loads(qa_report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                qa_reports[target_lang] = {}
            integrity_report_path = OUTPUT_DIR / f"{transcription_file.stem}_{target_lang}.linguistic_integrity_report.json"
            try:
                integrity_reports[target_lang] = json.loads(integrity_report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                integrity_reports[target_lang] = {}
            print(
                f"  -> {output_file.name} "
                f"engine={translated.get('translation_engine')} "
                f"fallback_used={translated.get('translation_policy', {}).get('fallback_used')} "
                f"translation_qa={translated.get('translation_qa', {}).get('status')} "
                f"linguistic_integrity={translated.get('linguistic_integrity', {}).get('status')} "
                f"output={output_file}"
            )
        aggregate_report = {
            "status": "failed"
            if any(report.get("status") == "failed" for report in qa_reports.values())
            else "warning"
            if any(report.get("status") == "warning" for report in qa_reports.values())
            else "passed",
            "reports": qa_reports,
        }
        with open(OUTPUT_DIR / "translation_qa_report.json", "w", encoding="utf-8") as f:
            json.dump(aggregate_report, f, indent=2, ensure_ascii=False)
        if integrity_reports:
            aggregate_integrity = {
                "status": "failed"
                if any(report.get("status") == "failed" for report in integrity_reports.values())
                else "warning"
                if any(report.get("status") == "warning" for report in integrity_reports.values())
                else "passed",
                "reports": integrity_reports,
            }
            with open(OUTPUT_DIR / "linguistic_integrity_report.json", "w", encoding="utf-8") as f:
                json.dump(aggregate_integrity, f, indent=2, ensure_ascii=False)
            parent_report = OUTPUT_DIR.parent / "linguistic_integrity_report.json"
            with open(parent_report, "w", encoding="utf-8") as f:
                json.dump(aggregate_integrity, f, indent=2, ensure_ascii=False)

    out_count = len([path for path in OUTPUT_DIR.glob("*.json") if not path.name.endswith("translation_qa_report.json") and path.name != "translation_qa_report.json"])
    if out_count == 0:
        print("Translation error: no output files produced", file=sys.stderr)
        sys.exit(1)
    print(f"Translation complete: {out_count} file(s) in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
