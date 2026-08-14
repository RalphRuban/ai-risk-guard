import { useState, useEffect, useCallback, useMemo } from 'react'
import PageHeader from '../components/PageHeader'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { getAllScans, getRepos, getUser, revalidateScan } from '../api/client'

function RiskScore({ score }) {
  const color = score >= 7 ? '#F43F5E' : score >= 4 ? '#3B82F6' : '#A8B0BC'
  return <span className="font-bold" style={{ color }}>{score != null ? score.toFixed(1) : '—'}</span>
}

function Select({ value, onChange, options, placeholder }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="select-field"
    >
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

export default function Scans() {
  const [scans, setScans] = useState([])
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [repoId, setRepoId] = useState('')
  const [status, setStatus] = useState('')
  const [revalidating, setRevalidating] = useState({})

  const fetchScans = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (repoId) params.repo_id = repoId
      if (status) params.status = status
      const rows = await getAllScans(params)
      setScans(rows)
      setError(null)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load scans')
    } finally {
      setLoading(false)
    }
  }, [repoId, status])

  const handleRevalidate = useCallback(async (scanId) => {
    setRevalidating((prev) => ({ ...prev, [scanId]: true }))
    try {
      await revalidateScan(scanId)
      setError(null)
      await fetchScans()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to queue re-validation')
    } finally {
      setRevalidating((prev) => ({ ...prev, [scanId]: false }))
    }
  }, [fetchScans])

  useEffect(() => {
    getUser().then((auth) => {
      if (!auth.authenticated) {
        setError('Please log in to view scans')
        setLoading(false)
        return
      }
      getRepos()
        .then(setRepos)
        .catch(() => {})
      fetchScans().catch(() => {})
    }).catch(() => {
      setError('Please log in to view scans')
      setLoading(false)
    })
  }, [fetchScans])

  const stats = useMemo(() => {
    const withFindings = scans.filter((s) => s.findings_count > 0).length
    const totalFindings = scans.reduce((s, x) => s + (x.findings_count || 0), 0)
    const highRisk = scans.filter((s) => (s.max_risk || 0) >= 7).length
    return { total: scans.length, withFindings, totalFindings, highRisk }
  }, [scans])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader eyebrow="Pull Requests" title="Pull Requests"
        subtitle="Every scanned pull request across your repositories">
        <button onClick={() => fetchScans()} className="btn-secondary">↻ Refresh</button>
      </PageHeader>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="enterprise-card p-4">
          <p className="stat-label mb-1" style={{ color: 'rgba(241,245,249,0.7)' }}>Scans</p>
          <h3 className="stat-heading text-white">{stats.total}</h3>
        </div>
        <div className="enterprise-card card-blue p-4">
          <p className="stat-label mb-1" style={{ color: 'rgba(241,245,249,0.7)' }}>With Findings</p>
          <h3 className="stat-heading text-white">{stats.withFindings}</h3>
        </div>
        <div className="enterprise-card card-red p-4">
          <p className="stat-label mb-1" style={{ color: 'rgba(255,255,255,0.7)' }}>Total Findings</p>
          <h3 className="stat-heading text-white">{stats.totalFindings}</h3>
        </div>
        <div className="enterprise-card card-silver p-4">
          <p className="stat-label mb-1" style={{ color: 'rgba(241,245,249,0.7)' }}>High Risk PRs</p>
          <h3 className="stat-heading">{stats.highRisk}</h3>
        </div>
      </div>

      {/* Filters */}
      <div className="enterprise-card p-4 mb-6 flex flex-col lg:flex-row lg:items-center gap-3">
        <Select
          value={repoId}
          onChange={setRepoId}
          placeholder="All repositories"
          options={repos.map((r) => ({ value: String(r.id), label: r.full_name }))}
        />
        <Select
          value={status}
          onChange={setStatus}
          placeholder="All statuses"
          options={[
            { value: 'completed', label: 'Completed' },
            { value: 'pending', label: 'Pending' },
            { value: 'failed', label: 'Failed' },
          ]}
        />
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg text-sm font-medium" style={{ backgroundColor: 'rgba(225, 29, 72, 0.1)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
          {error}
        </div>
      )}

      {/* Table */}
      <div className="enterprise-card p-6">
        <h4 className="chart-label mb-6">Scans ({scans.length})</h4>
        {loading ? (
          <div className="space-y-3">
            {[1,2,3,4,5].map(i => <div key={i} className="h-10 bg-gray-700/40 rounded animate-pulse" />)}
          </div>
        ) : scans.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b" style={{ borderColor: 'var(--border)' }}>
                <tr className="stat-label" style={{ color: 'var(--text-muted)' }}>
                  <th className="pb-3 px-2">Repository</th>
                  <th className="pb-3 px-2">PR</th>
                  <th className="pb-3 px-2">Title</th>
                  <th className="pb-3 px-2">Findings</th>
                  <th className="pb-3 px-2">Max Risk</th>
                  <th className="pb-3 px-2">Duration</th>
                  <th className="pb-3 px-2">Status</th>
                  <th className="pb-3 px-2">Validation</th>
                  <th className="pb-3 px-2">Scanned</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((s) => (
                  <motion.tr key={s.id} className="border-b" style={{ borderColor: 'var(--border)' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <td className="py-3 px-2 max-w-[180px] truncate">
                      <Link to={`/repositories/${s.repo_id}`} className="hover:underline">{s.repo_full_name}</Link>
                    </td>
                    <td className="py-3 px-2">
                      <Link to={`/scan/${s.id}`} className="hover:underline font-semibold">#{s.pr_number}</Link>
                    </td>
                    <td className="py-3 px-2 max-w-[220px] truncate">{s.pr_title || '—'}</td>
                    <td className="py-3 px-2">
                      <span className={s.findings_count > 0 ? 'text-blue-400 font-semibold' : ''}>{s.findings_count || 0}</span>
                    </td>
                    <td className="py-3 px-2"><RiskScore score={s.max_risk} /></td>
                    <td className="py-3 px-2">{s.duration_ms != null ? `${(s.duration_ms / 1000).toFixed(1)}s` : '—'}</td>
                    <td className="py-3 px-2">
                      <span className={`badge capitalize ${
                        s.status === 'completed' ? 'badge-ok'
                          : s.status === 'failed' ? 'badge-red'
                          : 'badge-warn'
                      }`}>
                        {s.status || '—'}
                      </span>
                    </td>
                    <td className="py-3 px-2">
                      {s.validation_status === 'pending' ? (
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="badge badge-warn">re-validation pending</span>
                          <button
                            onClick={() => handleRevalidate(s.id)}
                            disabled={revalidating[s.id]}
                            className="btn-secondary text-xs px-2 py-1"
                          >
                            {revalidating[s.id] ? 'Queuing…' : 'Re-validate'}
                          </button>
                        </div>
                      ) : (
                        <span className="badge badge-ok">validated</span>
                      )}
                    </td>
                    <td className="py-3 px-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {s.scanned_at ? new Date(s.scanned_at).toLocaleString() : '—'}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            No scans match the current filters.
          </div>
        )}
      </div>
    </div>
  )
}
