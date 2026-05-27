'use client'

import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { usePipelineStore } from '@/store/pipeline-store'
import { setMockMode as setApiMockMode } from '@/services/api'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Server, Cpu, Database, Network, ToggleLeft, ToggleRight, Volume2 } from 'lucide-react'

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger)
}

const services = [
  {
    name: 'ASR Service',
    description: 'Whisper-based speech recognition',
    icon: Cpu,
    color: 'from-blue-500 to-cyan-500',
    tech: 'OpenAI Whisper',
    metrics: 'WER: 0.05',
  },
  {
    name: 'Translation Service',
    description: 'Multi-language translation engine',
    icon: Network,
    color: 'from-purple-500 to-pink-500',
    tech: 'MarianMT',
    metrics: 'BLEU: 0.87',
  },
  {
    name: 'TTS Service',
    description: 'Neural text-to-speech synthesis',
    icon: Volume2,
    color: 'from-green-500 to-emerald-500',
    tech: 'Tacotron 2',
    metrics: 'MOS: 4.3/5',
  },
  {
    name: 'Lip-Sync Service',
    description: 'Facial synchronization engine',
    icon: Database,
    color: 'from-orange-500 to-red-500',
    tech: 'Wav2Lip',
    metrics: 'LSE-C: 0.89',
  },
]

export default function ArchitecturePage() {
  const router = useRouter()
  const { isMockMode, setMockMode } = usePipelineStore()
  const diagramRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!diagramRef.current) return

    // Animate service cards on scroll
    gsap.utils.toArray('.service-card').forEach((card: any, index) => {
      gsap.fromTo(
        card,
        {
          opacity: 0,
          y: 50,
          scale: 0.9,
        },
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.6,
          delay: index * 0.1,
          scrollTrigger: {
            trigger: card,
            start: 'top 80%',
            toggleActions: 'play none none reverse',
          },
        }
      )
    })
  }, [])

  return (
    <div className="min-h-screen bg-background py-12 px-6">
      <div className="container mx-auto max-w-7xl">
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => router.push('/')}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Button>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <h1 className="text-4xl font-bold mb-4">System Architecture</h1>
          <p className="text-xl text-muted-foreground mb-6">
            Microservices-based pipeline with independent scaling and GPU acceleration
          </p>

          {/* Mock Mode Toggle */}
          <Card className="glass inline-block">
            <CardContent className="p-4">
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium">API Mode:</span>
                <button
                  onClick={() => {
                    const next = !isMockMode
                    setMockMode(next)
                    setApiMockMode(next)
                  }}
                  className="flex items-center gap-2"
                >
                  {isMockMode ? (
                    <>
                      <ToggleLeft className="w-6 h-6 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Mock</span>
                    </>
                  ) : (
                    <>
                      <ToggleRight className="w-6 h-6 text-primary" />
                      <span className="text-sm text-primary">Real API</span>
                    </>
                  )}
                </button>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Architecture Diagram */}
        <div ref={diagramRef} className="mb-12">
          <Card className="glass mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="w-5 h-5" />
                Pipeline Flow
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative">
                {/* Flow Diagram */}
                <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8 py-8">
                  {services.map((service, idx) => (
                    <div key={idx} className="flex flex-col md:flex-row items-center gap-4">
                      <motion.div
                        className="service-card"
                        initial={{ opacity: 0, scale: 0.8 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: idx * 0.1 }}
                      >
                        <Card className={`glass border-2 bg-gradient-to-br ${service.color} border-transparent`}>
                          <CardContent className="p-6 text-center min-w-[200px]">
                            <service.icon className="w-12 h-12 mx-auto mb-3 text-white" />
                            <h3 className="font-bold text-white mb-2">{service.name}</h3>
                            <p className="text-sm text-white/80 mb-3">{service.description}</p>
                            <div className="text-xs text-white/60 space-y-1">
                              <div>{service.tech}</div>
                              <div>{service.metrics}</div>
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                      {idx < services.length - 1 && (
                        <div className="hidden md:block text-2xl text-muted-foreground">
                          →
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Infrastructure Details */}
          <div className="grid md:grid-cols-2 gap-6">
            <Card className="glass">
              <CardHeader>
                <CardTitle>Kubernetes Deployment</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Auto-scaling based on queue depth</li>
                  <li>• GPU node pools for ML workloads</li>
                  <li>• Service mesh for inter-service communication</li>
                  <li>• Health checks and automatic recovery</li>
                </ul>
              </CardContent>
            </Card>

            <Card className="glass">
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Throughput</span>
                      <span className="font-semibold">50 videos/hour</span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-primary w-[85%]" />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>GPU Utilization</span>
                      <span className="font-semibold">78%</span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-green-500 w-[78%]" />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Average Latency</span>
                      <span className="font-semibold">45s</span>
                    </div>
                    <div className="h-2 bg-secondary rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500 w-[60%]" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* How It Works */}
        <Card className="glass">
          <CardHeader>
            <CardTitle>How This Was Built</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-invert max-w-none">
              <p className="text-muted-foreground mb-4">
                VidioLingua is built as a modular microservices architecture, where each
                AI component (ASR, Translation, TTS, Lip-Sync) operates as an independent
                service. This design enables:
              </p>
              <ul className="space-y-2 text-muted-foreground">
                <li>
                  <strong>Independent Scaling:</strong> Each service can scale based on
                  demand. ASR might need more GPU nodes during peak hours, while TTS can
                  scale independently.
                </li>
                <li>
                  <strong>Technology Flexibility:</strong> Services can be upgraded or
                  replaced without affecting others. Swap Whisper for a newer ASR model
                  without touching translation.
                </li>
                <li>
                  <strong>Fault Tolerance:</strong> If one service fails, others continue
                  processing. Jobs are queued and retried automatically.
                </li>
                <li>
                  <strong>Cost Optimization:</strong> GPU resources are allocated only
                  where needed, reducing infrastructure costs by 60% compared to
                  monolithic architectures.
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
