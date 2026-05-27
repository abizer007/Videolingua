'use client'

import { motion } from 'framer-motion'

interface WaveformProps {
  className?: string
  bars?: number
  animated?: boolean
}

export function Waveform({ className = '', bars = 20, animated = true }: WaveformProps) {
  return (
    <div className={`flex items-end justify-center gap-1 h-16 ${className}`}>
      {Array.from({ length: bars }).map((_, i) => (
        <motion.div
          key={i}
          className="bg-primary rounded-t w-1"
          initial={{ height: '20%' }}
          animate={
            animated
              ? {
                  height: ['20%', `${20 + Math.random() * 60}%`, '20%'],
                }
              : { height: '20%' }
          }
          transition={{
            duration: 0.5 + Math.random() * 0.5,
            repeat: Infinity,
            delay: i * 0.05,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  )
}
