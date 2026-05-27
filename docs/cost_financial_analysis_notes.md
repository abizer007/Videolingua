# Cost & Financial Analysis Notes

Pricing checked: 2026-04-30  
Workspace: `D:\Vidiolingua`

This file supports `assets/cost_financial_analysis.html` and the rendered page image. It separates repo-backed facts from estimates.

## Repo-backed pipeline facts

- Pipeline order: upload -> ASR -> translation -> TTS -> lip-sync/mux -> final MP4. Evidence: `README.md`, `docs/PROJECT_PIPELINE.md`, `backend/pipeline_runner.py`.
- ASR: `asr/run_asr.py` extracts audio with ffmpeg and runs WhisperX first, with faster-whisper fallback. The known-good run log reports WhisperX on CPU with model `base`.
- Translation: current router policy uses IndicTrans2 for supported pairs, and allows Llama/Ollama or deep-translator only when explicitly configured. The preserved known-good French run log says `Engine: GOOGLE`, which maps to the deep-translator/Google fallback path in current router code.
- Voice / TTS: current working practical path uses Coqui XTTSv2 for supported languages with a required speaker reference. `docs/WORKING_STATE_XTTS_PRACTICAL_2026-04-28.md` records `.venv_tts` as CPU-only at capture time.
- Indian-language voice: Sarvam is the practical managed backend when configured; IndicF5 material exists but is classified as experimental/deprecated in `docs/PHASE3C_INDICF5_REMNANTS_AUDIT_2026-04-29.md`.
- Lip-sync / video processing: the known-good output used ffmpeg audio replacement, not Wav2Lip/MuseTalk animation. Optional Wav2Lip/MuseTalk/GFPGAN paths exist in `lipsync/run_lipsync.py`.
- Known-good result: `outputs\french_official_test\pipeline_result.json` reports `totalTime: 305`.
- Known-good MP4 duration: `ffprobe` on `outputs\french_official_test\results\Vidiolingua_Test_Official_dubbed_fr.mp4` reports `duration=30.573991`.
- XTTS model storage: `models\xtts_v2\model.pth` is 1,867,929,118 bytes, plus config, vocab, and speaker files. Rounded as about 1.9 GB.

## Baseline calculations

### Current CPU-heavy practical run

- Video duration: 30.573991 seconds = 0.5095665 minutes.
- End-to-end time: 305 seconds.
- Realtime factor: `305 / 30.573991 = 9.98`, rounded to `~10x realtime`.
- Estimated 60-minute batch on the same CPU-heavy profile: `60 * 9.98 = 598.8 minutes`, rounded to `~10h elapsed`.

This is a repo-backed baseline for the known French XTTS practical run only. It should not be treated as a universal benchmark for every language, every lip-sync engine, or every GPU deployment.

### Cloud GPU compute estimate

Public GPU prices used:

- RunPod RTX 4090 page says RTX 4090 GPUs are available from `$0.69/hr`: https://www.runpod.io/gpu-models/rtx-4090
- Lambda Instances page lists 1x NVIDIA A10 at `$1.29/GPU/hr`: https://lambda.ai/instances

Throughput assumption:

- Low case: 1x realtime after a CUDA-ready deployment.
- High case: 4x realtime after batching/model caching.
- This is an estimate because the repo does not contain a Vidiolingua cloud-GPU benchmark.

Formula:

```text
cost_per_video_min = gpu_hourly_price / (60 * realtime_multiplier)
```

Results:

- RunPod RTX 4090 at 4x realtime: `$0.69 / 240 = $0.002875/min`, rounded to `$0.003/min`.
- Lambda A10 at 1x realtime: `$1.29 / 60 = $0.0215/min`, rounded to `$0.022/min`.
- 60-minute batch range: `60 * $0.002875 = $0.1725` to `60 * $0.0215 = $1.29`, rounded to `$0.20-$1.30`.

These are compute-only figures. They exclude human QA, API usage, failed retries, storage retention, data egress, and engineering setup.

## Manual dubbing / localization comparison

Source:

- Voquent dubbing costs: https://www.voquent.com/dubbing/costs/

