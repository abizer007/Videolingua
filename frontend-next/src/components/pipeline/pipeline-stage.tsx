'use client'

import { motion } from 'framer-motion'
import { PipelineStage } from '@/types'
import { CheckCircle2, Loader2, Circle, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PipelineStageProps {
  stage: PipelineStage
  label: string
  description: string
  progress: number
  metrics?: {
    label: string
    value: number | string
    unit?: string
  }[]
  isActive: boolean
  isComplete: boolean
  hasError: boolean
}

export function PipelineStageComponent({
  stage,
  label,
  description,
  progress,
  metrics = [],
  isActive,
  isComplete,
  hasError,
}: PipelineStageProps) {
  const getIcon = () => {
    if (hasError) return <XCircle className="w-6 h-6 text-destructive" />
    if (isComplete) return <CheckCircle2 className="w-6 h-6 text-green-500" />
    if (isActive) return <Loader2 className="w-6 h-6 text-primary animate-spin" />
    return <Circle className="w-6 h-6 text-muted-foreground" />
  }

  return (
    <motion.div
      className={cn(
        'glass rounded-xl p-6 border transition-all',
        isActive && 'border-primary shadow-lg shadow-primary/20',
        isComplete && 'border-green-500/50',
        hasError && 'border-destructive'
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 mt-1">{getIcon()}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold">{label}</h3>
            {isActive && (
              <span className="text-sm text-muted-foreground">{progress}%</span>
            )}
          </div>
          <p className="text-sm text-muted-foreground mb-4">{description}</p>
          
          {isActive && (
            <motion.div
              className="h-1.5 bg-secondary rounded-full overflow-hidden mb-4"
              initial={{ width: 0 }}
              animate={{ width: '100%' }}
            >
              <motion.div
                className="h-full bg-primary rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </motion.div>
          )}

          {metrics.length > 0 && (isActive || isComplete) && (
            <div className="grid grid-cols-2 gap-3 mt-4">
              {metrics.map((metric, idx) => (
                <motion.div
                  key={idx}
                  className="glass rounded-lg p-3"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: idx * 0.1 }}
                >
                  <div className="text-xs text-muted-foreground mb-1">
                    {metric.label}
                  </div>
                  <div className="text-lg font-semibold">
                    {typeof metric.value === 'number'
                      ? metric.value.toFixed(2)
                      : metric.value}
                    {metric.unit && <span className="text-xs ml-1">{metric.unit}</span>}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
