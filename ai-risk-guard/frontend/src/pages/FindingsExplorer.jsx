import { useState, useEffect, useCallback, useMemo } from 'react'
import PageHeader from '../components/PageHeader'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'
import { getAllFindings, getRepos, getUser, updateFindingStatus } from '../api/client'

function SeverityBadge({ severity }) {
  const classes = {
    HIGH: 'badge badge-red',
    MEDIUM: 'badge badge-warn',
    LOW: 'badge badge-ok',
  }
  return (
    <span className={classes[severity] || 'badge'}>
      {severity}
    </span>
  )
}

function StatusBadge({ status }) {
  const classes = {
    open: 'badge badge-red',
    resolved: 'badge badge-ok',
    dismissed: 'badge',
  }
  return <span className={`${classes[status] || 'badge'} capitalize`}>{status}</span>
}

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

export default function FindingsExplorer() {
  const [findings, setFindings] = useState([])
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [repoId, setRepoId] = useState('')
  const [severity, setSeverity] = useState('')
  const [status, setStatus] = useState('open')
  const [type, setType] = useState('')
  const [q, setQ] = useState('')
  const [updatingId, setUpdatingId] = useState(null)

  const fetchFindings = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (repoId) params.repo_id = repoId
      if (severity) params.severity = severity
      if (status) params.status = status
      if (type) params.type = type
      if (q.trim()) params.q = q.trim()
      const rows = await getAllFindings(params)
      setFindings(rows)
      setError(null)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load findings')
    } finally {
      setLoading(false)
    }
  }, [repoId, severity, status, type, q])

  useEffect(() => {
    getUser().then((auth) => {
      if (!auth.authenticated) {
        setError('Please log in to view findings')
        setLoading(false)
        return
      }
      getRepos()
        .then(setRepos)
        .catch(() => {})
      fetchFindings().catch(() => {})
    }).catch(() => {
      setError('Please log in to view findings')
      setLoading(false)
    })
  }, [fetchFindings])

  const handleSetStatus = async (findingId, newStatus) => {
    setUpdatingId(findingId)
    try {
      await updateFindingStatus(findingId, newStatus)
      setFindings((prev) =>
        prev
          .filter((f) => (status ? f.id !== findingId || newStatus === status : true))
          .map((f) => (f.id === findingId ? { ...f, status: newStatus } : f))
      )
    } catch {
      setError('Failed to update finding status')
    } finally {
      setUpdatingId(null)
    }
  }

  const filteredTypes = useMemo(() => {
    const counts = {}
    findings.forEach((f) => { counts[f.vuln_type] = (counts[f.vuln_type] || 0) + 1 })
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [findings])

  const stats = useMemo(() => {
    const high = findings.filter((f) => f.severity === 'HIGH').length
    const med = findings.filter((f) => f.severity === 'MEDIUM').length
    const low = findings.filter((f) => f.severity === 'LOW').length
    return { total: findings.length, high, med, low }
  }, [findings])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader eyebrow="Triage" title="Findings Explorer"
        subtitle="Triage every detected vulnerability across your repositories">
        <button onClick={() => fetchFindings()} className="btn-outline">↻ Refresh</button>
      </PageHeader>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="enterprise-card card-blue p-4">
          <p className="stat-label mb-1" style={{ color: 'rgba(241,245,249,0.7)' }}>Matching</p>
          <h3 className="stat-heading text-white">{stats.total}</h3>
        </div>
        <div className="enterprise-card card-red p-4">
          <p className="stat-label mb-1" style={{ color: 'rgba(255,255,255,0.7)' }}>High</p>
          <h3 className="stat-heading text-white">{stats.high}</h3>
        </div>
        <div className="enterprise-card card-blue p-4">
          <p className="stat-label mb-1" style={{ color: 'rgba(241,245,249,0.7)' }}>Medium</p>
          <h3 className="stat-heading text-white">{stats.med}</h3>
        </div>
        <div className="enterprise-card card-silver p-4">
          <p className="stat-label mb-1" style={{ color: 'rgba(241,245,249,0.7)' }}>Low</p>
          <h3 className="stat-heading">{stats.low}</h3>
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
          value={severity}
          onChange={setSeverity}
          placeholder="All severities"
          options={[
            { value: 'HIGH', label: 'High' },
            { value: 'MEDIUM', label: 'Medium' },
            { value: 'LOW', label: 'Low' },
          ]}
        />
        <Select
          value={status}
          onChange={setStatus}
          placeholder="All statuses"
          options={[
            { value: 'open', label: 'Open' },
            { value: 'resolved', label: 'Resolved' },
            { value: 'dismissed', label: 'Dismissed' },
          ]}
        />
        <Select
          value={type}
          onChange={setType}
          placeholder="All types"
          options={filteredTypes.map(([t]) => ({ value: t, label: t }))}
        />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') fetchFindings() }}
          placeholder="Search repo, type, file…"
          className="flex-1 input-field"
        />
        <button
          onClick={() => fetchFindings()}
          className="btn-primary"
        >
          Apply
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg text-sm font-medium" style={{ backgroundColor: 'rgba(225, 29, 72, 0.1)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
          {error}
        </div>
      )}

      {/* Table */}
      <div className="enterprise-card p-6">
        <h4 className="chart-label mb-6">Findings ({findings.length})</h4>
        {loading ? (
          <div className="space-y-3">
            {[1,2,3,4,5].map(i => <div key={i} className="h-10 bg-gray-700/40 rounded animate-pulse" />)}
          </div>
        ) : findings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b" style={{ borderColor: 'var(--border)' }}>
                <tr className="stat-label" style={{ color: 'var(--text-muted)' }}>
                  <th className="pb-3 px-2">Repository</th>
                  <th className="pb-3 px-2">PR</th>
                  <th className="pb-3 px-2">Type</th>
                  <th className="pb-3 px-2">Severity</th>
                  <th className="pb-3 px-2">Risk</th>
                  <th className="pb-3 px-2">Location</th>
                  <th className="pb-3 px-2">Status</th>
                  <th className="pb-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence initial={false}>
                {findings.map((f) => (
                  <motion.tr
                    key={f.id}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="border-b"
                    style={{ borderColor: 'var(--border)' }}
                  >
                    <td className="py-3 px-2 max-w-[200px] truncate">
                      <Link to={`/repositories/${f.repo_id}`} className="hover:underline">{f.repo_full_name}</Link>
                    </td>
                    <td className="py-3 px-2">
                      <Link to={`/scan/${f.scan_id || f.pr_number}`} className="hover:underline font-semibold">#{f.pr_number}</Link>
                    </td>
                    <td className="py-3 px-2 font-mono text-xs">{f.vuln_type}</td>
                    <td className="py-3 px-2"><SeverityBadge severity={f.severity} /></td>
                    <td className="py-3 px-2"><RiskScore score={f.risk_score} /></td>
                    <td className="py-3 px-2 font-mono text-xs max-w-[220px] truncate">{f.file_path}:{f.line_number}</td>
                    <td className="py-3 px-2"><StatusBadge status={f.status} /></td>
                    <td className="py-3 px-2">
                      <div className="flex gap-2">
                        {f.status === 'open' ? (
                          <>
                            <button
                              onClick={() => handleSetStatus(f.id, 'resolved')}
                              disabled={updatingId === f.id}
                              className="text-xs font-semibold px-2 py-1 rounded-lg transition-all hover:scale-105 disabled:opacity-40"
                              style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3B82F6' }}
                            >
                              Resolve
                            </button>
                            <button
                              onClick={() => handleSetStatus(f.id, 'dismissed')}
                              disabled={updatingId === f.id}
                              className="text-xs font-semibold px-2 py-1 rounded-lg transition-all hover:scale-105 disabled:opacity-40"
                              style={{ backgroundColor: 'rgba(148, 163, 184, 0.15)', color: 'var(--text-muted)' }}
                            >
                              Dismiss
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleSetStatus(f.id, 'open')}
                            disabled={updatingId === f.id}
                            className="text-xs font-semibold px-2 py-1 rounded-lg transition-all hover:scale-105 disabled:opacity-40"
                            style={{ backgroundColor: 'var(--highlight)', color: 'var(--accent)' }}
                          >
                            Reopen
                          </button>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            No findings match the current filters.
          </div>
        )}
      </div>
    </div>
  )
}
