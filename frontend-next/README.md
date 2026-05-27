# VidioLingua - Advanced Frontend

An extremely advanced, highly animated, premium frontend web application for VidioLingua: AI-Powered Multilingual Video Localization System.

## 🚀 Tech Stack

- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS** (with custom design system)
- **Framer Motion** (micro & macro animations)
- **GSAP** (scroll-based storytelling & timelines)
- **Zustand** (global pipeline state)
- **Axios** (API abstraction)
- **React Hook Form + Zod** (advanced validation)
- **ShadCN UI** (accessible base components)

## ✨ Features

### 1. Landing Page
- Animated hero headline with GSAP
- Scroll-triggered animations
- Problem → Solution → Impact storytelling
- Market size & cost comparison (animated counters)
- Gradient mesh backgrounds
- Glassmorphism effects

### 2. Video Upload & Configuration
- Drag & drop video upload with preview
- Multi-language selector (100+ languages UI)
- Voice options (gender, emotion, cloned voice)
- Real-time validation with Zod
- Animated submit states

### 3. AI Pipeline Visualizer (MOST CRITICAL)
Visually represents each stage:
- **ASR (Whisper)**: Waveform → text animation
- **MT (MarianMT)**: Text morphing visualization
- **TTS (Tacotron)**: Waveform synthesis animation
- **Lip-sync (Wav2Lip)**: Facial sync overlay

Each stage shows:
- Animated status indicators
- Real-time metrics (WER, BLEU, MOS, LSE-C)
- Progress bars
- Clear explanations for judges

### 4. Processing & Progress
- Job-based progress tracker
- Parallel language processing UI
- Polling-based progress updates (WebSocket-ready)
- GPU usage & time estimation visuals
- Graceful error states with retry animations

### 5. Result & Preview
- Side-by-side original vs localized video
- Audio track toggle
- Confidence & quality indicators
- Download localized videos
- Quality metrics dashboard

### 6. System Architecture Page
- Animated microservices diagram
- ASR / MT / TTS / Sync as independent services
- Kubernetes & GPU scaling visualization
- Mock vs real API toggle explanation
- Performance metrics

## 🎨 Design Language

- **Dark-mode default** (cinematic aesthetic)
- **Gradient meshes** for backgrounds
- **Glassmorphism** throughout
- **Timeline-based animations**
- **Motion communicates intelligence**
- **Subtle sound-wave & waveform visuals**
- **Accessibility-first** (ARIA, keyboard nav)

## 📁 Project Structure

```
frontend-next/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx           # Landing page
│   │   ├── upload/            # Upload & configuration
│   │   ├── pipeline/          # Pipeline visualizer
│   │   ├── results/           # Results & preview
│   │   └── architecture/      # System architecture
│   ├── components/
│   │   ├── pipeline/          # Pipeline visualization components
│   │   ├── motion/            # Animation components
│   │   └── ui/                # ShadCN UI components
│   ├── store/                 # Zustand state management
│   ├── services/             # API service layer
│   ├── hooks/                # Custom React hooks
│   ├── lib/                  # Utilities
│   └── types/                # TypeScript types
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

## 🛠️ Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend-next
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Build for Production

```bash
npm run build
npm start
```

## 🔌 Backend Integration

The frontend supports both **mock mode** (default) and **real API mode**.

### Mock Mode (Default)
- Automatically simulates the entire pipeline
- Perfect for demos and presentations
- No backend required

### Real API Mode
Set the API URL in `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### API Endpoints Expected

- `POST /api/upload` - Upload video and start processing
- `GET /api/job-status/:jobId` - Get job status
- `GET /api/result/:jobId` - Get processing result
- `GET /api/health` - Health check

## 🎯 Key Features for Judges

1. **Clear Pipeline Visualization**: Every stage is explained with metrics
2. **Real-time Progress**: See exactly what's happening at each step
3. **Quality Metrics**: WER, BLEU, MOS, LSE-C scores displayed
4. **Architecture Explanation**: Understand the microservices design
5. **Mock vs Real Toggle**: See how it works with/without backend

## 🎨 Customization

### Colors & Theme
Edit `src/app/globals.css` for color scheme changes.

### Animations
- GSAP animations: `src/app/page.tsx` (landing)
- Framer Motion: Used throughout components
- Custom animations: `tailwind.config.ts`

## 📝 Notes

- The app defaults to **mock mode** for easy demonstration
- All animations are optimized for performance
- Responsive design works on all screen sizes
- Dark mode is the default (can be extended to support light mode)

## 🚀 Deployment

### Vercel (Recommended)
```bash
npm install -g vercel
vercel
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## 📄 License

Part of the VidioLingua Techgium PoC project.
