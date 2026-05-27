# XTTS Supported Language Batch Run After Clipfix

Date: 2026-04-28
Workspace: `D:\Vidiolingua`
Output root: `outputs\xtts_supported_langs_2026-04-28`

## Validation Change

- Changed `voice\xtts_cloner.py` so raw XTTS output is analyzed before cleanup but near-full-scale raw peaks are warnings, not fatal errors.
- Final `xtts_clean.wav` still uses strict `validate_generated_audio(...)`.

## Japanese Dependency Repair

- Installed only missing Japanese XTTS cleaner dependencies into `.venv_tts`: `cutlet 0.5.0`, `fugashi 1.5.2`, `jaconv 0.5.0`, `mojimoji 0.0.13`, `unidic-lite 1.0.8`.
- No core dependency versions were changed: `TTS 0.22.0`, `torch 2.5.1+cpu`, `torchaudio 2.5.1+cpu`, `transformers 4.46.3`, `tokenizers 0.20.3` remain in place.
- Japanese cleaner validation passed with `cutlet.Cutlet().romaji(...)`.

## Smoke And Resume Summary

- TTS-only smoke-tested after clipfix: `cs`, `es`, `fr`, `hu`, `it`, and later `ja`; all produced `smoke.wav`.
- Reused ASR + translation, reran only TTS+lipsync: `cs`, `es`, `fr`, `hu`, `it`.
- Reused ASR, regenerated Japanese translation, then ran TTS+lipsync: `ja`.
- Reused ASR, translated with Google target `zh-CN`, normalized JSON language to XTTS `zh`, then ran TTS+lipsync: `zh`.
- Hindi/`hi` was skipped because XTTS v2 on this machine does not support Hindi.

## Language Results

