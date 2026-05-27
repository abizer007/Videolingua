# 🚀 How to Preview VidioLingua Frontend

## Quick Start (3 Steps)

### Step 1: Navigate to Frontend Directory
```bash
cd frontend-next
```

### Step 2: Install Dependencies
```bash
npm install
```

This will install all required packages:
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Framer Motion
- GSAP
- Zustand
- And all other dependencies

### Step 3: Start Development Server
```bash
npm run dev
```

The server will start at **http://localhost:3000**

---

## 🎯 What You'll See

### 1. Landing Page (`/`)
- **Animated Hero**: "Translate Any Video. Speak Every Language."
- **GSAP Scroll Animations**: Smooth scroll-triggered animations
- **Problem Section**: Language barriers, cost, time issues
- **Solution Section**: 95% cost reduction, 99% time savings
- **Market Stats**: Animated counters showing market opportunity
- **CTA Button**: "Localize a Video" → Takes you to upload

### 2. Upload Page (`/upload`)
- **Drag & Drop**: Upload video files (MP4, AVI, MOV, WebM)
- **Video Preview**: See your uploaded video before processing
- **Language Selection**: Choose from 8+ languages (Hindi, Spanish, French, etc.)
- **Voice Options**: 
  - Gender: Male, Female, Neutral
  - Emotion: Neutral, Happy, Sad, Excited
  - Cloned Voice: Toggle option
- **Start Processing**: Button to begin the pipeline

### 3. Pipeline Page (`/pipeline`) ⭐ **MOST IMPORTANT**
- **Overall Progress Bar**: Shows 0-100% completion
- **AI Pipeline Visualizer**: 
  - **ASR Stage**: Shows WER (Word Error Rate) and Confidence
  - **Translation Stage**: Shows BLEU Score and Languages
  - **TTS Stage**: Shows MOS Score and Quality rating
  - **Lip-Sync Stage**: Shows LSE-C Score and Sync Quality
- **Animated Waveform**: Visual audio representation
- **Real-time Updates**: Progress updates every second (mock mode)
- **Stage Indicators**: Icons show active, complete, or error states

### 4. Results Page (`/results`)
- **Metrics Summary**: Total time, languages processed, success rate
- **Side-by-Side Comparison**: Original vs Localized videos
- **Quality Indicators**: ASR Accuracy, Translation Quality, Voice Naturalness, Lip Sync
- **Download Buttons**: Download each localized video
- **Preview Buttons**: Preview each localized version

### 5. Architecture Page (`/architecture`)
- **Microservices Diagram**: Animated service cards
- **Pipeline Flow**: ASR → Translation → TTS → Lip-Sync
- **Mock/Real Toggle**: Switch between mock and real API mode
- **Infrastructure Details**: Kubernetes deployment info
- **Performance Metrics**: Throughput, GPU utilization, latency

---

## 🎨 Key Features to Demo

### For Judges - What to Highlight:

1. **Pipeline Visualization** (`/pipeline`)
   - Show how each stage is clearly explained
   - Point out the real-time metrics (WER, BLEU, MOS, LSE-C)
   - Demonstrate the animated progress

2. **Architecture Explanation** (`/architecture`)
   - Explain the microservices design
   - Show the mock/real API toggle
   - Discuss scalability and fault tolerance

3. **User Experience** (`/upload` → `/pipeline` → `/results`)
   - Show the complete flow
   - Highlight the drag & drop upload
   - Demonstrate language selection
   - Show the results comparison

4. **Design Quality**
   - Dark mode cinematic aesthetic
   - Glassmorphism effects
   - Smooth animations
   - Responsive design

---

## 🔧 Troubleshooting

### Port Already in Use
If port 3000 is busy, Next.js will automatically use the next available port (3001, 3002, etc.)

### Module Not Found Errors
```bash
# Clear cache and reinstall
rm -rf node_modules .next
npm install
```

### TypeScript Errors
Make sure you're using Node.js 18+:
```bash
node --version
```

### Build Errors
```bash
# Clean build
rm -rf .next
npm run build
```

---

## 🎬 Demo Flow Recommendation

1. **Start at Landing** (`/`)
   - Let animations play
   - Scroll to see problem/solution sections
   - Click "Localize a Video"

2. **Upload Page** (`/upload`)
   - Upload a sample video (any MP4 file)
   - Select 2-3 languages (Hindi, Spanish, French)
   - Choose voice options
   - Click "Start Processing"

3. **Pipeline Page** (`/pipeline`) ⭐
   - **THIS IS THE KEY PAGE FOR JUDGES**
   - Watch the pipeline progress through stages
   - Point out each metric as it appears
   - Explain what each stage does
   - Show the waveform animation

4. **Results Page** (`/results`)
   - Show the quality metrics
   - Compare original vs localized
   - Highlight the confidence scores

5. **Architecture Page** (`/architecture`)
   - Explain the microservices design
   - Toggle between mock/real mode
   - Show performance metrics

---

## 📱 Responsive Testing

The app is fully responsive. Test on:
- Desktop (1920x1080)
- Tablet (768x1024)
- Mobile (375x667)

---

## 🎯 Mock Mode vs Real API

### Mock Mode (Default)
- No backend required
- Simulates entire pipeline
- Perfect for demos
- Progress updates automatically

### Real API Mode (With real backend)

1. **Start the backend** from the project root (not inside `frontend-next`):
   ```bash
   pip install -r requirements.txt
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Ensure **ffmpeg** is on your PATH (required for TTS and lip-sync).

2. **Point the frontend at the API** – create `frontend-next/.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Turn off mock mode**: Open the **Architecture** page and switch **API Mode** to **Real API**.

4. **Run the full flow**: Upload a short video on the Upload page, select languages (e.g. Hindi, Spanish, French), and start processing. The Pipeline page will poll the backend; when complete, the Results page will show the original and localized videos. Result videos are served by the backend; you can preview and download them from the Results page.

---

## 🚀 Production Build

To build for production:
```bash
npm run build
npm start
```

This creates an optimized production build in `.next/` folder.

---

## 💡 Pro Tips

1. **First Load**: The first `npm install` might take 2-3 minutes. Be patient!

2. **Hot Reload**: Changes to code automatically refresh the browser

3. **Console**: Open browser DevTools to see any warnings (should be minimal)

4. **Network Tab**: Check API calls in Network tab (mock mode won't make real calls)

5. **Performance**: The app is optimized, but first load might be slower due to animations

---

## ✅ Checklist Before Demo

- [ ] `npm install` completed successfully
- [ ] `npm run dev` starts without errors
- [ ] Landing page loads with animations
- [ ] Can upload a video file
- [ ] Pipeline page shows progress
- [ ] Results page displays correctly
- [ ] Architecture page loads
- [ ] All navigation links work
- [ ] Responsive on mobile/tablet

---

## 🎉 You're Ready!

The frontend is complete and ready for the Techgium competition. The mock mode ensures you can demo everything without a backend, making it perfect for presentations.

**Good luck with your PoC! 🚀**
