import '../styles/Button.css'

function Button({ children, onClick, variant = 'primary', disabled = false, type = 'button', className = '' }) {
  // Merge default classes with custom className
  const combinedClassName = className 
    ? `btn btn-${variant} ${className}`.trim()
    : `btn btn-${variant}`
  
  return (
    <button
      className={combinedClassName}
      onClick={onClick}
      disabled={disabled}
      type={type}
    >
      {children}
    </button>
  )
}

export default Button

