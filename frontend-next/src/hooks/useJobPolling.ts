import { useEffect, useRef } from 'react'
import { usePipelineStore } from '@/store/pipeline-store'
import { apiService } from '@/services/api'

export function useJobPolling() {
  const { currentJob, updateJobStatus, setResult } = usePipelineStore()
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!currentJob || currentJob.stage === 'complete' || currentJob.stage === 'error') {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    // Poll job status every 1 second
    intervalRef.current = setInterval(async () => {
      try {
        const status = await apiService.getJobStatus(currentJob.jobId)
        updateJobStatus(status)

        // If complete, fetch result
        if (status.stage === 'complete') {
          const result = await apiService.getResult(currentJob.jobId)
          setResult(result)
        }
      } catch (error) {
        updateJobStatus({ error: 'Failed to fetch job status' })
      }
    }, 1000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [currentJob, updateJobStatus, setResult])
}
