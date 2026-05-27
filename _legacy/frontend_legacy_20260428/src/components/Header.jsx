import { Link } from 'react-router-dom'
import '../styles/Header.css'

function Header() {
  return (
    <header className="header">
      <div className="header-container">
        <Link to="/" className="logo">
          <h1>VidioLingua</h1>
        </Link>
        <nav className="nav">
          <Link to="/" className="nav-link">Home</Link>
          <Link to="/demo" className="nav-link">Demo</Link>
        </nav>
      </div>
    </header>
  )
}

export default Header

