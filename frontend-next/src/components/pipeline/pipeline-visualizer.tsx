'use client'

import { motion } from 'framer-motion'
import { usePipelineStore } from '@/store/pipeline-store'
import { PipelineStageComponent } from './pipeline-stage'
import { Waveform } from '../motion/waveform'
import { PipelineStage } from '@/types'

const stages: Array<{
  stage: PipelineStage
  label: string
  description: string
  getMetrics: (status: any) => Array<{ label: string; value: number | string; unit?: string }>
}> = [
  {
    stage: 'asr',
    label: 'Automatic Speech Recognition',
    description: 'Extracting spoken text from video with precise timestamps',
    getMetrics: (status) => [
      { label: 'Word Error Rate', value: status.metrics?.wer || 0, unit: '' },
      { label: 'Confidence', value: (1 - (status.metrics?.wer || 0)) * 100, unit: '%' },
    ],
  },
  {
    stage: 'translation',
    label: 'Machine Translation',
    description: 'Translating text into target languages while preserving timing',
    getMetrics: (status) => [
      { label: 'BLEU Score', value: status.metrics?.bleu || 0, unit: '' },
      { label: 'Languages', value: status.languages?.length || 0, unit: '' },
    ],
  },
  {
    stage: 'tts',
    label: 'Text-to-Speech Synthesis',
    description: 'Generating natural-sounding voice in target languages',
    getMetrics: (status) => [
      { label: 'MOS Score', value: status.metrics?.mos || 0, unit: '/5.0' },
      { label: 'Quality', value: status.metrics?.mos ? (status.metrics.mos > 4 ? 'Excellent' : 'Good') : 'N/A', unit: '' },
    ],
  },
  {
    stage: 'lipsync',
    label: 'Lip Synchronization',
    description: 'Synchronizing generated audio with video lip movements',
    getMetrics: (status) => [
      { label: 'LSE-C Score', value: status.metrics?.lseC || 0, unit: '' },
      { label: 'Sync Quality', value: status.metrics?.lseC ? (status.metrics.lseC > 0.8 ? 'Excellent' : 'Good') : 'N/A', unit: '' },
    ],
  },
]

export function PipelineVisualizer() {
  const { currentJob } = usePipelineStore()

  if (!currentJob) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Upload a video to start the AI pipeline
      </div>
    )
  }

  const jobComplete = currentJob.stage === 'complete'
  const hasError = currentJob.stage === 'error'
  
  // When job is complete, all stages should be marked complete
  // When job is in progress, find the current stage index
  const currentStageIndex = jobComplete 
    ? stages.length // Set to length so all stages are complete
    : stages.findIndex((s) => s.stage === currentJob.stage)

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-2">AI Pipeline Processing</h2>
        <p className="text-muted-foreground">
          Real-time visualization of the localization pipeline
        </p>
      </div>

      {currentJob.stage !== 'idle' && currentJob.stage !== 'uploading' && (
        <div className="mb-8">
          <Waveform animated={!jobComplete && !hasError} />
        </div>
      )}

      <div className="space-y-4">
        {stages.map((stageConfig, index) => {
          const isActive = currentJob.stage === stageConfig.stage
          // When complete, all stages should be complete (index < stages.length is always true)
          // When in progress, mark stages before current as complete
          const isStageComplete = jobComplete ? true : index < currentStageIndex
          const progress = isActive ? currentJob.progress : isStageComplete ? 100 : 0

          return (
            <PipelineStageComponent
              key={stageConfig.stage}
              stage={stageConfig.stage}
              label={stageConfig.label}
              description={stageConfig.description}
              progress={progress}
              metrics={isActive || isStageComplete ? stageConfig.getMetrics(currentJob) : []}
              isActive={isActive}
              isComplete={isStageComplete}
              hasError={hasError && isActive}
            />
          )
        })}
      </div>

      {(currentJob.currentLanguage || currentJob.sourceLanguage) && (
        <motion.div
          className="glass rounded-lg p-4 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {currentJob.sourceLanguage && (
            <div className="mb-3">
              <p className="text-sm text-muted-foreground">Detected source language:</p>
              <p className="text-lg font-semibold mt-1">
                {currentJob.sourceLanguage}
                {typeof currentJob.sourceLanguageConfidence === 'number' && (
                  <span className="text-xs text-muted-foreground ml-2">
                    ({Math.round(currentJob.sourceLanguageConfidence * 100)}% confidence)
                  </span>
                )}
              </p>
            </div>
          )}
          {currentJob.currentLanguage && (
            <>
              <p className="text-sm text-muted-foreground">Currently processing:</p>
              <p className="text-lg font-semibold mt-1">{currentJob.currentLanguage}</p>
            </>
          )}
        </motion.div>
      )}
    </div>
  )
}
