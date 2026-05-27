'use client'

import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowRight, Globe, DollarSign, Clock, TrendingUp } from 'lucide-react'

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger)
}

export default function LandingPage() {
  const heroRef = useRef<HTMLDivElement>(null)
  const headlineRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (!headlineRef.current) return

    // Animate headline on mount
    gsap.fromTo(
      headlineRef.current,
      {
        opacity: 0,
        y: 50,
      },
      {
        opacity: 1,
        y: 0,
        duration: 1.2,
        ease: 'power3.out',
      }
    )

    // Scroll-triggered animations
    gsap.utils.toArray('.animate-on-scroll').forEach((element: any) => {
      gsap.fromTo(
        element,
        {
          opacity: 0,
          y: 60,
        },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: element,
            start: 'top 80%',
            toggleActions: 'play none none reverse',
          },
        }
      )
    })
  }, [])

  return (
    <div className="min-h-screen gradient-mesh">
      {/* Header */}
      <header className="fixed top-0 w-full z-50 glass-strong border-b border-white/10">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="text-2xl font-bold bg-gradient-to-r from-primary to-purple-500 bg-clip-text text-transparent">
            VidioLingua
          </div>
          <nav className="flex gap-6">
            <Link href="/upload" className="text-sm hover:text-primary transition-colors">
              Upload
            </Link>
            <Link href="/pipeline" className="text-sm hover:text-primary transition-colors">
              Pipeline
            </Link>
            <Link href="/architecture" className="text-sm hover:text-primary transition-colors">
              Architecture
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section ref={heroRef} className="pt-32 pb-20 px-6">
        <div className="container mx-auto text-center">
          <motion.h1
            ref={headlineRef}
            className="text-6xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-primary to-purple-400 bg-clip-text text-transparent"
          >
            Translate Any Video.
            <br />
            Speak Every Language.
          </motion.h1>
          <motion.p
            className="text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8 }}
          >
            Advanced AI pipeline for seamless video localization. From speech recognition
            to lip-sync, all in one intelligent system.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.8 }}
          >
            <Link href="/upload">
              <Button size="lg" className="text-lg px-8 py-6">
                Localize a Video
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto">
          <motion.h2
            className="text-4xl font-bold text-center mb-16 animate-on-scroll"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            The Problem
          </motion.h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Globe,
                title: 'Language Barriers',
                description:
                  'Content creators struggle to reach global audiences. Only 25% of internet users speak English.',
              },
              {
                icon: DollarSign,
                title: 'Expensive Dubbing',
                description:
                  'Traditional dubbing costs $5,000-$50,000 per video. Professional voice actors and extensive post-production required.',
              },
              {
                icon: Clock,
                title: 'Time-Consuming',
                description:
                  'Manual translation and dubbing processes take weeks or months. Multiple rounds of revisions delay content delivery.',
              },
            ].map((problem, idx) => (
              <motion.div
                key={idx}
                className="animate-on-scroll"
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
              >
                <Card className="glass h-full">
                  <CardContent className="p-6">
                    <problem.icon className="w-12 h-12 text-primary mb-4" />
                    <h3 className="text-xl font-semibold mb-3">{problem.title}</h3>
                    <p className="text-muted-foreground">{problem.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto">
          <motion.div
            className="text-center max-w-4xl mx-auto animate-on-scroll"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl font-bold mb-6">Our Solution</h2>
            <p className="text-xl text-muted-foreground mb-12">
              VidioLingua automates the entire video translation pipeline. Convert videos
              from English to multiple target languages (Hindi, Spanish, French, and 100+ more)
              in minutes instead of weeks.
            </p>
            <div className="grid md:grid-cols-2 gap-8 mt-12">
              <Card className="glass">
                <CardContent className="p-6">
                  <TrendingUp className="w-10 h-10 text-primary mb-4" />
                  <h3 className="text-2xl font-bold mb-2">95% Cost Reduction</h3>
                  <p className="text-muted-foreground">
                    From $50,000 to $2,500 per video. Automated pipeline eliminates
                    manual labor costs.
                  </p>
                </CardContent>
              </Card>
              <Card className="glass">
                <CardContent className="p-6">
                  <Clock className="w-10 h-10 text-primary mb-4" />
                  <h3 className="text-2xl font-bold mb-2">99% Time Savings</h3>
                  <p className="text-muted-foreground">
                    From 4-6 weeks to 30-60 minutes. Real-time processing with parallel
                    language generation.
                  </p>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Market Stats */}
      <section className="py-20 px-6">
        <div className="container mx-auto">
          <motion.h2
            className="text-4xl font-bold text-center mb-16 animate-on-scroll"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            Market Opportunity
          </motion.h2>
          <div className="grid md:grid-cols-4 gap-8">
            {[
              { value: '$12B', label: 'Global Dubbing Market' },
              { value: '500M+', label: 'Videos to Localize' },
              { value: '100+', label: 'Languages Supported' },
              { value: '95%', label: 'Cost Reduction' },
            ].map((stat, idx) => (
              <motion.div
                key={idx}
                className="text-center animate-on-scroll"
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1, type: 'spring' }}
              >
                <div className="text-5xl font-bold bg-gradient-to-r from-primary to-purple-500 bg-clip-text text-transparent mb-2">
                  {stat.value}
                </div>
                <div className="text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="container mx-auto text-center">
          <motion.div
            className="animate-on-scroll"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl font-bold mb-6">Ready to Localize?</h2>
            <p className="text-xl text-muted-foreground mb-8">
              Experience the future of video translation
            </p>
            <Link href="/upload">
              <Button size="lg" className="text-lg px-8 py-6">
                Start Your Demo
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-12 px-6">
        <div className="container mx-auto text-center text-muted-foreground">
          <p>&copy; 2024 VidioLingua. Techgium PoC.</p>
        </div>
      </footer>
    </div>
  )
}
