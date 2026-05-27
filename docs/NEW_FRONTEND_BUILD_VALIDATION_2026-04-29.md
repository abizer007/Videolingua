# NEW_Frontend Build Validation - 2026-04-29

## Package Manager

Package manager used:

```text
pnpm
```

Reason:

```text
pnpm-lock.yaml exists.
package-lock.json, yarn.lock, and bun.lockb do not exist.
```

Corepack was used because `pnpm` was not initially on PATH.

## Install Result

Initial install attempts failed because the `D:` drive is exFAT and pnpm's default symlink layout is not supported there.

Fix applied:

```text
NEW_Frontend\.npmrc
node-linker=hoisted
```

The template also included unused mobile/3D dependencies that were not imported by the Vidiolingua frontend. These were removed from `package.json` before the successful install:

```text
@react-three/fiber
expo
expo-asset
expo-file-system
expo-gl
react-native
three
```

Successful install command:

```powershell
corepack pnpm install --no-frozen-lockfile --ignore-scripts --reporter append-only
```

Result:

```text
passed
```

## Lint Result

The template had a `lint` script but no ESLint dependency/config. Added:

```text
NEW_Frontend\eslint.config.mjs
devDependencies: eslint, typescript-eslint
```

Command:

```powershell
corepack pnpm run lint
```

Result:

```text
passed
```

## Typecheck Result

No `typecheck` script exists in `NEW_Frontend\package.json`, so no separate typecheck command was run.

Note: `next.config.mjs` currently has `typescript.ignoreBuildErrors=true`, inherited from the template.

## Build Result

Command:

```powershell
corepack pnpm run build
```

Result:

```text
passed
```

Built routes:

```text
/
/_not-found
/architecture
/backends
/pipeline
/results
/upload
```

Build warning:

```text
baseline-browser-mapping data is over two months old
```

This warning did not fail the build.

## Frontend Files Fixed

```text
NEW_Frontend\.npmrc
NEW_Frontend\eslint.config.mjs
NEW_Frontend\package.json
NEW_Frontend\pnpm-lock.yaml
```

The previously implemented Vidiolingua pages and components were preserved.

## Backend Light Validation

Commands:

```powershell
.\.venv_api\Scripts\python.exe -m compileall backend app tools voice translation tts
.\.venv_api\Scripts\python.exe -m tools.inspect_pipeline_config
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "ಇದು ಪರೀಕ್ಷೆ." --target-language kn --reference test_speaker_ref.wav --reference-text "Technical validation reference transcript." --cloning-required true --output outputs\validation\frontend_build_router_kn.wav --dry-run
.\.venv_api\Scripts\python.exe -m tools.validate_voice_router --text "Ceci est un test." --target-language fr --reference test_speaker_ref.wav --cloning-required true --output outputs\validation\frontend_build_router_fr.wav --dry-run
```

Results:

```text
compileall: passed
inspect_pipeline_config: passed
kn dry-run: selected_engine=sarvam, managed_tts=true, exact_voice_clone=false
fr dry-run: selected_engine=xtts
```

No full video pipeline was run.

## Remaining Browser QA Steps

1. Start the backend:

```powershell
cd D:\Vidiolingua
.\.venv_api\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

2. Start the new frontend:

```powershell
cd D:\Vidiolingua\NEW_Frontend
corepack pnpm run dev
```

3. Open:

```text
http://localhost:3000
```

4. Browser-test:

```text
/
/upload
/pipeline
/results
/architecture
/backends
```

## Frontend Env

Set in `NEW_Frontend\.env.local` if needed:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Do not add backend secrets or Sarvam API keys to frontend env.

## Safety Confirmation

- No secrets exposed.
- No Sarvam key in frontend.
- No Python dependencies installed.
- No Python venvs mutated.
- No full video pipeline run.
- No local IndicF5 load or generation.
- `models\xtts_v2` untouched.
- `outputs\french_official_test` untouched.
- `outputs\kannada_sarvam_practical_test_clipfix` untouched.
