/**
 * API Service for VidioLingua Backend Integration
 * 
 * This service handles all API calls to the backend.
 * For the PoC, it includes mock functionality for demonstration.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Process a video file through the translation pipeline
 * 
 * @param {File} file - The video file to process
 * @param {string} targetLanguage - Target language (hindi, spanish, french, or all)
 * @returns {Promise<Object>} - API response with status, result, and confidence
 */
export async function processVideo(file, targetLanguage) {
  // Create FormData to send file
  const formData = new FormData()
  formData.append('video', file)
  formData.append('target_language', targetLanguage)

  try {
    const response = await fetch(`${API_BASE_URL}/api/process`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    // If API is not available, use mock response for PoC demonstration
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      console.warn('Backend API not available, using mock response for PoC')
      return mockProcessVideo(file, targetLanguage)
    }
    throw error
  }
}

/**
 * Mock function for PoC demonstration when backend is not available
 * 
 * @param {File} file - The video file
 * @param {string} targetLanguage - Target language
 * @returns {Promise<Object>} - Mock response
 */
function mockProcessVideo(file, targetLanguage) {
  return new Promise((resolve) => {
    // Simulate API processing time
    setTimeout(() => {
      const languages = targetLanguage === 'all' 
        ? ['Hindi', 'Spanish', 'French']
        : [targetLanguage.charAt(0).toUpperCase() + targetLanguage.slice(1)]

      resolve({
        status: 'success',
        result: `Video successfully translated to ${languages.join(', ')}`,
        confidence: 0.87,
        languages: languages,
        message: 'Video processing completed. Check demo_outputs folder for translated videos.'
      })
    }, 2000) // 2 second delay to simulate processing
  })
}

/**
 * Health check endpoint to verify backend connectivity
 * 
 * @returns {Promise<Object>} - Health status
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`)
    if (!response.ok) {
      throw new Error('Health check failed')
    }
    return await response.json()
  } catch (error) {
    console.warn('Backend health check failed:', error)
    return { status: 'unavailable', message: 'Backend not connected' }
  }
}

