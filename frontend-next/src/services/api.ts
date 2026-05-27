import axios from 'axios'
import { JobStatus, ProcessingResult, VideoUpload } from '@/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

// Mock mode flag
let mockMode = true

export const setMockMode = (mock: boolean) => {
  mockMode = mock
}

export const apiService = {
  /**
   * Upload video and start processing
   */
  async uploadVideo(
    file: File,
    languages: string[],
    voiceOptions: any,
    sourceLanguage?: string,
    voiceSample?: File | null
  ): Promise<{ jobId: string }> {
    if (mockMode) {
      // Simulate upload delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      return { jobId: `job_${Date.now()}` }
    }

    const formData = new FormData()
    formData.append('video', file)
    formData.append('languages', JSON.stringify(languages))
    formData.append('voiceOptions', JSON.stringify(voiceOptions))
    if (sourceLanguage) {
      formData.append('sourceLanguage', sourceLanguage)
    }
    if (voiceSample) {
      formData.append('voiceSample', voiceSample)
    }

    const response = await api.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  /**
   * Get job status
   */
  async getJobStatus(jobId: string): Promise<JobStatus> {
    if (mockMode) {
      // Return mock status based on time elapsed
      const mockStatus = generateMockStatus(jobId)
      return mockStatus
    }

    const response = await api.get(`/api/job-status/${jobId}`)
    return response.data
  },

  /**
   * Get processing result
   */
  async getResult(jobId: string): Promise<ProcessingResult> {
    if (mockMode) {
      return generateMockResult(jobId)
    }

    const response = await api.get(`/api/result/${jobId}`)
    return response.data
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    try {
      const response = await api.get('/api/health')
      return response.data
    } catch {
      return { status: 'unavailable' }
    }
  },
}

// Mock status generator
function generateMockStatus(jobId: string): JobStatus {
  const stages: Array<{ stage: JobStatus['stage']; progress: number }> = [
    { stage: 'uploading', progress: 10 },
    { stage: 'asr', progress: 30 },
    { stage: 'translation', progress: 50 },
    { stage: 'tts', progress: 75 },
    { stage: 'lipsync', progress: 90 },
    { stage: 'complete', progress: 100 },
  ]

  // Simulate progression based on jobId timestamp
  const jobTime = parseInt(jobId.split('_')[1]) || Date.now()
  const elapsed = Date.now() - jobTime
  const stageIndex = Math.min(
    Math.floor(elapsed / 3000), // 3 seconds per stage
    stages.length - 1
  )

  const currentStage = stages[stageIndex]
  const progress = Math.min(
    currentStage.progress + ((elapsed % 3000) / 3000) * 20,
    100
  )

  return {
    jobId,
    stage: currentStage.stage,
    progress: Math.round(progress),
    currentLanguage: ['Hindi', 'Spanish', 'French', 'German', 'Japanese', 'Chinese', 'Arabic', 'Portuguese'][stageIndex % 8],
    languages: ['Hindi', 'Spanish', 'French', 'German', 'Japanese', 'Chinese', 'Arabic', 'Portuguese'],
    sourceLanguage: 'English',
    sourceLanguageConfidence: 0.93,
    metrics: {
      wer: stageIndex >= 1 ? 0.05 + Math.random() * 0.1 : undefined,
      bleu: stageIndex >= 2 ? 0.75 + Math.random() * 0.2 : undefined,
      mos: stageIndex >= 3 ? 4.0 + Math.random() * 0.8 : undefined,
      lseC: stageIndex >= 4 ? 0.85 + Math.random() * 0.1 : undefined,
    },
  }
}

// Mock result generator - no real video URLs (they would 404 on frontend)
function generateMockResult(jobId: string): ProcessingResult {
  return {
    jobId,
    originalVideo: '',
    localizedVideos: [
      { language: 'Hindi', url: '', confidence: 0.87 },
      { language: 'Spanish', url: '', confidence: 0.92 },
      { language: 'French', url: '', confidence: 0.89 },
      { language: 'German', url: '', confidence: 0.86 },
      { language: 'Japanese', url: '', confidence: 0.83 },
      { language: 'Chinese', url: '', confidence: 0.85 },
      { language: 'Arabic', url: '', confidence: 0.81 },
      { language: 'Portuguese', url: '', confidence: 0.88 },
    ],
    metrics: {
      totalTime: 45,
      languagesProcessed: 8,
    },
  }
}
