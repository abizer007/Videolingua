# Cost Analysis Research Sources

Date researched: 2026-05-05
Requested filename date: 2026-04-29
Rule: values below are source-backed planning data or measured Vidiolingua data. They are not ROI claims.

| Category | Source | URL | Value / Range | Notes | Used in frontend? | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Measured French output | Vidiolingua metrics report | `outputs\french_official_test\evaluation\metrics_report.json` | 30.574s, 78,499,361 bytes | Measured local artifact; XTTS route. | Yes | High |
| Measured Kannada output | Vidiolingua metrics report | `outputs\kannada_sarvam_practical_test_clipfix\evaluation\metrics_report.json` | 30.655s, 78,710,653 bytes | Measured local artifact; IndicTrans2 + Sarvam route. | Yes | High |
| Measured French elapsed time | Vidiolingua pipeline result | `outputs\french_official_test\pipeline_result.json` | 305s | Historical local run timing, not a general benchmark. | Yes | High |
| Measured Kannada elapsed time | Vidiolingua pipeline result | `outputs\kannada_sarvam_practical_test_clipfix\pipeline_result.json` | 166s | Historical local run timing, not a general benchmark. | Yes | High |
| Sarvam TTS pricing | Sarvam AI pricing | https://www.sarvam.ai/api-pricing | Bulbul v3: INR 30 / 10K chars; Bulbul v2: INR 15 / 10K chars | Official pricing page. Update before submission because provider pricing can change. | Yes | High |
| Sarvam speech/translation pricing | Sarvam API docs pricing | https://docs.sarvam.ai/api-reference-docs/pricing | STT: INR 30/hour; STT + diarization: INR 45/hour; Translate: INR 20 / 10K chars | Useful context for Indian-language managed API routes. | Yes | High |
| ElevenLabs API TTS | ElevenLabs API pricing | https://elevenlabs.io/pricing/api | Flash/Turbo: $0.05 / 1K chars; Multilingual v2/v3: $0.10 / 1K chars | Comparison only; not a validated Vidiolingua route. | Yes | High |
| Google Cloud TTS | Google Cloud Text-to-Speech pricing | https://cloud.google.com/text-to-speech/pricing | Chirp 3 HD: $30 / 1M chars after free allowance | Comparison only; pricing depends on SKU/free tier. | Yes | High |
| Google Cloud Translation | Google Cloud Translation pricing | https://cloud.google.com/translate/pricing | NMT: $20 / 1M chars after monthly credit; LLM text: $10 / 1M input + $10 / 1M output chars | Comparison only. Vidiolingua en->kn uses local IndicTrans2. | Yes | High |
| AWS Translate | AWS Translate pricing | https://aws.amazon.com/translate/pricing/ | Standard: $15 / 1M chars; Active Custom: $60 / 1M chars | Comparison only; AWS free tier and document modes vary. | Yes | High |
| Azure Speech TTS | Azure Speech pricing | https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/ | Not used as a concrete numeric card | The accessible page exposes region/tier-dependent placeholders in the crawl, so no exact USD number was copied into the frontend. | No | Medium |
| RunPod RTX 4090 | RunPod RTX 4090 pricing | https://www.runpod.io/gpu-models/rtx-4090 | from $0.59/hr secure, $0.34/hr community | Planning comparison for future GPU workers. Throughput still requires Vidiolingua benchmark. | Yes | High |
| Lambda A10/A100 | Lambda GPU Cloud pricing | https://lambda.ai/service/gpu-cloud/pricing | A10: $0.75/GPU/hr; A100 PCIe: $1.29/GPU/hr | Planning comparison for self-hosted GPU economics. | Yes | High |
| Rev localization | Rev pricing help | https://support.rev.com/hc/en-us/articles/18893487380365-Pricing | Human transcription/captions: $1.99/min; global subtitles: $6.49-$15.99/min; AI services: $0.25/min | Market comparison for localization services, not full dubbing ROI. | Yes | High |
| Voquent dubbing | Voquent video dubbing | https://www.voquent.com/dubbing/video/ | Video dubbing from $11/min | Professional dubbing benchmark; quote varies by scope. | Yes | Medium |
| Voquent packages | Voquent pricing guide | https://www.voquent.com/pricing/ | Package starts from $20-$62/min | Market comparison only; not a savings claim. | Yes | Medium |
| WER definition | Microsoft Learn speech evaluation | https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-custom-speech-evaluate-data | WER = (I + D + S) / N | Requires ground-truth transcript. | Yes | High |
| BLEU definition | ACL Anthology, Papineni et al. 2002 | https://aclanthology.org/P02-1040/ | Reference-based machine translation metric | Requires reference translation. | Yes | High |
| chrF definition | ACL Anthology, Popovic 2015 | https://aclanthology.org/W15-3049/ | Character n-gram F-score | Requires reference translation. | Yes | High |
| MOS terminology | ITU-T P.800.1 summary | https://www.itu.int/dms_pubrec/itu-t/rec/p/T-REC-P.800.1-201607-I!!SUM-HTM-E.htm | Mean opinion score terminology | Requires human rating or evaluator model. | Yes | High |
| LSE-C / LSE-D | VividWav2Lip / SyncNet-style evaluation discussion | https://www.mdpi.com/2079-9292/13/18/3657 | Lip-sync confidence/distance concepts | Requires evaluator model; not computed by current Vidiolingua. | Yes | Medium |
| Speaker similarity | Speaker embedding literature | https://link.springer.com/article/10.1186/s13636-019-0166-8 | Speaker embeddings used for verification concepts | Not used as a numeric claim. | Docs only | Medium |

## Sources Rejected Or Not Used

- Techgium screenshots: treated as inspiration only. No numbers, claims, tables, or wording were copied.
- Earlier standalone HTML/PNG report: not used as frontend source. It was only audited to understand the prior mistake.
- Old cloud throughput assumptions such as `1x-4x realtime`: not used as frontend numeric cost because the repo has no hosted GPU benchmark.
- Azure Speech numeric TTS values: not used because the accessible pricing crawl contained region-dependent placeholders instead of stable concrete USD values.
- Rask AI/platform credit calculations from the earlier notes: not reused because the new page focuses on official provider costs, measured Vidiolingua facts, and clearly labeled market comparisons.

## Measurement Notes

- Measured MP4 duration, file size, route, and media/audio metrics come from local Vidiolingua artifacts and generated `metrics_report.json` files.
- Protected MP4 outputs were not overwritten.
- Metrics that require references or evaluator models remain labeled as optional and unavailable unless the required input/model exists.
