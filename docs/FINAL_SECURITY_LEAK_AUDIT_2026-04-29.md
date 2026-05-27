# Final Security Leak Audit - 2026-04-29

## Scope

Scanned project text surfaces for secret-like values:

- source directories: `backend`, `asr`, `translation`, `tts`, `voice`, `app`,
  `workers`, `tools`, `scripts`
- docs and command log
- frontend source and config
- env examples and requirement files
- output text artifacts: `*.json`, `*.log`, `*.txt`, `*.md`

Excluded:

- virtual environments
- model/checkpoint directories
- binary media and model files such as `*.mp4`, `*.wav`, `*.pth`,
  `*.safetensors`, images
- `backend\.env` content except for git ignore/tracking checks

## Git Secret File Checks

- `backend\.env` is gitignored by `.gitignore` rule `.env`.
- root `.env` is gitignored by `.gitignore` rule `.env`.
- `git ls-files -- backend\.env .env .env.example` did not list
  `backend\.env` or root `.env`.
- `.env.example` is tracked/intended as a template and contains no real keys.

## Findings

No confirmed secret leak was found.

Masked candidate scan findings were code references, placeholders, or secret
names rather than committed secret values:

| Path | Type | Assessment |
| --- | --- | --- |
| `.env.example` | key names/placeholders | Clean; placeholders only. |
| `COMMAND_LOG.md` | `SARVAM_API_KEY=` placeholder mention | Clean; no real key. |
| `voice\engines\sarvam_engine.py` | `SARVAM_API_KEY`, `api-subscription-key` | Code references only. |
| `tools\validate_sarvam_voice.py` | `SARVAM_API_KEY` env read | Code reference only. |
| `app\services\hume_tts_service.py` | authorization/API key code | Code references only. |
| `asr\run_asr.py`, `workers\indicf5_worker.py` | token variable names | Code references only. |
| `translation\engines\indictrans2_engine.py`, docs | `HF_HOME`/cache-like strings | False positives from `hf_` prefix; not tokens. |

An explicit fixed-string scan for the current Sarvam key outside `backend\.env`
found no matches.

## Area Results

- `backend\.env`: contains local secret, ignored and untracked.
- `.env.example`: clean.
- `COMMAND_LOG.md`: clean.
- `docs`: clean.
- `outputs` JSON/log/text artifacts: no confirmed secret leak.
- tracked files: no confirmed secret leak.

## Recommended Actions

- Keep `backend\.env` untracked.
- Before committing, run a pre-commit secret scanner or at least repeat a masked
  `rg` scan.
- Do not include full API keys in future command logs, reports, output JSON, or
  screenshots.
