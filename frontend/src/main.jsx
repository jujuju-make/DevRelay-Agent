import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import LoginPage from './pages/LoginPage'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import './index.css'

function Root() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-neutral-950">
        <div className="flex gap-1.5">
          <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" />
          <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" style={{ animationDelay: '0.2s' }} />
          <span className="w-2 h-2 rounded-full bg-neutral-500 animate-pulse-dot" style={{ animationDelay: '0.4s' }} />
        </div>
      </div>
    )
  }

  return isAuthenticated ? <App /> : <LoginPage />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <Root />
    </AuthProvider>
  </React.StrictMode>
)
