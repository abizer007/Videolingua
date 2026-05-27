# VidioLingua — System Architecture

For a **one-page diagram for export** (PNG/SVG), see [SYSTEM_ARCHITECTURE_EXPORT.md](SYSTEM_ARCHITECTURE_EXPORT.md).

## Full system architecture (high-level + pipeline + data flow)

```mermaid
flowchart TB
  subgraph USER["👤 User"]
    BROWSER["Browser"]
  end

  subgraph FRONTEND["🖥️ Frontend (Next.js)"]
    direction TB
    PAGES["Pages: /, /upload, /pipeline, /results, /architecture"]
    API_MODE["API Mode: Real API | Mock"]
    STATE["State: jobId, progress, result URLs"]
    PAGES --> API_MODE
    API_MODE --> STATE
  end

  subgraph BACKEND["⚙️ Backend (FastAPI)"]
    direction TB
    ROUTES["Routes"]
    JOB_STORE["Job Store (in-memory)"]
    ORCHESTRATOR["Pipeline Runner (background thread)"]
    
    subgraph ROUTES
      R_ROOT["GET /"]
      R_HEALTH["GET /api/health"]
      R_DEPS["GET /api/health/deps"]
      R_TTS_HEALTH["GET /tts-health, /api/tts-health"]
      R_UPLOAD["POST /api/upload"]
      R_STATUS["GET /api/job-status/:id"]
      R_RESULT["GET /api/result/:id"]
      R_FILE["GET /api/result/:id/file/:name"]
    end
    
    R_UPLOAD --> JOB_STORE
    R_UPLOAD --> ORCHESTRATOR
    R_STATUS --> JOB_STORE
    R_RESULT --> JOB_STORE
    R_FILE --> FILESYSTEM
  end

  subgraph FILESYSTEM["📁 Job workspace (JOBS_DIR)"]
    direction LR
    JOB_DIR["jobs/<job_id>/"]
    JOB_DIR --> INPUT_VIDEO["input_video.mp4"]
    JOB_DIR --> RESULTS_DIR["results/"]
    RESULTS_DIR --> DUBBED["*_dubbed_<lang>.mp4"]
    RESULTS_DIR --> ORIG_COPY["input_video.mp4"]
  end

  subgraph PIPELINE["🔄 Pipeline stages (orchestrated by backend)"]
    direction LR
    
    subgraph STAGE_ASR["1. ASR"]
      direction TB
      A_IN["asr/input/"]
      A_FF["ffmpeg extract audio"]
      A_WHISPER["faster-whisper (Whisper base)"]
      A_OUT["asr/output/*_transcription.json"]
      A_IN --> A_FF --> A_WHISPER --> A_OUT
    end
    
    subgraph STAGE_MT["2. Translation"]
      direction TB
      M_IN["translation/input/"]
      M_DT["deep-translator"]
      M_OUT["translation/output/*_<lang>.json"]
      M_IN --> M_DT --> M_OUT
    end
    
    subgraph STAGE_TTS["3. TTS"]
      direction TB
      T_IN["tts/input/"]
      T_ENGINE["VIDIOLINGUA_TTS_ENGINE"]
      T_HUME["Hume API (HUME_API_KEY)"]
      T_XTTS["XTTS (optional)"]
      T_LEGACY["Legacy: gTTS / ElevenLabs"]
      T_OUT["tts/output/*.wav"]
      T_IN --> T_ENGINE
      T_ENGINE --> T_HUME
      T_ENGINE --> T_XTTS
      T_ENGINE --> T_LEGACY
      T_HUME --> T_OUT
      T_XTTS --> T_OUT
      T_LEGACY --> T_OUT
    end
    
    subgraph STAGE_LS["4. Lip-sync"]
      direction TB
      L_IN["lipsync/input/"]
      L_W2L["Wav2Lip (if VIDIOLINGUA_WAV2LIP_DIR)"]
      L_FF["ffmpeg (fallback)"]
      L_OUT["lipsync/output/*_dubbed_<lang>.mp4"]
      L_IN --> L_W2L
      L_IN --> L_FF
      L_W2L --> L_OUT
      L_FF --> L_OUT
    end
    
    STAGE_ASR --> STAGE_MT --> STAGE_TTS --> STAGE_LS
  end

  subgraph EXTERNAL["☁️ External services"]
    HUME_API["Hume AI TTS API"]
    ELEVEN["ElevenLabs API (optional)"]
    W2L_REPO["Wav2Lip (local repo)"]
  end

  BROWSER <-->|"HTTP (NEXT_PUBLIC_API_URL)"| FRONTEND
  FRONTEND <-->|"Real API: upload, poll, result"| BACKEND
  ORCHESTRATOR --> PIPELINE
  ORCHESTRATOR --> FILESYSTEM
  STAGE_TTS -.->|"hume"| HUME_API
  STAGE_TTS -.->|"legacy + key"| ELEVEN
  STAGE_LS -.->|"optional"| W2L_REPO
```

