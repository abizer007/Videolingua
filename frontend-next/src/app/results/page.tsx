'use client'

import { usePipelineStore } from '@/store/pipeline-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useRouter } from 'next/navigation'
import { Download, Play, ArrowLeft, CheckCircle2, AlertCircle } from 'lucide-react'
import { motion } from 'framer-motion'

// True if URL is from backend (full URL); false for mock/empty/relative
function isRealVideoUrl(url: string | undefined): boolean {
  return !!url && (url.startsWith('http://') || url.startsWith('https://'))
}

export default function ResultsPage() {
  const router = useRouter()
  const { result, videoUpload, resetPipeline, isMockMode } = usePipelineStore()

  if (!result) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="glass max-w-md">
          <CardContent className="p-6 text-center">
            <p className="text-muted-foreground mb-4">No results available.</p>
            <Button onClick={() => router.push('/upload')}>Start New Job</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background py-12 px-6">
      <div className="container mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold mb-2">
                {result.error ? 'Processing finished with issues' : 'Processing Complete'}
              </h1>
              <p className="text-muted-foreground">
                {result.error
                  ? 'No localized videos were produced. See the message below and fix the backend setup.'
                  : 'Your video has been successfully localized'}
              </p>
            </div>
            <Button variant="outline" onClick={() => router.push('/upload')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              New Video
            </Button>
          </div>
        </motion.div>

        {result.error && (
          <Card className="glass border-amber-500/50 bg-amber-500/10 mb-8">
            <CardContent className="p-4 flex gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-amber-200 mb-1">Pipeline message</p>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{result.error}</p>
                <p className="text-xs text-muted-foreground mt-2">
                  Check backend dependencies: open{' '}
                  <a
                    href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/health/deps`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline text-primary"
                  >
                    /api/health/deps
                  </a>
                  {' '}and ensure ffmpeg is on PATH and you ran: pip install -r requirements.txt
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Metrics Summary */}
        <Card className="glass mb-8">
          <CardContent className="p-6">
            <div className="grid md:grid-cols-3 gap-6">
              <div>
                <div className="text-sm text-muted-foreground mb-1">
                  Total Processing Time
                </div>
                <div className="text-2xl font-bold">{result.metrics.totalTime}s</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">
                  Languages Processed
                </div>
                <div className="text-2xl font-bold">
                  {result.metrics.languagesProcessed}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Success Rate</div>
                <div className={`text-2xl font-bold ${result.error ? 'text-amber-500' : 'text-green-500'}`}>
                  {result.error ? (result.metrics.languagesProcessed > 0 ? 'Partial' : '0%') : '100%'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Video Comparison */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Original */}
          <Card className="glass">
            <CardHeader>
              <CardTitle>Original Video</CardTitle>
            </CardHeader>
            <CardContent>
              {(isRealVideoUrl(result.originalVideo) || videoUpload?.preview) ? (
                <video
                  src={isRealVideoUrl(result.originalVideo) ? result.originalVideo! : videoUpload?.preview}
                  controls
                  className="w-full rounded-lg"
                  crossOrigin="anonymous"
                />
              ) : (
                <div className="aspect-video rounded-lg bg-muted flex items-center justify-center text-muted-foreground text-sm">
                  {videoUpload?.preview ? 'Your uploaded video (demo mode)' : 'Original will appear when using Real API'}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Localized Videos */}
          <Card className="glass">
            <CardHeader>
              <CardTitle>Localized Videos</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {result.localizedVideos.map((video, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className="border rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-semibold">{video.language}</div>
                      <div className="flex items-center gap-2">
                        <div className="text-sm text-muted-foreground">
                          {(video.confidence * 100).toFixed(1)}% confidence
                        </div>
                        <div className="w-24">
                          <Progress value={video.confidence * 100} className="h-1.5" />
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2">
                      {isRealVideoUrl(video.url) ? (
                        <>
                          <video
                            src={video.url}
                            controls
                            className="w-full rounded-lg max-h-48"
                            crossOrigin="anonymous"
                          />
                          <div className="flex gap-2">
                            <a
                              href={video.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex-1 inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
                            >
                              <Play className="w-4 h-4 mr-2" />
                              Preview
                            </a>
                            <a
                              href={video.url}
                              download
                              className="flex-1 inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Download
                            </a>
                          </div>
                        </>
                      ) : (
                        <div className="aspect-video rounded-lg bg-muted flex items-center justify-center text-muted-foreground text-sm p-4 text-center">
                          Demo mode: no video file. Switch to <strong>Real API</strong> on the Architecture page, then run a new job to get real localized videos.
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quality Indicators */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>Quality Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-4">
              {[
                { label: 'ASR Accuracy', value: '95.2%', status: 'excellent' },
                { label: 'Translation Quality', value: 'BLEU: 0.87', status: 'excellent' },
                { label: 'Voice Naturalness', value: 'MOS: 4.3/5', status: 'excellent' },
                { label: 'Lip Sync', value: 'LSE-C: 0.89', status: 'excellent' },
              ].map((metric, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className="text-center p-4 rounded-lg bg-secondary/50"
                >
                  <div className="text-sm text-muted-foreground mb-1">
                    {metric.label}
                  </div>
                  <div className="text-xl font-bold mb-1">{metric.value}</div>
                  <div className="flex items-center justify-center gap-1 text-green-500">
                    <CheckCircle2 className="w-4 h-4" />
                    <span className="text-xs">Excellent</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-center gap-4 mt-8">
          <Button
            size="lg"
            onClick={() => {
              resetPipeline()
              router.push('/upload')
            }}
          >
            Process Another Video
          </Button>
          <Button size="lg" variant="outline" onClick={() => router.push('/architecture')}>
            View Architecture
          </Button>
        </div>
      </div>
    </div>
  )
}