| Lang | Language | Status | Mode | Final MP4 | Logs |
| --- | --- | --- | --- | --- | --- |
| `ar` | Arabic | success | already successful; preserved, not rerun after clipfix | `outputs\xtts_supported_langs_2026-04-28\ar\results\Vidiolingua_Test_Official_dubbed_ar.mp4` | `outputs\xtts_supported_langs_2026-04-28\ar.pipeline.log` |
| `cs` | Czech | success | resumed: existing ASR/translation, reran TTS+lipsync after clipfix | `outputs\xtts_supported_langs_2026-04-28\cs\results\Vidiolingua_Test_Official_dubbed_cs.mp4` | `outputs\xtts_supported_langs_2026-04-28\cs.clipfix.lipsync.log`<br>`outputs\xtts_supported_langs_2026-04-28\cs.clipfix.tts.log`<br>`outputs\xtts_supported_langs_2026-04-28\cs.pipeline.log` |
| `de` | German | success | already successful; preserved, not rerun after clipfix | `outputs\xtts_supported_langs_2026-04-28\de\results\Vidiolingua_Test_Official_dubbed_de.mp4` | `outputs\xtts_supported_langs_2026-04-28\de.pipeline.log` |
| `en` | English | success | already successful; preserved, not rerun after clipfix | `outputs\xtts_supported_langs_2026-04-28\en\results\Vidiolingua_Test_Official_dubbed_en.mp4` | `outputs\xtts_supported_langs_2026-04-28\en.pipeline.log` |
| `es` | Spanish | success | resumed: existing ASR/translation, reran TTS+lipsync after clipfix | `outputs\xtts_supported_langs_2026-04-28\es\results\Vidiolingua_Test_Official_dubbed_es.mp4` | `outputs\xtts_supported_langs_2026-04-28\es.clipfix.lipsync.log`<br>`outputs\xtts_supported_langs_2026-04-28\es.clipfix.tts.log`<br>`outputs\xtts_supported_langs_2026-04-28\es.pipeline.log` |
| `fr` | French | success | resumed: existing ASR/translation, reran TTS+lipsync after clipfix | `outputs\xtts_supported_langs_2026-04-28\fr\results\Vidiolingua_Test_Official_dubbed_fr.mp4` | `outputs\xtts_supported_langs_2026-04-28\fr.clipfix.lipsync.log`<br>`outputs\xtts_supported_langs_2026-04-28\fr.clipfix.tts.log`<br>`outputs\xtts_supported_langs_2026-04-28\fr.pipeline.log` |
| `hu` | Hungarian | success | resumed: existing ASR/translation, reran TTS+lipsync after clipfix | `outputs\xtts_supported_langs_2026-04-28\hu\results\Vidiolingua_Test_Official_dubbed_hu.mp4` | `outputs\xtts_supported_langs_2026-04-28\hu.clipfix.lipsync.log`<br>`outputs\xtts_supported_langs_2026-04-28\hu.clipfix.tts.log`<br>`outputs\xtts_supported_langs_2026-04-28\hu.pipeline.log` |
| `it` | Italian | success | resumed: existing ASR/translation, reran TTS+lipsync after clipfix | `outputs\xtts_supported_langs_2026-04-28\it\results\Vidiolingua_Test_Official_dubbed_it.mp4` | `outputs\xtts_supported_langs_2026-04-28\it.clipfix.lipsync.log`<br>`outputs\xtts_supported_langs_2026-04-28\it.clipfix.tts.log`<br>`outputs\xtts_supported_langs_2026-04-28\it.pipeline.log` |
| `ja` | Japanese | success | resumed after installing Japanese cleaner deps: reused ASR, regenerated translation, ran TTS+lipsync | `outputs\xtts_supported_langs_2026-04-28\ja\results\Vidiolingua_Test_Official_dubbed_ja.mp4` | `outputs\xtts_supported_langs_2026-04-28\ja.clipfix.tts.log`<br>`outputs\xtts_supported_langs_2026-04-28\ja.cutletfix.lipsync.log`<br>`outputs\xtts_supported_langs_2026-04-28\ja.cutletfix.translation.log`<br>`outputs\xtts_supported_langs_2026-04-28\ja.cutletfix.tts.log`<br>`outputs\xtts_supported_langs_2026-04-28\ja.pipeline.log` |
| `ko` | Korean | success | already successful; preserved, not rerun after clipfix | `outputs\xtts_supported_langs_2026-04-28\ko\results\Vidiolingua_Test_Official_dubbed_ko.mp4` | `outputs\xtts_supported_langs_2026-04-28\ko.pipeline.log` |
| `nl` | Dutch | success | already successful; preserved, not rerun after clipfix | `outputs\xtts_supported_langs_2026-04-28\nl\results\Vidiolingua_Test_Official_dubbed_nl.mp4` | `outputs\xtts_supported_langs_2026-04-28\nl.pipeline.log` |
| `pl` | Polish | success | completed via full pipeline after clipfix/interrupted continuation | `outputs\xtts_supported_langs_2026-04-28\pl\results\Vidiolingua_Test_Official_dubbed_pl.mp4` | `outputs\xtts_supported_langs_2026-04-28\pl.clipfix.pipeline.log`<br>`outputs\xtts_supported_langs_2026-04-28\pl.pipeline.log` |
| `pt` | Portuguese | success | completed via full pipeline after clipfix/interrupted continuation | `outputs\xtts_supported_langs_2026-04-28\pt\results\Vidiolingua_Test_Official_dubbed_pt.mp4` | `outputs\xtts_supported_langs_2026-04-28\pt.clipfix.pipeline.log`<br>`outputs\xtts_supported_langs_2026-04-28\pt.pipeline.log` |
| `ru` | Russian | success | completed via full pipeline after clipfix/interrupted continuation | `outputs\xtts_supported_langs_2026-04-28\ru\results\Vidiolingua_Test_Official_dubbed_ru.mp4` | `outputs\xtts_supported_langs_2026-04-28\ru.clipfix.pipeline.log`<br>`outputs\xtts_supported_langs_2026-04-28\ru.pipeline.log` |
| `tr` | Turkish | success | already successful; preserved, not rerun after clipfix | `outputs\xtts_supported_langs_2026-04-28\tr\results\Vidiolingua_Test_Official_dubbed_tr.mp4` | `outputs\xtts_supported_langs_2026-04-28\tr.clipfix.pipeline.log`<br>`outputs\xtts_supported_langs_2026-04-28\tr.pipeline.log` |
| `zh` | Chinese | success | resumed: existing ASR, translated with zh-CN then normalized to XTTS zh, ran TTS+lipsync | `outputs\xtts_supported_langs_2026-04-28\zh\results\Vidiolingua_Test_Official_dubbed_zh.mp4` | `outputs\xtts_supported_langs_2026-04-28\zh.clipfix.lipsync.log`<br>`outputs\xtts_supported_langs_2026-04-28\zh.clipfix.pipeline.log`<br>`outputs\xtts_supported_langs_2026-04-28\zh.clipfix.translation.log`<br>`outputs\xtts_supported_langs_2026-04-28\zh.clipfix.tts.log`<br>`outputs\xtts_supported_langs_2026-04-28\zh.pipeline.log` |

## FFprobe Summary For Successful MP4s

| Lang | Duration | Video | Resolution | FPS | Audio | Sample Rate | Channels | Exists Non-empty |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |
| `ar` | 30.666009 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `cs` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `de` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `en` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `es` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `fr` | 30.660998 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `hu` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `it` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `ja` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `ko` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `nl` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `pl` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `pt` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `ru` | 30.663991 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `tr` | 30.662993 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |
| `zh` | 30.666667 | h264 | 1920x1080 | 30/1 | aac | 44100 | 2 | True |

## Confirmations

- No virtual environments were deleted or recreated.
- No XTTS model files under `models\xtts_v2` were modified or deleted.
- Existing successful outputs were preserved.
- No cleanup/delete operation was run against logs or outputs.
- No frontend, MuseTalk, GFPGAN, or model changes were made.
- Dependency change was limited to missing Japanese text-cleaner packages in `.venv_tts`.

JSON summary: `outputs\xtts_supported_langs_2026-04-28\batch_summary_after_clipfix.json`
