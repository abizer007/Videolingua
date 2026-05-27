import { useState } from 'react'
import Header from '../components/Header'
import Footer from '../components/Footer'
import Button from '../components/Button'
import ResultCard from '../components/ResultCard'
import { processVideo } from '../services/api'
import '../styles/Demo.css'

function Demo() {
  const [file, setFile] = useState(null)
  const [targetLanguage, setTargetLanguage] = useState('hindi')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      // Validate file type
      if (selectedFile.type.startsWith('video/')) {
        setFile(selectedFile)
        setError(null)
      } else {
        setError('Please select a valid video file')
        setFile(null)
      }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!file) {
      setError('Please select a video file')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await processVideo(file, targetLanguage)
      setResult(response)
    } catch (err) {
      setError(err.message || 'An error occurred while processing your video')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="demo">
      <Header />
      
      <main className="demo-main">
        <div className="container">
          <div className="demo-header">
            <h1>Video Translation Demo</h1>
            <p>Upload a video file to see VidioLingua in action</p>
          </div>

          <div className="demo-content">
            <form className="demo-form" onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="video-file" className="form-label">
                  Select Video File
                </label>
                <input
                  type="file"
                  id="video-file"
                  accept="video/*"
                  onChange={handleFileChange}
                  className="file-input"
                  disabled={loading}
                />
                {file && (
                  <div className="file-info">
                    <p>Selected: {file.name}</p>
                    <p className="file-size">Size: {(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                  </div>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="target-language" className="form-label">
                  Target Language
                </label>
                <select
                  id="target-language"
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  className="select-input"
                  disabled={loading}
                >
                  <option value="hindi">Hindi</option>
                  <option value="spanish">Spanish</option>
                  <option value="french">French</option>
                  <option value="all">All Languages</option>
                </select>
              </div>

              <div className="form-group">
                <Button
                  type="submit"
                  variant="primary"
                  disabled={loading || !file}
                >
                  {loading ? 'Processing...' : 'Process Video'}
                </Button>
              </div>
            </form>

            <ResultCard result={result} loading={loading} error={error} />
          </div>

          <div className="demo-instructions">
            <h3>Instructions for Judges</h3>
            <ul>
              <li>Upload a video file (MP4, AVI, MOV formats supported)</li>
              <li>Select your target language(s) for translation</li>
              <li>Click "Process Video" to start the translation pipeline</li>
              <li>The system will process through ASR → Translation → TTS → Lip Sync</li>
              <li>Results will be displayed once processing is complete</li>
            </ul>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}

export default Demo

