# Automatic Quality Framework - 2026-05-05

VideoLingua now generates `metrics_report.json` automatically for backend jobs. Normal users upload video, choose a target language, provide reference audio only when the voice route needs it, and run the pipeline.

Expert transcript, translation, and MOS inputs are optional and collapsed under `Expert reference metrics` in the frontend.

The framework never labels proxy metrics as human ground truth. ASR, translation, voice, sync, speaker, output validation, and overall score cards include status, method, confidence, source, reference type, and explanation.

Validated reports:

- `outputs\french_official_test\evaluation\metrics_report.json`
- `outputs\kannada_sarvam_practical_test_clipfix\evaluation\metrics_report.json`

Current evaluator gaps are explicit: LSE-C/LSE-D and true speaker embedding similarity require optional evaluator dependencies and remain unavailable unless installed.
