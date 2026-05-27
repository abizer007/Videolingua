import '../styles/ResultCard.css'

function ResultCard({ result, loading, error }) {
  if (loading) {
    return (
      <div className="result-card loading">
        <div className="spinner"></div>
        <p>Processing your video...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="result-card error">
        <h3>Error</h3>
        <p>{error}</p>
      </div>
    )
  }

  if (!result) {
    return null
  }

  return (
    <div className="result-card success">
      <h3>Processing Complete!</h3>
      <div className="result-content">
        <div className="result-item">
          <span className="result-label">Status:</span>
          <span className="result-value">{result.status}</span>
        </div>
        {result.result && (
          <div className="result-item">
            <span className="result-label">Result:</span>
            <span className="result-value">{result.result}</span>
          </div>
        )}
        {result.confidence !== undefined && (
          <div className="result-item">
            <span className="result-label">Confidence:</span>
            <span className="result-value">{(result.confidence * 100).toFixed(1)}%</span>
          </div>
        )}
        {result.languages && (
          <div className="result-item">
            <span className="result-label">Languages:</span>
            <span className="result-value">{result.languages.join(', ')}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default ResultCard

