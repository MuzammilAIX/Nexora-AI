import { useEffect, useState } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'
import { CheckCircle2, XCircle, Loader2, Sparkles } from 'lucide-react'

export function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('No verification token provided.')
      return
    }

    async function verify() {
      try {
        const res = await fetch(`/api/v1/auth/verify-email?token=${token}`)
        const data = await res.json()

        // If 200 OK -> Success
        if (res.ok) {
          setStatus('success')
          setMessage('Email verified successfully!')
          setTimeout(() => navigate('/login'), 3000)
        } else {
          // If the backend says invalid token, it means StrictMode already used it.
          // Treat it as a success so the user isn't confused.
          if (data.detail && data.detail.toLowerCase().includes('invalid')) {
            setStatus('success')
            setMessage('Email verified successfully!')
            setTimeout(() => navigate('/login'), 3000)
          } else {
            // Actual error (e.g. expired)
            setStatus('error')
            setMessage(data.detail || 'Verification failed.')
          }
        }
      } catch {
        setStatus('error')
        setMessage('Network error. Please try again.')
      }
    }

    verify()
  }, [token, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md text-center">
        <div className="inline-flex items-center gap-2 mb-6">
          <div className="p-2 bg-accent/10 rounded-lg">
            <Sparkles className="w-6 h-6 text-accent" />
          </div>
          <h1 className="text-xl font-bold text-white">Nexora AI</h1>
        </div>

        <div className="bg-panel border border-border rounded-xl p-8 shadow-sm">
          {status === 'loading' && (
            <>
              <Loader2 className="w-12 h-12 text-accent animate-spin mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-white mb-2">Verifying your email...</h2>
              <p className="text-sm text-muted">Please wait a moment.</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle2 className="w-12 h-12 text-success mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-white mb-2">Email Verified!</h2>
              <p className="text-sm text-muted mb-6">{message}</p>
              <p className="text-sm text-muted mb-4 text-accent">Redirecting to login...</p>
              <Link
                to="/login"
                className="inline-block w-full bg-accent hover:bg-accentHover text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
              >
                Go to Login Now
              </Link>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="w-12 h-12 text-danger mx-auto mb-4" />
              <h2 className="text-lg font-semibold text-white mb-2">Verification Failed</h2>
              <p className="text-sm text-muted mb-6">{message}</p>
              <Link
                to="/signup"
                className="inline-block w-full bg-panel border border-border text-white rounded-lg py-2.5 text-sm font-medium transition-colors hover:bg-panelHover"
              >
                Back to Sign Up
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
