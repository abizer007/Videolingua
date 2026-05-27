# Linguistic and Phonetic Integrity Report - 2026-05-05

## What Was Added

- Grammar and Linguistic Integrity Engine.
- Phonetic and Ambiguity Resolution Layer.
- Standalone validation tools.
- Pronunciation dictionary example.
- Pipeline, manifest, metrics, API, and frontend reflection.

## Research Consulted

Research is documented in `docs\LINGUISTIC_PHONETIC_INTEGRITY_RESEARCH_2026-05-05.md`.

## Grammar and Integrity Checks

- Script ratio and English leakage checks.
- Empty translated segment detection.
- Repeated segment and repeated token/punctuation checks.
- Too-short and too-long segment ratio checks.
- Sentence-ending punctuation preservation.
- Number, percentage, currency, date, and ordinal preservation.
- Name, acronym, and project-term preservation.
- Segment count, ordering, merge, and split checks.
- Computed score, status, severity, warnings, errors, and affected segment IDs.

## Phonetic and Ambiguity Features

- Backend-local pronunciation dictionary.
- Safe acronym expansion for TTS-prepared text.
- Separate `display_text` and `tts_prepared_text`.
- English homophone ambiguity warnings.
- Date ambiguity warnings.
- XTTS-safe preparation without claiming perfect pronunciation.
- Sarvam-safe Indian-script preservation without romanizing Kannada/Hindi aggressively.

## Pronunciation Dictionary Format

Example file: `config\pronunciation_dictionary.example.json`

```json
{
  "terms": [
    {
      "term": "Vidiolingua",
      "spoken_form": "vi-dee-oh-ling-gwa",
      "preserve_text": true,
      "languages": ["en", "fr", "kn", "hi"]
    }
  ]
}
```

Project dictionary path:

```text
VIDIOLINGUA_PRONUNCIATION_DICTIONARY=config\pronunciation_dictionary.json
```

## TTS Prepared Text Behavior

Canonical translated text remains in `text` / `display_text`. TTS-safe changes are placed in `tts_prepared_text` and are used only when `VIDIOLINGUA_USE_TTS_PREPARED_TEXT=true`.

## Pipeline Integration

- Translation stage writes linguistic integrity reports after translation QA.
- TTS stage writes phonetic resolution reports before synthesis.
- Fatal linguistic errors stop before TTS when configured.
- Warning-only linguistic and phonetic reports continue through the pipeline.

## API and Job Metadata Integration

Summaries are exposed as:

- `linguisticIntegrity`
- `phoneticResolution`

They are included in job status, result payloads, manifest artifacts, and metrics report fields.

## Frontend Integration

- New page: `NEW_Frontend\app\language-integrity\page.tsx`
- Navigation label: `Language Integrity`
- Homepage quality section includes phonetic preparation.
- Architecture page includes language integrity and phonetic resolver lanes.
- Pipeline page shows live language integrity and phonetic resolution cards.
- Results page shows final language integrity and phonetic resolution evidence.

## Validation Results

- Backend compile: passed.
- Config inspect: passed.
- Kannada linguistic integrity validation: `status=warning`, `score=91.8`, `severity=excellent`.
- Kannada phonetic resolution validation: `status=passed`, `risk=0.0`, dictionary loaded.
- Router dry-run Kannada: selected `sarvam`, no IndicF5, no Indic Parler, no generic fallback.
- Router dry-run French: selected `xtts`, no generic fallback.
- Frontend lint: passed after rerunning with approved access to Corepack pnpm cache.
- Frontend build: passed.

Validation report paths:

- `outputs\validation\linguistic_integrity_kn_report.json`
- `outputs\validation\phonetic_resolution_kn_report.json`

## What This Feature Does Not Claim

- No trained grammar model was added.
- No perfect grammar guarantee is claimed.
- No perfect pronunciation guarantee is claimed.
- No human-level linguistic accuracy is claimed.
- Sarvam is not described as exact voice cloning.
- IndicF5 and Indic Parler are not used.

## Remaining Limitations

- Named entity preservation is literal and allowlist-based; transliteration matching is roadmap.
- Homophone warnings are lightweight and English-only.
- Date and number verbalization is conservative and mostly warning-based.
- SSML/phoneme output is not emitted until backend support is explicitly verified.
- COMET/QE quality estimation is not included in this phase.

## Roadmap

- Stronger NER.
- Glossary editor UI.
- Pronunciation dictionary editor UI.
- Transliteration-aware entity preservation.
- Optional COMET/QE evaluation.
- SSML/phoneme support where supported.
- Pronunciation feedback loop.
- Human review queue.