Public rates observed:

- Search/result text and page content show professional dubbing packages around `$39-$45/min` for small-cast/non-fiction examples.
- The same page FAQ gives a smaller 60-minute example at about `$45/min`.
- Higher-cast or more complex packages rise above that range. I used `$39-$93/min` as a rounded professional dubbing range by combining the public package rates and the higher-package GBP examples implied by the same page.

Formula:

```text
manual_60_min_low = 60 * 39 = 2340
manual_60_min_high = 60 * 93 = 5580
```

Slide value:

- `$39-$93/min`
- `$2.3k-$5.6k per 60-minute batch`

Manual rates vary by cast size, language, studio requirements, script adaptation, usage rights, and minimum order size.

## API-based automated dubbing comparison

Source:

- Rask AI pricing: https://www.rask.ai/pricing

Relevant public pricing facts:

- Creator Pro monthly plan: `$150/month` for `100 minutes`.
- Business plan: `$750/month` for `500 minutes`.
- Rask FAQ says 1 minute is a universal credit; translation consumes 1 minute per final video minute, and lip-sync consumes 1 additional minute per lip-synced video minute.
- Business extra minutes are listed at `$3/min`.

Calculation:

```text
included_credit_price = 150 / 100 = $1.50 per minute-credit
translated_lipsync_video_min = 2 minute-credits
included_effective_cost = 2 * 1.50 = $3.00 per video minute
business_overage_effective_cost = 2 * 3.00 = $6.00 per video minute
60_min_batch = 60 * $3 to 60 * $6 = $180-$360
```

Slide value:

- `$3-$6/min with lip-sync`
- `$180-$360 per 60-minute batch`

This is a representative API-platform comparison, not a quote for every automated dubbing vendor.

## Translation and TTS API references

These sources are included to show what would become billable if the local/offline stages are replaced by commercial APIs.

- Google Cloud Translation pricing: https://cloud.google.com/translate/pricing
  - NMT text translation is free for the first 500,000 characters per month via credit, then `$20 per million characters`.
  - Translation LLM text pricing is `$10 per million input characters` and `$10 per million output characters`.
- ElevenLabs pricing: https://elevenlabs.io/pricing
  - Pricing page states that V1 English, V1 Multilingual, and V2 Multilingual TTS consume 1 credit per text character.
  - The slide does not use ElevenLabs as the default Vidiolingua cost because the working XTTS path is local and open-source.

## Storage estimate

Source:

- RunPod Pod storage pricing: https://docs.runpod.io/pods/pricing

Relevant public pricing:

- Network volume under 1 TB: `$0.07/GB/month`.
- Volume disk while running: `$0.10/GB/month`.
- Volume disk while stopped: `$0.20/GB/month`.

Repo storage facts:

- XTTS model directory is about 1.9 GB.
- Known-good 30.57s final MP4 is 78,499,361 bytes, about 75 MB.
- Known-good input MP4 is 78,838,770 bytes, about 75 MB.

Implication:

- Model storage is small compared with compute and manual dubbing costs.
- Long-term retention of many source/result MP4s matters more than the XTTS model itself.

## Risks and estimates needing manual verification

- Cloud GPU throughput (`1x-4x realtime`) must be benchmarked on the actual Vidiolingua stack after CUDA-enabled ASR/TTS/lip-sync setup.
- Wav2Lip/MuseTalk/GFPGAN costs are not measured in the known-good run; enabling true lip animation may add substantial GPU time.
- Manual dubbing quotes vary heavily by language, voice talent, rights, cast size, review cycles, and minimum order.
- API-based dubbing cost depends on plan tier, credit definitions, watermark/editor choices, file limits, and whether lip-sync is enabled.
- Sarvam/Hume/ElevenLabs costs are excluded from the default XTTS local-path math and should be added only for jobs that actually route to those providers.
- Human review, localization QA, legal review, and project management are excluded from all infrastructure-only Vidiolingua estimates.

## Final consistency check

- Slide numbers were checked against this notes file.
- Spelling checked for: financial, consistency, localization, and infrastructure.
- No unsupported speedup claim such as `120x faster` is used.
