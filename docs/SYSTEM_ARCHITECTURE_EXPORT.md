# VidioLingua — System Architecture (export)

Single-page system architecture diagram. Copy the Mermaid code below to export as PNG or SVG.

---

## Diagram

```mermaid
flowchart LR
  subgraph user [User]
    browser[Browser]
  end

  subgraph frontend [Frontend Next.js]
    direction TB
    pages[Pages: /, /upload, /pipeline, /results, /architecture]
    apiMode["API Mode: Real API | Mock"]
    state[State: jobId, progress, result URLs]
    pages --> apiMode
    apiMode --> state
  end

  subgraph backend [Backend FastAPI]
    direction TB
    routes[Routes]
    jobStore["Job Store (in-memory)"]
    orchestrator["Pipeline Runner (background thread)"]
    routes --> jobStore
    routes --> orchestrator
    subgraph routeList [API]
      rRoot["GET /"]
      rHealth["GET /api/health"]
      rDeps["GET /api/health/deps"]
      rTtsHealth["GET /tts-health, /api/tts-health"]
      rUpload["POST /api/upload"]
      rStatus["GET /api/job-status/:id"]
      rResult["GET /api/result/:id"]
      rFile["GET /api/result/:id/file/:name"]
    end
  end

  subgraph pipeline [Pipeline stages]
    direction LR
    subgraph stageAsr [1. ASR]
      direction TB
      aScript[asr/run_asr.py]
      aFfmpeg[ffmpeg extract audio]
      aWhisper[faster-whisper Whisper base]
      aOut["*_transcription.json"]
      aScript --> aFfmpeg --> aWhisper --> aOut
    end
    subgraph stageMt [2. Translation]
      direction TB
      mScript[translation/run_translate.py]
      mDt[deep-translator]
      mOut["*_<lang>.json"]
      mScript --> mDt --> mOut
    end
    subgraph stageTts [3. TTS]
      direction TB
      tScript[tts/run_tts.py]
      tEngine[Engine: Hume | XTTS | legacy]
      tHume[Hume API]
      tXtts[XTTS optional]
      tLegacy[gTTS / ElevenLabs]
      tOut["*.wav"]
      tScript --> tEngine
      tEngine --> tHume
      tEngine --> tXtts
      tEngine --> tLegacy
      tHume --> tOut
      tXtts --> tOut
      tLegacy --> tOut
    end
    subgraph stageLs [4. Lip-sync]
      direction TB
      lScript[lipsync/run_lipsync.py]
      lWav2lip[Wav2Lip]
      lFfmpeg[ffmpeg fallback]
      lOut["*_dubbed_<lang>.mp4"]
      lScript --> lWav2lip
      lScript --> lFfmpeg
      lWav2lip --> lOut
      lFfmpeg --> lOut
    end
    stageAsr --> stageMt --> stageTts --> stageLs
  end

  subgraph jobWorkspace [Job workspace JOBS_DIR]
    direction TB
    jobDir["jobs/<job_id>/"]
    inputVideo[input_video.mp4]
    resultsDir[results/]
    dubbedFiles["*_dubbed_<lang>.mp4"]
    jobDir --> inputVideo
    jobDir --> resultsDir
    resultsDir --> dubbedFiles
  end

  subgraph external [External services]
    humeApi[Hume AI TTS API]
    elevenApi[ElevenLabs API optional]
    wav2lipLocal[Wav2Lip local repo]
  end

  subgraph env [Environment]
    direction LR
    ttsEngine[VIDIOLINGUA_TTS_ENGINE]
    humeKey[HUME_API_KEY]
    wav2lipDir[VIDIOLINGUA_WAV2LIP_DIR]
    targetLangs[VIDIOLINGUA_TARGET_LANGUAGES]
  end

  browser <-->|"HTTP NEXT_PUBLIC_API_URL"| frontend
  frontend <-->|"Real API: upload, poll, result"| backend
  env -.-> backend
  env -.-> pipeline
  orchestrator --> pipeline
  orchestrator --> jobWorkspace
  stageTts -.->|hume| humeApi
  stageTts -.->|legacy| elevenApi
  stageLs -.->|optional| wav2lipLocal
```

---

## How to export

### Option A: Mermaid Live Editor (no install)

1. Copy the entire Mermaid code block above (from `flowchart LR` through the last `end`).
2. Open [Mermaid Live Editor](https://mermaid.live).
3. Paste the code into the editor.
4. Use **Actions** → **Download PNG** or **Download SVG** to save the diagram.

### Option B: Mermaid CLI (PNG/SVG in repo)

1. Install Node.js (required for `npx`).
2. From the project root, run:
   ```bash
   npx @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.png
   npx @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.svg
   ```
   Or use the script: `./scripts/export-architecture.sh` (Linux/macOS) or `scripts/export-architecture.ps1` (Windows).
3. Output files: `docs/architecture.png`, `docs/architecture.svg`.
