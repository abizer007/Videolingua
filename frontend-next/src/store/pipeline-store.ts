import { create } from 'zustand'
import { PipelineStage, JobStatus, VideoUpload, ProcessingResult, Language } from '@/types'

interface PipelineState {
  // Current job
  currentJob: JobStatus | null
  videoUpload: VideoUpload | null
  selectedLanguages: Language[]
  sourceLanguage: string | null
  sourceLanguageConfidence: number | null
  voiceSample: File | null
  voiceOptions: {
    gender: 'male' | 'female' | 'neutral'
    emotion: 'neutral' | 'happy' | 'sad' | 'excited'
    cloned: boolean
  }
  
  // Results
  result: ProcessingResult | null
  
  // UI State
  isMockMode: boolean
  showArchitecture: boolean
  
  // Actions
  setVideoUpload: (upload: VideoUpload | null) => void
  setSelectedLanguages: (languages: Language[]) => void
  setSourceLanguage: (language: string | null, confidence?: number | null) => void
  setVoiceSample: (sample: File | null) => void
  setVoiceOptions: (options: Partial<PipelineState['voiceOptions']>) => void
  startJob: (jobId: string) => void
  updateJobStatus: (status: Partial<JobStatus>) => void
  setResult: (result: ProcessingResult) => void
  resetPipeline: () => void
  setMockMode: (mock: boolean) => void
  setShowArchitecture: (show: boolean) => void
}

const initialState = {
  currentJob: null,
  videoUpload: null,
  selectedLanguages: [],
  sourceLanguage: null,
  sourceLanguageConfidence: null,
  voiceSample: null,
  voiceOptions: {
    gender: 'neutral' as const,
    emotion: 'neutral' as const,
    cloned: false,
  },
  result: null,
  isMockMode: true,
  showArchitecture: false,
}

export const usePipelineStore = create<PipelineState>((set) => ({
  ...initialState,
  
  setVideoUpload: (upload) => set({ videoUpload: upload }),
  
  setSelectedLanguages: (languages) => set({ selectedLanguages: languages }),

  setSourceLanguage: (language, confidence = null) =>
    set({ sourceLanguage: language, sourceLanguageConfidence: confidence }),

  setVoiceSample: (sample) => set({ voiceSample: sample }),
  
  setVoiceOptions: (options) => 
    set((state) => ({ 
      voiceOptions: { ...state.voiceOptions, ...options } 
    })),
  
  startJob: (jobId) => set({
    currentJob: {
      jobId,
      stage: 'uploading',
      progress: 0,
    }
  }),
  
  updateJobStatus: (status) => 
    set((state) => ({
      currentJob: state.currentJob 
        ? { ...state.currentJob, ...status }
        : null
    })),
  
  setResult: (result) => set({ result }),
  
  resetPipeline: () =>
    set((state) => ({
      ...initialState,
      isMockMode: state.isMockMode,
    })),
  
  setMockMode: (mock) => {
    set({ isMockMode: mock })
    if (typeof window !== 'undefined') {
      localStorage.setItem('vidiolingua_mock_mode', mock ? 'true' : 'false')
    }
  },

  setShowArchitecture: (show) => set({ showArchitecture: show }),
}))
