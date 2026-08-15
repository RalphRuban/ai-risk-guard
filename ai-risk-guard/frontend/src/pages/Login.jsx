import { useState, useEffect } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { getUser } from '../api/client'

export default function Login() {
  const [searchParams] = useSearchParams()
  const noInstallations = searchParams.get('error') === 'no_installations'
  const installUrl = searchParams.get('install_url')
  const [checking, setChecking] = useState(true)
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    getUser().then((data) => {
      if (data.authenticated) {
        setLoggedIn(true)
      }
    }).catch(() => {}).finally(() => setChecking(false))
  }, [])

  if (checking) return null

  if (loggedIn && !noInstallations) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="enterprise-card p-8">
          {noInstallations && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 rounded-lg"
              style={{ backgroundColor: 'rgba(250, 204, 21, 0.08)', border: '1px solid rgba(250, 204, 21, 0.4)' }}
              role="alert"
            >
              <p className="font-semibold text-sm flex items-center gap-2">
                <span>⚠️</span> No app installed in any repository
              </p>
              <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>
                The AI Risk Guard app isn't installed on any of your repositories, so there's nothing to scan yet.
                Install the app and try again.
              </p>
              {installUrl && (
                <a
                  href={installUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 btn-accent"
                >
                  Install the app ↗
                </a>
              )}
            </motion.div>
          )}

          <div className="text-center mb-8">
            <div className="inline-flex mb-4">
              <svg
                viewBox="0 0 24 24"
                className="w-12 h-12"
                fill="none"
                stroke="var(--accent-bright)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                <path d="M9 12l2 2 4-4"/>
              </svg>
            </div>
            <h2 className="k-title inline-block">Welcome</h2>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              Sign in to AI Risk Guard
            </p>
          </div>

          <a
            href="/auth/login"
            className="btn-primary w-full"
          >
            <svg className="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            Sign in with GitHub
          </a>

          <div className="text-center mt-6">
            <Link to="/" className="text-sm hover:underline" style={{ color: 'var(--text-muted)' }}>
              &larr; Back to Home
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  )
}