'use client'

import { useEffect } from 'react'
import { usePipelineStore } from '@/store/pipeline-store'
import { useJobPolling } from '@/hooks/useJobPolling'
import { PipelineVisualizer } from '@/components/pipeline/pipeline-visualizer'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useRouter } from 'next/navigation'
import { ArrowLeft, CheckCircle2 } from 'lucide-react'

export default function PipelinePage() {
  const router = useRouter()
  const { currentJob, result, resetPipeline } = usePipelineStore()
  useJobPolling()

  useEffect(() => {
    if (result) {
      // Redirect to results page after a delay
      const timeoutId = setTimeout(() => {
        router.push('/results')
      }, 2000)

      // Cleanup: clear timeout if component unmounts or effect re-runs
      return () => {
        clearTimeout(timeoutId)
      }
    }
  }, [result, router])

  if (!currentJob) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="glass max-w-md">
          <CardContent className="p-6 text-center">
            <p className="text-muted-foreground mb-4">
              No active job. Please upload a video first.
            </p>
            <Button onClick={() => router.push('/upload')}>Go to Upload</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background py-12 px-6">
      <div className="container mx-auto max-w-6xl">
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => router.push('/upload')}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Upload
          </Button>
        </div>

        {/* Overall Progress */}
        <Card className="glass mb-8">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold">Processing Pipeline</h2>
              <span className="text-lg font-semibold">{currentJob.progress}%</span>
            </div>
            <Progress value={currentJob.progress} className="h-3" />
            {currentJob.stage === 'complete' && (
              <div className="mt-4 flex items-center gap-2 text-green-500">
                <CheckCircle2 className="w-5 h-5" />
                <span>Processing complete!</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pipeline Visualizer */}
        <PipelineVisualizer />

        {/* Error State */}
        {currentJob.error && (
          <Card className="glass border-destructive mt-6">
            <CardContent className="p-6">
              <p className="text-destructive">{currentJob.error}</p>
              <Button
                variant="outline"
                onClick={() => {
                  resetPipeline()
                  router.push('/upload')
                }}
                className="mt-4"
              >
                Reset Pipeline
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
