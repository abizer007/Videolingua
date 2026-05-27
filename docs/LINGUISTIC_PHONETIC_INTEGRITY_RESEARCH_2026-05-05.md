# Linguistic and Phonetic Integrity Research - 2026-05-05

## Sources Used

- Okapi CheckMate: https://okapiframework.org/wiki/index.php/CheckMate
- Unicode Standard Annex #24, Script Property: https://www.unicode.org/reports/tr24/tr24-39.html
- Unicode Technical Standard #18, Unicode Regular Expressions: https://www.unicode.org/reports/tr18/
- MQM Core Typology: https://themqm.org/the-mqm-typology/
- Google Cloud Translation glossaries: https://docs.cloud.google.com/translate/docs/advanced/glossary
- W3C SSML 1.1: https://www.w3.org/TR/speech-synthesis11/
- W3C Pronunciation Lexicon Specification 1.0: https://www.w3.org/TR/pronunciation-lexicon/
- Amazon Polly pronunciation lexicons: https://docs.aws.amazon.com/polly/latest/dg/managing-lexicons.html
- Amazon Polly SSML supported tags: https://docs.aws.amazon.com/polly/latest/dg/supportedtags.html
- Microsoft Azure Speech SSML voice documentation: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice

## What Was Learned

- Practical localization QA tools such as Okapi CheckMate focus on missing translations, repeated words, corrupted characters, source/target pattern correspondence, inline-code differences, and suspicious source/target length changes.
- Unicode script validation should be explicit about script properties and should avoid confusing script blocks with language identity. Script checks are useful, but mixed-script names, digits, punctuation, and borrowed terms must be allowed.
- MQM-style quality thinking separates accuracy, terminology, locale convention, fluency, and style issues. Vidiolingua should report concrete issue classes rather than collapse everything into one opaque quality score.
- Glossaries are a common production mechanism for term control and should be compatible with validation, not treated as a model replacement.
- SSML, phoneme tags, `say-as`, substitutions, and pronunciation lexicons are established ways to guide TTS systems, but support varies by backend.
- Pronunciation dictionaries and lexicons should be modeled as backend-preparation metadata. They should not overwrite canonical translated text.
- TTS text normalization is naturally ambiguous for dates, numbers, acronyms, and homographs. Warnings are safer than aggressive automatic rewrites.

## What Was Adopted

- A localization QA style validation gate with missing segment, script, repetition, number, entity, punctuation, segment-alignment, and expansion-ratio checks.
- Computed reports with per-check status, per-segment affected IDs, warnings, errors, and score.
- Unicode-range script checks for Kannada, Devanagari, Tamil, Telugu, Bengali, Malayalam, Gujarati, Gurmukhi, Odia, Arabic, Cyrillic, CJK, Japanese, and Korean.
- Glossary and project-term allowlists so roman names and product terms can be preserved without triggering false script failures.
- A pronunciation dictionary JSON format modeled after lexicon practice, but kept backend-local and simple.
- Separate `display_text` and `tts_prepared_text` fields so TTS-safe text never silently replaces canonical translations.
- Conservative acronym expansion and homophone/date ambiguity warnings.

## What Was Rejected as Too Heavy or Risky

- Training or claiming a new grammar-correction model.
- Hard-failing on all grammar warnings. The gate only fails for severe integrity errors; warnings continue through the pipeline.
- Aggressive romanization for Kannada/Hindi/Sarvam paths. Indian-language scripts remain intact.
- SSML/phoneme insertion into XTTS or Sarvam without confirmed backend support.
- COMET/QE model integration in this phase, because it would add model/dependency/runtime risk.
- Local IndicF5 or Indic Parler usage.

## Roadmap

- Transliteration-aware named entity matching.
- Stronger NER with language-specific support.
- Glossary and pronunciation dictionary editor UI.
- COMET/QE quality estimation as an optional advanced evaluator.
- SSML/phoneme support only where a selected TTS backend explicitly supports it.
- Human review queue for failed integrity gates.
