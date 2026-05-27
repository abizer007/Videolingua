import { Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import Button from '../components/Button'
import '../styles/Landing.css'

function Landing() {
  return (
    <div className="landing">
      <Header />
      
      <main className="landing-main">
        {/* Hero Section */}
        <section className="hero">
          <div className="hero-content">
            <h1 className="hero-title">Break Language Barriers with AI-Powered Video Translation</h1>
            <p className="hero-subtitle">
              VidioLingua transforms videos from one language to multiple languages using advanced 
              AI technology. Experience seamless video dubbing with automatic speech recognition, 
              translation, text-to-speech, and lip synchronization.
            </p>
            <div className="hero-buttons">
              <Link to="/demo">
                <Button variant="primary">Try Demo</Button>
              </Link>
            </div>
          </div>
        </section>

        {/* Problem Section */}
        <section className="problem-section">
          <div className="container">
            <h2>The Problem</h2>
            <div className="problem-content">
              <div className="problem-item">
                <h3>Language Barriers</h3>
                <p>Content creators struggle to reach global audiences due to language limitations.</p>
              </div>
              <div className="problem-item">
                <h3>Expensive Dubbing</h3>
                <p>Traditional video dubbing requires professional voice actors and extensive post-production.</p>
              </div>
              <div className="problem-item">
                <h3>Time-Consuming</h3>
                <p>Manual translation and dubbing processes take weeks or months to complete.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Solution Section */}
        <section className="solution-section">
          <div className="container">
            <h2>Our Solution</h2>
            <p className="solution-intro">
              VidioLingua automates the entire video translation pipeline, converting videos 
              from English to multiple target languages (Hindi, Spanish, French) in minutes 
              instead of weeks.
            </p>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="how-it-works">
          <div className="container">
            <h2>How It Works</h2>
            <div className="steps">
              <div className="step">
                <div className="step-number">1</div>
                <h3>Automatic Speech Recognition (ASR)</h3>
                <p>Extract spoken text from your video with precise timestamps and transcription accuracy.</p>
              </div>
              <div className="step">
                <div className="step-number">2</div>
                <h3>Machine Translation</h3>
                <p>Translate the transcribed text into target languages while preserving timing information.</p>
              </div>
              <div className="step">
                <div className="step-number">3</div>
                <h3>Text-to-Speech & Lip Sync</h3>
                <p>Generate natural-sounding voice in target languages and synchronize with video lip movements.</p>
              </div>
            </div>
            <div className="cta-section">
              <Link to="/demo">
                <Button variant="primary" className="cta-button">Start Your Demo</Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}

export default Landing

