'use client'

import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { usePipelineStore } from '@/store/pipeline-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { apiService } from '@/services/api'
import { Upload, Video, Languages, Volume2, User, Mic, Sparkles } from 'lucide-react'

const uploadSchema = z.object({
  languages: z.array(z.string()).min(1, 'Select at least one language'),
  sourceLanguage: z.string().optional(),
  gender: z.enum(['male', 'female', 'neutral']),
  emotion: z.enum(['neutral', 'happy', 'sad', 'excited']),
  cloned: z.boolean(),
})

type UploadFormData = z.infer<typeof uploadSchema>

const languages = [
  { code: 'hi', name: 'Hindi', flag: '🇮🇳' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'de', name: 'German', flag: '🇩🇪' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳' },
  { code: 'ar', name: 'Arabic', flag: '🇸🇦' },
  { code: 'pt', name: 'Portuguese', flag: '🇵🇹' },
]

const sourceLanguages = [
  { code: 'auto', name: 'Auto-detect', flag: '✨' },
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'hi', name: 'Hindi', flag: '🇮🇳' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'de', name: 'German', flag: '🇩🇪' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳' },
  { code: 'ar', name: 'Arabic', flag: '🇸🇦' },
  { code: 'pt', name: 'Portuguese', flag: '🇵🇹' },
]

export default function UploadPage() {
  const router = useRouter()
  const {
    setVideoUpload,
    setSelectedLanguages,
    setVoiceOptions,
    setSourceLanguage,
    setVoiceSample,
    startJob,
    isMockMode,
  } = usePipelineStore()
  const [file, setFile] = useState<File | null>(null)
  const [voiceSampleFile, setVoiceSampleFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<UploadFormData>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      languages: [],
      sourceLanguage: 'auto',
      gender: 'neutral',
      emotion: 'neutral',
      cloned: false,
    },
  })

  const selectedLanguages = watch('languages')
  const selectedSourceLanguage = watch('sourceLanguage')

  // Cleanup preview URL on unmount
  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview)
      }
    }
  }, [preview])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const videoFile = acceptedFiles[0]
    if (videoFile) {
      // Clean up previous preview URL if it exists
      if (preview) {
        URL.revokeObjectURL(preview)
      }

      setFile(videoFile)
      const previewUrl = URL.createObjectURL(videoFile)
      setPreview(previewUrl)

      // Set video upload in store
      setVideoUpload({
        file: videoFile,
        preview: previewUrl,
        size: videoFile.size,
      })
    }
  }, [setVideoUpload, preview])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.webm'],
    },
    maxFiles: 1,
  })

  const toggleLanguage = (code: string) => {
    const current = selectedLanguages || []
    const updated = current.includes(code)
      ? current.filter((l) => l !== code)
      : [...current, code]
    setValue('languages', updated)
    setSelectedLanguages(
      languages.filter((l) => updated.includes(l.code)).map((l) => ({
        code: l.code,
        name: l.name,
        flag: l.flag,
      }))
    )
  }

  const onSubmit = async (data: UploadFormData) => {
    if (!file) return

    setUploading(true)
    try {
      const { jobId } = await apiService.uploadVideo(
        file,
        data.languages,
        {
          gender: data.gender,
          emotion: data.emotion,
          cloned: data.cloned,
        },
        data.sourceLanguage,
        voiceSampleFile
      )

      setVoiceOptions({
        gender: data.gender,
        emotion: data.emotion,
        cloned: data.cloned,
      })
      setSourceLanguage(data.sourceLanguage === 'auto' ? null : (data.sourceLanguage || null))
      setVoiceSample(voiceSampleFile)

      startJob(jobId)
      router.push('/pipeline')
    } catch (error) {
      console.error('Upload failed:', error)
      alert('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background gradient-mesh py-20 px-6">
      <div className="container mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mb-10 text-center"
        >
          <h1 className="text-5xl font-extrabold mb-4 bg-gradient-to-br from-primary via-purple-400 to-accent bg-clip-text text-transparent drop-shadow-sm">
            Launch Localization
          </h1>
          <p className="text-xl text-muted-foreground/90 max-w-2xl mx-auto font-light">
            Configure your AI agent pipeline. We'll automatically detect, translate, clone voices, and lip-sync with cinematic precision.
          </p>
        </motion.div>

        {!isMockMode ? (
          <div className="mb-6 rounded-lg border border-green-500/50 bg-green-500/10 px-4 py-3 text-sm text-green-200">
            <strong>Real API</strong> – Backend connected. Real localized videos will be produced.
          </div>
        ) : (
          <div className="mb-6 rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            <strong>Demo mode</strong> – No real videos. Start the backend and refresh, or switch to Real API on the Architecture page.
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Video Upload */}
              <motion.div 
                initial={{ opacity: 0, x: -30 }} 
                animate={{ opacity: 1, x: 0 }} 
                transition={{ delay: 0.1, duration: 0.6 }}
              >
                <Card className="glass-strong border-white/5 relative overflow-hidden group">
                  <div className="absolute inset-0 bg-gradient-to-r from-primary/10 to-accent/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl tracking-wide">
                      <Video className="w-6 h-6 text-primary" />
                      Source Asset
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div
                      {...getRootProps()}
                      className={`border-2 border-dashed rounded-xl p-16 text-center cursor-pointer transition-all duration-300 ${
                        isDragActive
                          ? 'border-primary bg-primary/15 shadow-[0_0_30px_rgba(168,85,247,0.3)]'
                          : 'border-white/20 hover:border-primary/60 hover:bg-white/5'
                      }`}
                    >
                      <input {...getInputProps()} />
                      <Upload className={`w-14 h-14 mx-auto mb-6 transition-colors ${file ? 'text-primary' : 'text-muted-foreground'}`} />
                      {file ? (
                        <div className="space-y-4 pt-2">
                          <p className="font-semibold text-lg text-white drop-shadow-md">{file.name}</p>
                          <span className="inline-flex items-center px-3 py-1 rounded-full bg-white/10 text-xs text-white/80">
                            {(file.size / (1024 * 1024)).toFixed(2)} MB
                          </span>
                          {preview && (
                            <motion.video
                              initial={{ opacity: 0, scale: 0.95 }}
                              animate={{ opacity: 1, scale: 1 }}
                              src={preview}
                              controls
                              className="mt-6 max-w-full rounded-xl border border-white/10 shadow-2xl"
                            />
                          )}
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <p className="text-xl font-medium tracking-wide">
                            {isDragActive
                              ? 'Drop to Initiate'
                              : 'Drag & Drop Media'}
                          </p>
                          <p className="text-sm text-muted-foreground/80 font-light">
                            Supported: MP4, AVI, MOV, WebM (Max 2GB)
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Source Language */}
              <Card className="glass">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5" />
                    Source Language
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    {sourceLanguages.map((lang) => (
                      <motion.button
                        key={lang.code}
                        type="button"
                        onClick={() => setValue('sourceLanguage', lang.code)}
                        className={`p-3 rounded-lg border transition-all ${
                          selectedSourceLanguage === lang.code
                            ? 'border-primary bg-primary/20'
                            : 'border-muted-foreground/50 hover:border-primary/50'
                        }`}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                      >
                        <div className="text-lg mb-1">{lang.flag}</div>
                        <div className="text-sm font-medium">{lang.name}</div>
                      </motion.button>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground mt-3">
                    Auto-detect will infer the spoken language from the audio and display it during processing.
                  </p>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-6">
              {/* Language Selection */}
              <motion.div 
                initial={{ opacity: 0, x: 30 }} 
                animate={{ opacity: 1, x: 0 }} 
                transition={{ delay: 0.2, duration: 0.6 }}
              >
                <Card className="glass-strong border-white/5">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl tracking-wide">
                      <Languages className="w-6 h-6 text-accent" />
                      Target Audiences
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      {languages.map((lang) => (
                        <motion.button
                          key={lang.code}
                          type="button"
                          onClick={() => toggleLanguage(lang.code)}
                          className={`p-5 rounded-xl border backdrop-blur-sm transition-all duration-300 ${
                            selectedLanguages?.includes(lang.code)
                              ? 'border-accent bg-accent/20 shadow-[0_0_15px_rgba(236,72,153,0.2)] scale-[1.02]'
                              : 'border-white/10 bg-black/20 hover:border-accent/50 hover:bg-white/5'
                          }`}
                          whileHover={{ y: -2 }}
                          whileTap={{ scale: 0.96 }}
                        >
                          <div className="text-3xl mb-2 filter drop-shadow-md">{lang.flag}</div>
                          <div className="text-sm font-semibold tracking-wider text-white/90">{lang.name}</div>
                        </motion.button>
                      ))}
                    </div>
                    {errors.languages && (
                      <p className="text-red-400 text-sm mt-3 animate-pulse">
                        {errors.languages.message}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              {/* Voice Options */}
              <Card className="glass">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Volume2 className="w-5 h-5" />
                    Voice Options
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Gender</label>
                    <div className="flex gap-3">
                      {(['male', 'female', 'neutral'] as const).map((gender) => (
                        <Button
                          key={gender}
                          type="button"
                          variant={watch('gender') === gender ? 'primary' : 'outline'}
                          onClick={() => setValue('gender', gender)}
                        >
                          {gender.charAt(0).toUpperCase() + gender.slice(1)}
                        </Button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">Emotion</label>
                    <div className="flex gap-3 flex-wrap">
                      {(['neutral', 'happy', 'sad', 'excited'] as const).map((emotion) => (
                        <Button
                          key={emotion}
                          type="button"
                          variant={watch('emotion') === emotion ? 'primary' : 'outline'}
                          onClick={() => setValue('emotion', emotion)}
                        >
                          {emotion.charAt(0).toUpperCase() + emotion.slice(1)}
                        </Button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="cloned"
                      {...register('cloned')}
                      className="w-4 h-4"
                    />
                    <label htmlFor="cloned" className="text-sm">
                      Use cloned voice (requires voice sample)
                    </label>
                  </div>

                  <div className="rounded-lg border border-muted-foreground/40 p-4">
                    <div className="flex items-center gap-2 mb-2 text-sm font-medium">
                      <Mic className="w-4 h-4" />
                      Optional voice sample (WAV/MP3)
                    </div>
                    <input
                      type="file"
                      accept="audio/*"
                      onChange={(event) => {
                        const sample = event.target.files?.[0] || null
                        setVoiceSampleFile(sample)
                        setVoiceSample(sample)
                      }}
                      className="text-sm"
                    />
                    <p className="text-xs text-muted-foreground mt-2">
                      If empty, we will extract a sample from the uploaded video.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          <Card className="glass">
            <CardContent className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div>
                <p className="text-sm text-muted-foreground">Selection Summary</p>
                <p className="text-sm">
                  {selectedLanguages?.length || 0} target languages selected
                </p>
              </div>
              <div className="text-xs text-muted-foreground">
                Source: {selectedSourceLanguage || 'auto'} · Voice clone: {watch('cloned') ? 'on' : 'off'}
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <div className="flex justify-end">
            <Button
              type="submit"
              size="lg"
              disabled={!file || uploading || !selectedLanguages?.length}
              className="min-w-[200px]"
            >
              {uploading ? 'Uploading...' : 'Start Processing'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
