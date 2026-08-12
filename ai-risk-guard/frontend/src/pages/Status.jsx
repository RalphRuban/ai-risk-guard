import { useState, useEffect, useCallback } from 'react'
import PageHeader from '../components/PageHeader'
import { motion } from 'framer-motion'
import { getDbHealth, getGeminiHealth, getSandboxHealth } from '../api/client'

function StatusRow({ label, value, ok, hint }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center justify-between p-4 rounded-lg"
      style={{ backgroundColor: 'var(--bg)', border: '1px solid var(--border)' }}
    >
      <div>
        <p className="text-sm font-semibold">{label}</p>
        {hint && <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{hint}</p>}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-bold capitalize" style={{ color: ok ? '#3B82F6' : '#F43F5E' }}>{value}</span>
        <span className={`w-2.5 h-2.5 rounded-full ${ok ? 'bg-blue-400' : 'bg-red-500'}`} />
      </div>
    </motion.div>
  )
}

export default function Status() {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [timeAgo, setTimeAgo] = useState('')

  const fetchHealth = useCallback(async () => {
    try {
      const [db, gemini, sandbox] = await Promise.all([
        getDbHealth(),
        getGeminiHealth(),
        getSandboxHealth(),
      ])
      setHealth({ db, gemini, sandbox })
      setLastUpdated(new Date())
    } catch {
      setHealth(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 30000)
    return () => clearInterval(interval)
  }, [fetchHealth])

  useEffect(() => {
    if (!lastUpdated) return
    const tick = () => {
      const seconds = Math.round((new Date() - lastUpdated) / 1000)
      setTimeAgo(seconds < 5 ? 'just now' : seconds < 60 ? `${seconds}s ago` : `${Math.round(seconds / 60)}m ago`)
    }
    tick()
    const timer = setInterval(tick, 5000)
    return () => clearInterval(timer)
  }, [lastUpdated])

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-48 bg-gray-700 rounded mb-1 animate-pulse" />
        <div className="h-4 w-64 bg-gray-700 rounded mb-8 animate-pulse" />
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="enterprise-card p-4 animate-pulse"><div className="h-4 w-32 bg-gray-700 rounded" /></div>)}
        </div>
      </div>
    )
  }

  const allOk = health && health.db?.status === 'ok' && health.gemini?.status === 'online' && health.sandbox?.mode === 'docker'

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader eyebrow="Health" title="System Status"
        subtitle={<span>Live health of the AI Risk Guard platform {lastUpdated && <span className="ml-2 text-xs opacity-60">updated {timeAgo}</span>}</span>}>
        <span className="flex items-center gap-1.5 text-sm font-semibold" style={{ color: allOk ? '#3B82F6' : '#F43F5E' }}>
          <span className={`w-2.5 h-2.5 rounded-full ${allOk ? 'bg-blue-400' : 'bg-red-500'}`} />
          {allOk ? 'All systems operational' : 'Degraded'}
        </span>
        <button onClick={fetchHealth} className="btn-secondary">↻ Refresh</button>
      </PageHeader>

      <div className="space-y-3">
        <StatusRow
          label="Database"
          value={health?.db?.status || 'unknown'}
          ok={health?.db?.status === 'ok'}
          hint="SQLite storage writable"
        />
        <StatusRow
          label="Gemini AI"
          value={health?.gemini?.status || 'offline'}
          ok={health?.gemini?.status === 'online'}
          hint="Patch generation API configured"
        />
        <StatusRow
          label="Sandbox"
          value={health?.sandbox?.mode || 'unknown'}
          ok={health?.sandbox?.mode === 'docker'}
          hint={health?.sandbox?.mode === 'docker'
            ? 'Isolated Docker execution available'
            : 'Docker unavailable — using hardened local fallback'}
        />
        {health?.sandbox && (
          <div className="p-4 rounded-lg text-xs" style={{ backgroundColor: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            docker_available={String(health.sandbox.docker_available)} · image_ready={String(health.sandbox.image_ready)}
          </div>
        )}
      </div>

      {!allOk && (
        <p className="mt-6 text-sm" style={{ color: 'var(--text-muted)' }}>
          Degraded services may still operate with reduced capability (e.g. local sandbox fallback, no LLM patch generation).
        </p>
      )}
    </div>
  )
}
