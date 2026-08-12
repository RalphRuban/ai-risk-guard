import { useState, useEffect, useCallback, useMemo } from 'react'
import PageHeader from '../components/PageHeader'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { getDashboard, getUser } from '../api/client'

function RiskCount({ label, value, color }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-sm font-semibold">{value}</span>
      <span className="stat-label" style={{ color: 'var(--text-muted)' }}>{label}</span>
    </div>
  )
}

export default function Repositories() {
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  const fetchRepos = useCallback(async () => {
    try {
      const data = await getDashboard()
      setRepos(data?.repos || [])
      setError(null)
    } catch (err) {
      setError(err?.response?.data?.message || 'Failed to load repositories')
    }
  }, [])

  useEffect(() => {
    getUser().then((auth) => {
      if (auth.authenticated) {
        fetchRepos().finally(() => setLoading(false))
      } else {
        setLoading(false)
        setError('Please log in to view repositories')
      }
    }).catch(() => {
      setLoading(false)
      setError('Please log in to view repositories')
    })
  }, [fetchRepos])

  const totalScans = repos.reduce((s, r) => s + (r.total_scans || 0), 0)
  const totalHigh = repos.reduce((s, r) => s + (r.high_risk || 0), 0)
  const totalMed = repos.reduce((s, r) => s + (r.med_risk || 0), 0)
  const totalLow = repos.reduce((s, r) => s + (r.low_risk || 0), 0)

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return repos
    return repos.filter((r) =>
      (r.full_name || '').toLowerCase().includes(q) ||
      (r.description || '').toLowerCase().includes(q) ||
      (r.language || '').toLowerCase().includes(q) ||
      (r.owner || '').toLowerCase().includes(q)
    )
  }, [repos, search])

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-56 bg-gray-700 rounded mb-1 animate-pulse" />
        <div className="h-4 w-72 bg-gray-700 rounded mb-8 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1,2,3,4,5,6].map(i => (
            <div key={i} className="enterprise-card p-5 animate-pulse">
              <div className="h-5 w-3/4 bg-gray-700 rounded mb-4" />
              <div className="h-3 w-1/3 bg-gray-700 rounded mb-3" />
              <div className="flex gap-6">
                <div className="h-4 w-16 bg-gray-700 rounded" />
                <div className="h-4 w-16 bg-gray-700 rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error && repos.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="enterprise-card p-8 text-center">
          <div className="text-5xl mb-4">📦</div>
          <h2 className="text-xl font-bold mb-2">Repositories</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{error}</p>
          {error.includes('log in') ? (
            <a
              href="/login"
              className="inline-block px-6 py-2.5 btn-primary"
            >
              Log in
            </a>
          ) : (
            <button
              onClick={() => { setLoading(true); fetchRepos().finally(() => setLoading(false)) }}
              className="px-6 py-2.5 btn-primary"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader eyebrow="Inventory" title="Repositories"
        subtitle={`${repos.length} tracked repos · ${totalScans} total scans`}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search repos…"
          className="input-field w-48 sm:w-56"
        />
        {error && (
          <button onClick={() => fetchRepos()} className="btn-secondary">↻ Refresh</button>
        )}
      </PageHeader>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="enterprise-card card-blue p-5">
          <p className="stat-label mb-1" style={{ color: 'rgba(241,245,249,0.7)' }}>Repositories</p>
          <h3 className="stat-heading text-white">{repos.length}</h3>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="enterprise-card p-5">
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Total Scans</p>
          <h3 className="stat-heading">{totalScans}</h3>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="enterprise-card card-red p-5">
          <p className="stat-label mb-1" style={{ color: 'rgba(255,255,255,0.7)' }}>Open High Risk</p>
          <h3 className="stat-heading text-white">{totalHigh}</h3>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="enterprise-card card-silver p-5">
          <p className="stat-label mb-1" style={{ color: 'rgba(241,245,249,0.7)' }}>Open Findings</p>
          <h3 className="stat-heading">{totalHigh + totalMed + totalLow}</h3>
        </motion.div>
      </div>

      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((r, i) => (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link
                to={`/repositories/${r.id}`}
                className="enterprise-card p-5 block hover:scale-[1.02] transition-transform"
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="min-w-0">
                    <h3 className="font-bold truncate">{r.full_name}</h3>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      {r.language || 'Unknown'} · {r.total_scans || 0} scans · {r.private ? 'Private' : 'Public'}
                    </p>
                  </div>
                  <span className={`badge flex-shrink-0 ${(r.high_risk || 0) > 0 ? 'badge-red' : 'badge-ok'}`}>
                    {(r.high_risk || 0) > 0 ? '⚠ At risk' : '✓ Healthy'}
                  </span>
                </div>
                {r.description && (
                  <p className="text-xs mb-3 line-clamp-2" style={{ color: 'var(--text-muted)' }}>
                    {r.description}
                  </p>
                )}
                <div className="flex gap-5 mb-3">
                  <RiskCount label="High" value={r.high_risk || 0} color="#F43F5E" />
                  <RiskCount label="Med" value={r.med_risk || 0} color="#3B82F6" />
                  <RiskCount label="Low" value={r.low_risk || 0} color="#A8B0BC" />
                </div>
                <p className="stat-label" style={{ color: 'var(--text-muted)' }}>
                  Last scanned {r.last_scan_at ? new Date(r.last_scan_at).toLocaleDateString() : '—'}
                </p>
              </Link>
            </motion.div>
          ))}
        </div>
      ) : search.trim() ? (
        <div className="enterprise-card p-12 text-center">
          <div className="text-5xl mb-4 opacity-40">🔍</div>
          <h2 className="text-xl font-bold mb-2">No Matching Repositories</h2>
          <p style={{ color: 'var(--text-muted)' }}>No repositories match "{search}". Try a different search.</p>
        </div>
      ) : (
        <div className="enterprise-card p-12 text-center">
          <div className="text-5xl mb-4 opacity-40">📦</div>
          <h2 className="text-xl font-bold mb-2">No Repositories Yet</h2>
          <p style={{ color: 'var(--text-muted)' }}>Install the GitHub App and open a PR to start scanning.</p>
        </div>
      )}
    </div>
  )
}
