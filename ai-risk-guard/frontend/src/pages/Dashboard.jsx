import { useState, useEffect, useCallback, useMemo } from 'react'
import PageHeader from '../components/PageHeader'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import useCountUp from '../hooks/useCountUp'
import { getDashboard, getUser, getDbHealth, getGeminiHealth, getSandboxHealth } from '../api/client'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from 'chart.js'
import { Doughnut, Bar } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

function StatCardSkeleton() {
  return (
    <div className="enterprise-card p-5 animate-pulse">
      <div className="w-10 h-10 rounded-xl bg-gray-700 mb-3" />
      <div className="h-3 w-20 bg-gray-700 rounded mb-2" />
      <div className="h-6 w-16 bg-gray-700 rounded" />
    </div>
  )
}

function ChartSkeleton({ className = '' }) {
  return (
    <div className={`enterprise-card p-6 ${className}`}>
      <div className="h-3 w-32 bg-gray-700 rounded mb-6" />
      <div className="h-48 bg-gray-700/50 rounded" />
    </div>
  )
}

function StatCard({ icon, label, value, color, prefix = '', suffix = '', zone = '' }) {
  const count = useCountUp(value)
  return (
    <motion.div className={`enterprise-card p-5 ${zone}`}>
      <div className={`stat-icon mb-3 ${color}`}>{icon}</div>
      <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>
        {label}
      </p>
      <h3 className={`stat-heading ${color}`}>
        {prefix}{typeof value === 'number' ? count.toLocaleString() : (value ?? 0)}{suffix}
      </h3>
    </motion.div>
  )
}

