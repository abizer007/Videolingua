export type PipelineStage = 'idle' | 'uploading' | 'asr' | 'translation' | 'tts' | 'lipsync' | 'complete' | 'error'

export type Language = {
  code: string
  name: string
  flag: string
}

export type JobStatus = {
  jobId: string
  stage: PipelineStage
  progress: number
  currentLanguage?: string
  languages?: string[]
  sourceLanguage?: string
  sourceLanguageConfidence?: number
  error?: string
  metrics?: {
    wer?: number // Word Error Rate (ASR)
    bleu?: number // BLEU Score (Translation)
    mos?: number // Mean Opinion Score (TTS)
    lseC?: number // Lip Sync Error (Lip-sync)
  }
}

export type VideoUpload = {
  file: File
  preview?: string
  duration?: number
  size: number
}

export type ProcessingResult = {
  jobId: string
  originalVideo: string
  localizedVideos: {
    language: string
    url: string
    confidence: number
  }[]
  metrics: {
    totalTime: number
    languagesProcessed: number
  }
  /** Set when pipeline failed or produced no dubbed videos */
  error?: string
}

export type VoiceOption = {
  id: string
  name: string
  gender: 'male' | 'female' | 'neutral'
  emotion?: 'neutral' | 'happy' | 'sad' | 'excited'
  cloned?: boolean
}
