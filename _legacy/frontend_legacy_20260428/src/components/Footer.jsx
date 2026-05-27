import '../styles/Footer.css'

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-content">
          <div className="footer-section">
            <h3>VidioLingua</h3>
            <p>AI-Powered Video Translation Platform</p>
          </div>
          <div className="footer-section">
            <h4>Team</h4>
            <p>Techgium PoC Team</p>
          </div>
          <div className="footer-section">
            <h4>Technology</h4>
            <p>ASR • Translation • TTS • Lip Sync</p>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2024 VidioLingua. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}

export default Footer