const defaultAvatar = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2394a3b8'%3E%3Cpath d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E"

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [timeAgo, setTimeAgo] = useState('')
  const [user, setUser] = useState(null)
  const [installations, setInstallations] = useState(-1)
  const [installUrl, setInstallUrl] = useState('')
  const [installBannerDismissed, setInstallBannerDismissed] = useState(false)
  const [health, setHealth] = useState(null)

  const fetchHealth = useCallback(() => {
    Promise.allSettled([getDbHealth(), getGeminiHealth(), getSandboxHealth()])
      .then(([db, gemini, sandbox]) => {
        setHealth({
          db: db.status === 'fulfilled' ? db.value : null,
          gemini: gemini.status === 'fulfilled' ? gemini.value : null,
          sandbox: sandbox.status === 'fulfilled' ? sandbox.value : null,
        })
      })
      .catch(() => {})
  }, [])

  const fetchData = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true)
    try {
      const result = await getDashboard()
      setData(result)
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err?.response?.data?.message || 'Failed to load dashboard data')
    } finally {
      if (showLoader) setLoading(false)
    }
  }, [])

  useEffect(() => {
    getUser().then((data) => {
      if (data.authenticated) {
        setUser(data.user)
        setInstallations(typeof data.installations === 'number' ? data.installations : -1)
        setInstallUrl(data.install_url || '')
        fetchData(true)
        fetchHealth()
      } else {
        setLoading(false)
        setError('Please log in to view the dashboard')
      }
    }).catch(() => {
      setLoading(false)
      setError('Please log in to view the dashboard')
    })
  }, [fetchData, fetchHealth])

  useEffect(() => {
    if (!user) return
    const interval = setInterval(() => { fetchData(false); fetchHealth() }, 30000)
    return () => clearInterval(interval)
  }, [user, fetchData, fetchHealth])

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

  const totalPrs = data?.total_prs ?? 0
  const totalVulns = data?.total_vulnerabilities ?? 0
  const riskLevels = data?.risk_levels || {}
  const avgRisk = data?.avg_risk_score ?? 0
  const remediationRate = data?.remediation_rate ?? 0
  const cacheHitRate = data?.cache_hit_rate ?? 0
  const trends = data?.trends || []
  const attention = data?.attention || []
  const week = data?.week_summary || {}

  const riskChartData = useMemo(() => ({
    labels: ['Low', 'Medium', 'High'],
    datasets: [{
      data: [riskLevels.LOW || 0, riskLevels.MEDIUM || 0, riskLevels.HIGH || 0],
      backgroundColor: [
        'rgba(168, 176, 188, 0.85)',
        'rgba(59, 130, 246, 0.85)',
        'rgba(244, 63, 94, 0.85)',
      ],
      borderColor: ['rgba(168,176,188,1)', 'rgba(59,130,246,1)', 'rgba(244,63,94,1)'],
      borderWidth: 1,
    }],
  }), [riskLevels])

  const trendLabels = useMemo(() =>
    [...trends].reverse().map(t => {
      const d = new Date(t.day + 'T00:00:00')
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }), [trends])
  const trendCounts = useMemo(() => [...trends].reverse().map(t => t.count), [trends])
  const trendChartData = useMemo(() => ({
    labels: trendLabels.length > 0 ? trendLabels : ['No data'],
    datasets: [{
      label: 'PRs',
      data: trendCounts.length > 0 ? trendCounts : [0],
      backgroundColor: 'rgba(21, 94, 239, 0.85)',
      borderColor: 'rgba(59, 130, 246, 1)',
      borderWidth: 1,
      borderRadius: 0,
    }],
  }), [trendLabels, trendCounts])

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-48 bg-gray-700 rounded mb-1 animate-pulse" />
        <div className="h-4 w-64 bg-gray-700 rounded mb-8 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
          {[1,2,3,4].map(i => <StatCardSkeleton key={i} />)}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <ChartSkeleton />
          <ChartSkeleton className="xl:col-span-2" />
        </div>
        <div className="enterprise-card p-6 mt-6 animate-pulse">
          <div className="h-3 w-36 bg-gray-700 rounded mb-6" />
          {[1,2,3].map(i => <div key={i} className="h-12 bg-gray-700/50 rounded mb-3" />)}
        </div>
      </div>
    )
  }

  if (error && !data) {
    const isAuthError = error.includes('log in')
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="enterprise-card p-8 text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold mb-2">{isAuthError ? 'Authentication Required' : 'Failed to Load Dashboard'}</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{error}</p>
          {isAuthError ? (
            <a href="/login" className="inline-block px-6 py-2.5 btn-primary">Log in</a>
          ) : (
            <button onClick={() => fetchData(true)} className="px-6 py-2.5 btn-primary">Retry</button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {error && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-3 rounded-lg text-sm font-medium"
          style={{ backgroundColor: 'rgba(225, 29, 72, 0.1)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
          {error.includes('log in') ? (
            <span>{error} — <a href="/login" className="underline font-semibold">Log in</a></span>
          ) : (
            <span>{error} — <button onClick={() => fetchData(false)} className="underline font-semibold">Retry</button></span>
          )}
        </motion.div>
      )}

      {/* Header */}
      <PageHeader
        eyebrow="Command Center"
        title="Security Command Center"
        subtitle={
          <span>
            Executive summary of active risk across your repositories
            {lastUpdated && <span className="ml-2 text-xs opacity-60">updated {timeAgo}</span>}
          </span>
        }
      >
        <span className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span className={`w-2 h-2 rounded-full ${error ? 'bg-red-500' : 'bg-blue-400'}`} />
          {error ? 'Error' : 'Connected'}
        </span>
        <button onClick={() => fetchData(true)}
          className="btn-outline">
          ↻ Refresh
        </button>
      </PageHeader>

      {/* User Greeting */}
      {user && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="enterprise-card p-5 mb-6 flex items-center gap-4">
          <img src={user.avatar_url || defaultAvatar} alt={user.login} className="w-12 h-12 rounded-full"
            onError={(e) => { if (e.target.src !== defaultAvatar) e.target.src = defaultAvatar }} />
          <div>
            <p className="text-lg font-bold">Welcome, {user.name}</p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>@{user.login} — your security overview</p>
          </div>
        </motion.div>
      )}

      {/* System Health */}
      {health && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="enterprise-card p-4 flex items-center gap-3">
            <span className={`w-2.5 h-2.5 rounded-full ${health.db?.status === 'ok' ? 'bg-blue-400' : 'bg-red-500'}`} />
            <div>
              <p className="stat-label" style={{ color: 'var(--text-muted)' }}>Database</p>
              <p className="text-sm font-semibold capitalize">{health.db?.status || 'unknown'}</p>
            </div>
          </div>
          <div className="enterprise-card p-4 flex items-center gap-3">
            <span className={`w-2.5 h-2.5 rounded-full ${health.gemini?.status === 'online' ? 'bg-blue-400' : 'bg-red-500'}`} />
            <div>
              <p className="stat-label" style={{ color: 'var(--text-muted)' }}>Gemini AI</p>
              <p className="text-sm font-semibold capitalize">{health.gemini?.status || 'unknown'}</p>
            </div>
          </div>
          <div className="enterprise-card p-4 flex items-center gap-3">
            <span className={`w-2.5 h-2.5 rounded-full ${health.sandbox?.mode === 'docker' ? 'bg-blue-400' : 'bg-red-400'}`} />
            <div>
              <p className="stat-label" style={{ color: 'var(--text-muted)' }}>Sandbox</p>
              <p className="text-sm font-semibold capitalize">
                {health.sandbox?.mode || 'unknown'}
                {health.sandbox?.mode === 'docker' ? ' · ✓ isolated' : ' · local fallback'}
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Install App Banner */}
      {user && installations === 0 && !installBannerDismissed && installUrl && (
        <div className="enterprise-card p-4 mb-6 flex items-center justify-between gap-4" style={{ borderColor: 'rgba(250, 204, 21, 0.4)' }}>
          <div className="flex items-center gap-3">
            <span className="text-xl">⚠️</span>
            <div>
              <p className="text-sm font-semibold">Install the AI Risk Guard app on your repositories</p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Your repositories won't be scanned until the app is installed.</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <a href={installUrl} target="_blank" rel="noreferrer"
              className="btn-primary">Install App</a>
            <button onClick={() => setInstallBannerDismissed(true)}
              className="btn-secondary">Dismiss</button>
          </div>
        </div>
      )}

      {/* KPI stat cards (unique, top-level) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
          label="Unique PRs Scanned"
          value={totalPrs}
          color="text-white"
          zone="card-blue"
        />
        <StatCard
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>}
          label="Active Vulnerabilities"
          value={totalVulns}
          color="text-red-200"
          zone="card-red"
        />
        <StatCard
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
          label="Avg Risk Score"
          value={avgRisk}
          color="text-white"
          suffix="/10"
          zone="card-blue"
        />
        <StatCard
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          label="Remediation Rate"
          value={remediationRate}
          color="text-slate-100"
          suffix="%"
          zone="card-silver"
        />
      </div>

      {/* Week summary chips */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="enterprise-card card-blue p-4 flex items-center gap-4">
          <div className="stat-icon text-white">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </div>
          <div>
            <p className="stat-label" style={{ color: 'rgba(241,245,249,0.7)' }}>PRs Scanned · 7d</p>
            <p className="text-lg font-bold text-white">{week.scans_7d ?? 0}</p>
          </div>
        </div>
        <div className="enterprise-card card-red p-4 flex items-center gap-4">
          <div className="stat-icon text-white">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3m0 4h.01M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z" /></svg>
          </div>
          <div>
            <p className="stat-label" style={{ color: 'rgba(255,255,255,0.7)' }}>New Open · 7d</p>
            <p className="text-lg font-bold text-white">{week.new_7d ?? 0}</p>
          </div>
        </div>
        <div className="enterprise-card card-silver p-4 flex items-center gap-4">
          <div className="stat-icon text-silver">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          </div>
          <div>
            <p className="stat-label" style={{ color: 'rgba(241,245,249,0.7)' }}>Open Now</p>
            <p className="text-lg font-bold">{week.open_now ?? 0}</p>
          </div>
        </div>
      </motion.div>

      {/* Charts: Risk distribution + PR scan volume */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <div className="enterprise-card p-6 flex flex-col items-center">
          <h4 className="chart-label mb-6">Risk Distribution</h4>
          <div className="w-48 h-48">
            <Doughnut data={riskChartData} options={{ cutout: '70%', plugins: { legend: { display: false } }, maintainAspectRatio: true }} />
          </div>
          <div className="flex gap-4 mt-4 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-300" /> Low {riskLevels.LOW || 0}</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Med {riskLevels.MEDIUM || 0}</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> High {riskLevels.HIGH || 0}</span>
          </div>
        </div>

        <div className="enterprise-card xl:col-span-2 p-6">
          <h4 className="chart-label mb-6">PRs Scanned — Last 7 Days</h4>
          <div className="h-48">
            <Bar data={trendChartData} options={{
              responsive: true, maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: { x: { grid: { display: false }, ticks: { color: 'var(--text-muted)' } }, y: { grid: { color: 'rgba(136,136,160,0.1)' }, ticks: { color: 'var(--text-muted)' }, beginAtZero: true } },
            }} />
          </div>
        </div>
      </div>

      {/* Needs Attention */}
      <div className="enterprise-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="chart-label">Needs Attention</h4>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Open HIGH-risk findings from the latest scan per PR
          </span>
        </div>
        {attention.length > 0 ? (
          <div className="space-y-2">
            {attention.map((a) => (
              <Link
                key={a.id}
                to={`/scan/${a.scan_id}`}
                className="flex items-center justify-between gap-3 p-3 rounded-lg transition-all hover:scale-[1.005] hover:bg-black/5 dark:hover:bg-white/5 block"
                style={{ backgroundColor: 'var(--bg)' }}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="badge badge-red flex-shrink-0">{a.severity}</span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold truncate">
                      <span style={{ color: 'var(--text-main)' }}>{a.vuln_type}</span>
                      <span className="ml-2 text-xs font-normal" style={{ color: 'var(--text-muted)' }}>{a.file_path}</span>
                    </p>
                    <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                      {a.repo_full_name} · #{a.pr_number}{a.pr_title ? ` — ${a.pr_title}` : ''}
                    </p>
                  </div>
                </div>
                <span className="text-sm font-bold text-red-400 flex-shrink-0">{a.risk_score != null ? a.risk_score.toFixed(1) : '—'}</span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            <span className="text-3xl mr-2">🛡️</span> No open high-risk findings. Nice work.
          </div>
        )}
      </div>
    </div>
  )
}