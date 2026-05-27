# Linguistic and Phonetic Integrity Plan - 2026-05-05

## Goal

Add a defensible backend feature that validates translation integrity after translation and prepares speech-safe text before TTS, while preserving the working French XTTS and Kannada IndicTrans2 + Sarvam paths.

## Backend Plan

1. Add a `translation.validation.linguistic_integrity` engine.
2. Split checks into focused modules for script, numbers, names/entities, punctuation, segment integrity, expansion ratio, and repetition.
3. Produce `linguistic_integrity_report.json` per job and per translated artifact.
4. Fail before TTS only when severe integrity errors occur and `VIDIOLINGUA_FAIL_ON_LINGUISTIC_ERRORS=true`.
5. Add a `voice.phonetic_resolution` layer with pronunciation dictionary support and TTS-only text preparation.
6. Produce `phonetic_resolution_report.json` during the TTS stage.
7. Register both reports in `job_manifest.json`, `pipeline_result.json`, API status/result metadata, and metrics reports.

## Frontend Plan

1. Create `NEW_Frontend/app/language-integrity/page.tsx`.
2. Add navigation label `Language Integrity`.
3. Add homepage, architecture, pipeline, and results reflections.
4. Display linguistic status/score, script status, names/numbers warnings, expansion warnings, phonetic risk score, dictionary use, and report paths when available.

## Safety Rules

- Do not run the full heavy pipeline.
- Do not mutate virtual environments.
- Do not touch `models\xtts_v2`.
- Do not overwrite protected outputs.
- Do not enable IndicF5 or Indic Parler.
- Do not expose Sarvam secrets.
- Do not introduce generic fallback or silent LLM translation fallback.
