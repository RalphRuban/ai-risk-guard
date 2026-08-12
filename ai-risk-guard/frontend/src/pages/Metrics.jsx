import { useState, useEffect, useCallback } from 'react'
import PageHeader from '../components/PageHeader'
import { motion } from 'framer-motion'
import { getMetricsSummary, getUser } from '../api/client'
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

function StatCard({ label, value, color = '', zone = '' }) {
  return (
    <motion.div className={`enterprise-card p-5 ${zone}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <p className={`stat-label mb-1 ${zone ? '' : ''}`} style={{ color: zone ? 'rgba(241,245,249,0.7)' : 'var(--text-muted)' }}>
        {label}
      </p>
      <h3 className={`stat-heading ${zone ? (color || 'text-white') : color}`}>{value}</h3>
    </motion.div>
  )
}

function MetricTable({ title, headers, rows }) {
  return (
    <div className="enterprise-card p-6">
      <h4 className="chart-label mb-6">{title}</h4>
      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b" style={{ borderColor: 'var(--border)' }}>
              <tr className="stat-label" style={{ color: 'var(--text-muted)' }}>
                {headers.map((h) => <th key={h} className="pb-3 px-2">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b" style={{ borderColor: 'var(--border)' }}>
                  {row.map((cell, j) => (
                    <td key={j} className="py-3 px-2 font-mono text-xs">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
          No data recorded yet
        </div>
      )}
    </div>
  )
}

export default function Metrics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [timeAgo, setTimeAgo] = useState('')

  const fetchData = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true)
    try {
      const result = await getMetricsSummary()
      setData(result)
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load metrics')
    } finally {
      if (showLoader) setLoading(false)
    }
  }, [])

  useEffect(() => {
    getUser().then((auth) => {
      if (auth.authenticated) {
        fetchData(true)
      } else {
        setLoading(false)
        setError('Please log in to view system metrics')
      }
    }).catch(() => {
      setLoading(false)
      setError('Please log in to view system metrics')
    })
  }, [fetchData])

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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-48 bg-gray-700 rounded mb-1 animate-pulse" />
        <div className="h-4 w-64 bg-gray-700 rounded mb-8 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
          {[1,2,3,4].map(i => <div key={i} className="enterprise-card p-5 animate-pulse"><div className="h-3 w-20 bg-gray-700 rounded mb-2" /><div className="h-6 w-16 bg-gray-700 rounded" /></div>)}
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="enterprise-card p-6 animate-pulse"><div className="h-48 bg-gray-700/50 rounded" /></div>
          <div className="enterprise-card xl:col-span-2 p-6 animate-pulse"><div className="h-48 bg-gray-700/50 rounded" /></div>
        </div>
      </div>
    )
  }

  if (error && !data) {
    const isAuthError = error.includes('log in')
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="enterprise-card p-8 text-center">
          <div className="text-5xl mb-4">📈</div>
          <h2 className="text-xl font-bold mb-2">{isAuthError ? 'Authentication Required' : 'Failed to Load Metrics'}</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{error}</p>
          {isAuthError ? (
            <a href="/login" className="inline-block px-6 py-2.5 btn-primary">
              Log in
            </a>
          ) : (
            <button onClick={() => fetchData(true)} className="px-6 py-2.5 btn-primary">
              Retry
            </button>
          )}
        </div>
      </div>
    )
  }

  const scans = data?.scans || {}
  const vulns = data?.vulnerabilities || {}
  const patches = data?.patches || {}
  const gemini = data?.gemini || {}
  const cache = data?.cache || {}
  const agents = data?.agents || {}
  const sandbox = data?.sandbox || {}

  const cacheTotal = Object.values(cache.hits || {}).reduce((s, v) => s + v, 0)
  const cacheMissTotal = Object.values(cache.misses || {}).reduce((s, v) => s + v, 0)
  const cacheHitPct = cacheTotal + cacheMissTotal > 0
    ? Math.round(cacheTotal / (cacheTotal + cacheMissTotal) * 100)
    : 0

  const geminiCalls = gemini.calls || {}
  const geminiTotal = Object.values(geminiCalls).reduce((s, v) => s + v, 0)
  const geminiSuccessPct = geminiTotal > 0
    ? Math.round((geminiCalls.success || 0) / geminiTotal * 100)
    : 0

  const patchTotal = (patches.success || 0) + (patches.failure || 0)
  const patchSuccessPct = patchTotal > 0
    ? Math.round((patches.success || 0) / patchTotal * 100)
    : 0

  const scanDuration = scans.duration_seconds || {}
  const scanStatusData = {
    labels: ['Success', 'Failure'],
    datasets: [{
      data: [scans.success || 0, scans.failure || 0],
      backgroundColor: ['rgba(59, 130, 246, 0.85)', 'rgba(244, 63, 94, 0.85)'],
      borderColor: ['rgba(59,130,246,1)', 'rgba(244,63,94,1)'],
      borderWidth: 1,
    }],
  }

  const cacheData = {
    labels: Object.keys({ ...(cache.hits || {}), ...(cache.misses || {}) }),
    datasets: [
      { label: 'Hits', data: Object.entries(cache.hits || {}).map(([k]) => cache.hits[k] || 0), backgroundColor: 'rgba(21, 94, 239, 0.85)', borderColor: 'rgba(59,130,246,1)', borderWidth: 1, borderRadius: 0 },
      { label: 'Misses', data: Object.entries(cache.misses || {}).map(([k]) => cache.misses[k] || 0), backgroundColor: 'rgba(244, 63, 94, 0.85)', borderColor: 'rgba(225,29,72,1)', borderWidth: 1, borderRadius: 0 },
    ],
  }

  const activeVulns = vulns.active || {}
  const vulnSeverityData = {
    labels: ['Low', 'Medium', 'High'],
    datasets: [{
      data: [activeVulns.LOW || 0, activeVulns.MEDIUM || 0, activeVulns.HIGH || 0],
      backgroundColor: ['rgba(168, 176, 188, 0.85)', 'rgba(59, 130, 246, 0.85)', 'rgba(244, 63, 94, 0.85)'],
      borderColor: ['rgba(168,176,188,1)', 'rgba(59,130,246,1)', 'rgba(244,63,94,1)'],
      borderWidth: 1,
    }],
  }

  const agentRows = Object.entries(agents.duration_seconds || {}).map(([agent, s]) => [
    agent, s.count || 0, s.avg != null ? s.avg.toFixed(2) : '—',
    s.p50 != null ? s.p50.toFixed(2) : '—', s.p95 != null ? s.p95.toFixed(2) : '—',
  ])

  const sandboxRows = Object.entries(sandbox.runs || {}).map(([mode, count]) => {
    const dur = (sandbox.duration_seconds || {})[mode] || {}
    return [mode, count || 0, dur.count || 0, dur.avg != null ? dur.avg.toFixed(2) : '—', dur.p95 != null ? dur.p95.toFixed(2) : '—']
  })

  const hasAny = scans.total > 0 || vulns.total > 0 || geminiTotal > 0 || cacheTotal > 0 || agents.duration_seconds

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader eyebrow="Telemetry" title="System Metrics"
        subtitle={<span>Real-time performance of scans, patches, caches, and agents {lastUpdated && <span className="ml-2 text-xs opacity-60">updated {timeAgo}</span>}</span>}>
        <button onClick={() => fetchData(true)} className="btn-outline">↻ Refresh</button>
      </PageHeader>

      {error && (
        <div className="mb-4 p-3 rounded-lg text-sm font-medium" style={{ backgroundColor: 'rgba(225, 29, 72, 0.1)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
          {error} — <button onClick={() => fetchData(false)} className="underline font-semibold">Retry</button>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Scans" value={scans.total || 0} zone="card-blue" />
        <StatCard label="Vulnerabilities" value={vulns.total || 0} color="text-red-300" zone="card-red" />
        <StatCard label="Patch Success" value={`${patchSuccessPct}%`} zone="card-silver" />
        <StatCard label="Cache Hit Rate" value={`${cacheHitPct}%`} color="text-blue-200" zone="card-blue" />
        <StatCard label="Gemini Calls" value={geminiTotal} />
        <StatCard label="Gemini Success" value={`${geminiSuccessPct}%`} color="text-slate-300" />
        <StatCard label="Active Analyses" value={data?.system?.active_analyses || 0} />
        <StatCard label="Sandbox Runs" value={Object.values(sandbox.runs || {}).reduce((s, v) => s + v, 0)} />
      </div>

      {hasAny ? (
        <>
          {/* Charts */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
            <div className="enterprise-card p-6 flex flex-col items-center">
              <h4 className="chart-label mb-6">Scans by Status</h4>
              <div className="w-48 h-48">
                <Doughnut
                  data={scanStatusData}
                  options={{ cutout: '70%', plugins: { legend: { display: false } }, maintainAspectRatio: true }}
                />
              </div>
              <div className="flex gap-4 mt-4 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Success {scans.success || 0}</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Failure {scans.failure || 0}</span>
              </div>
            </div>

            <div className="enterprise-card p-6 flex flex-col items-center">
              <h4 className="chart-label mb-6">Active Vulnerabilities</h4>
              <div className="w-48 h-48">
                <Doughnut
                  data={vulnSeverityData}
                  options={{ cutout: '70%', plugins: { legend: { display: false } }, maintainAspectRatio: true }}
                />
              </div>
              <div className="flex gap-4 mt-4 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-300" /> Low {activeVulns.LOW || 0}</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Med {activeVulns.MEDIUM || 0}</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> High {activeVulns.HIGH || 0}</span>
              </div>
            </div>

            <div className="enterprise-card xl:col-span-1 p-6">
              <h4 className="chart-label mb-6">Cache Hits vs Misses</h4>
              <div className="h-48">
                <Bar
                  data={cacheData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'top', labels: { color: 'var(--text-muted)', boxWidth: 12, padding: 12 } } },
                    scales: {
                      x: { stacked: true, grid: { display: false }, ticks: { color: 'var(--text-muted)' } },
                      y: { stacked: true, grid: { color: 'rgba(136,136,160,0.1)' }, ticks: { color: 'var(--text-muted)' }, beginAtZero: true },
                    },
                  }}
                />
              </div>
            </div>
          </div>

          {/* Latency / duration cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="enterprise-card p-5">
              <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Scan Duration (s)</p>
              <p className="text-xl font-bold">{scanDuration.count || 0} scans · avg {scanDuration.avg ?? '—'}s</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>p50 {scanDuration.p50 ?? '—'}s · p95 {scanDuration.p95 ?? '—'}s</p>
            </div>
            <div className="enterprise-card p-5">
              <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Gemini Latency (s)</p>
              <p className="text-xl font-bold">avg {(gemini.latency_seconds || {}).avg ?? '—'}s</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>p50 {(gemini.latency_seconds || {}).p50 ?? '—'}s · p95 {(gemini.latency_seconds || {}).p95 ?? '—'}s</p>
            </div>
            <div className="enterprise-card p-5">
              <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Patch Quality</p>
              <p className="text-xl font-bold">{(patches.quality_score || {}).count || 0} patches</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>avg {(patches.quality_score || {}).avg ?? '—'} · p95 {(patches.quality_score || {}).p95 ?? '—'}</p>
            </div>
          </div>

          {/* Tables */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
            <MetricTable
              title="Agent Duration (seconds)"
              headers={['Agent', 'Count', 'Avg', 'p50', 'p95']}
              rows={agentRows}
            />
            <MetricTable
              title="Sandbox Runs"
              headers={['Mode', 'Runs', 'Count', 'Avg (s)', 'p95 (s)']}
              rows={sandboxRows}
            />
          </div>
        </>
      ) : (
        <div className="enterprise-card p-12 text-center">
          <div className="text-5xl mb-4 opacity-40">📈</div>
          <h2 className="text-xl font-bold mb-2">No Metrics Recorded Yet</h2>
          <p style={{ color: 'var(--text-muted)' }}>Run scans to start accumulating performance data.</p>
        </div>
      )}
    </div>
  )
}