---

## Pipeline data flow (artifacts)

```mermaid
flowchart LR
  subgraph IN["Input"]
    V["video.mp4"]
  end

  subgraph ASR["ASR"]
    V --> A_JSON["transcription.json\n(segments, language)"]
  end

  subgraph MT["Translation"]
    A_JSON --> M_JSON["*_transcription_hi.json\n*_transcription_es.json\n..."]
  end

  subgraph TTS["TTS"]
    M_JSON --> WAV["*_hi.wav, *_es.wav\n... (one per language)"]
  end

  subgraph LS["Lip-sync"]
    V --> LS_IN
    WAV --> LS_IN["video + wavs"]
    LS_IN --> MP4["*_dubbed_hi.mp4\n*_dubbed_es.mp4\n..."]
  end

  subgraph OUT["Results"]
    MP4 --> DOWNLOAD["Served via /api/result/:id/file/:name"]
  end
```

---

## TTS engine selection & fallback

```mermaid
flowchart TB
  START["Request: synthesize text → WAV"]
  ENV["VIDIOLINGUA_TTS_ENGINE"]
  
  ENV --> HUME{"hume?"}
  ENV --> XTTS{"xtts?"}
  ENV --> LEGACY["legacy"]
  
  HUME -->|yes| HUME_CALL["Call Hume API\n(HUME_API_KEY)"]
  HUME_CALL --> HUME_OK{"OK?"}
  HUME_OK -->|yes| WAV["Write WAV"]
  HUME_OK -->|no| FALLBACK["Fallback to legacy"]
  
  XTTS -->|yes| XTTS_CALL["app.services.xtts_tts_service"]
  XTTS_CALL --> WAV
  
  LEGACY --> LEGACY_LOGIC["ElevenLabs (if key) else gTTS"]
  FALLBACK --> LEGACY_LOGIC
  LEGACY_LOGIC --> FFMPEG["ffmpeg → WAV"]
  FFMPEG --> WAV
```

---

## Lip-sync path (Wav2Lip vs ffmpeg)

```mermaid
flowchart TB
  INPUT["video + per-language WAVs"]
  W2L_DIR["VIDIOLINGUA_WAV2LIP_DIR set?"]
  
  INPUT --> W2L_DIR
  W2L_DIR -->|yes| RUN_W2L["Run Wav2Lip inference.py"]
  W2L_DIR -->|no| RUN_FF["ffmpeg: replace audio track"]
  
  RUN_W2L --> W2L_OK{"Success?"}
  W2L_OK -->|yes| MP4["*_dubbed_<lang>.mp4"]
  W2L_OK -->|no| RUN_FF
  RUN_FF --> MP4
```

---

## Component stack (summary)

| Layer        | Technology / component |
|-------------|-------------------------|
| Frontend    | Next.js 14, React       |
| Backend     | FastAPI, Uvicorn        |
| ASR         | faster-whisper (Whisper), ffmpeg |
| Translation | deep-translator        |
| TTS         | Hume API, XTTS (opt), gTTS, ElevenLabs |
| Lip-sync    | Wav2Lip (opt), ffmpeg   |
| Storage     | In-memory job store, filesystem (jobs/) |

---

## Environment-driven behavior

```mermaid
flowchart LR
  subgraph ENV["Environment"]
    TTS_ENGINE["VIDIOLINGUA_TTS_ENGINE"]
    HUME_KEY["HUME_API_KEY"]
    EL_KEY["ELEVENLABS_API_KEY"]
    W2L_DIR["VIDIOLINGUA_WAV2LIP_DIR"]
    TARGET_LANG["VIDIOLINGUA_TARGET_LANGUAGES"]
  end

  subgraph BEHAVIOR["Runtime behavior"]
    TTS_CHOICE["TTS: hume | xtts | legacy"]
    LIP_CHOICE["Lip-sync: Wav2Lip | ffmpeg"]
    LANGUAGES["Target languages (hi,es,fr,...)"]
  end

  TTS_ENGINE --> TTS_CHOICE
  HUME_KEY --> TTS_CHOICE
  EL_KEY --> TTS_CHOICE
  W2L_DIR --> LIP_CHOICE
  TARGET_LANG --> LANGUAGES
```

---

*Generated for VidioLingua. Render these Mermaid blocks in GitHub, GitLab, or any Mermaid-compatible viewer.*
