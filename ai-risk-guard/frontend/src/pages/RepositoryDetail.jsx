import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Link, useParams } from 'react-router-dom'
import { getRepo, getRepoScans, getRepoFindings, getUser, updateFindingStatus, submitFeedback, enableCodeql } from '../api/client'
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

function FeedbackCard({ repoId, findings, prNumber, scanId }) {
  const types = useMemo(() => {
    const seen = new Map()
    findings.forEach((f) => {
      if (!seen.has(f.vuln_type)) seen.set(f.vuln_type, 0)
      seen.set(f.vuln_type, seen.get(f.vuln_type) + 1)
    })
    return [...seen.entries()].sort((a, b) => b[1] - a[1])
  }, [findings])

  const [vulnType, setVulnType] = useState('')
  const [sending, setSending] = useState(false)
  const [msg, setMsg] = useState(null)

  const submit = async (outcome) => {
    if (!vulnType) {
      setMsg({ type: 'error', text: 'Select a vulnerability type first' })
      return
    }
    setSending(true)
    setMsg(null)
    try {
      await submitFeedback(vulnType, outcome, { repo_id: repoId, pr_number: prNumber, scan_id: scanId })
      setMsg({ type: 'success', text: `Feedback recorded: ${outcome} for ${vulnType}` })
      setVulnType('')
    } catch {
      setMsg({ type: 'error', text: 'Failed to submit feedback' })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="enterprise-card p-5">
      <h4 className="chart-label mb-2">Patch Feedback</h4>
      {types.length > 0 ? (
        <>
          <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
            {prNumber ? `Vulnerability types detected in PR #${prNumber}` : 'Vulnerability types detected in this repository'} — only detected types are listed.
          </p>
          <div className="flex flex-col sm:flex-row sm:items-end gap-3 mb-4">
            <div className="flex-1">
              <label className="stat-label mb-1 block" style={{ color: 'var(--text-muted)' }}>
                Vulnerability type
              </label>
              <select
                value={vulnType}
                onChange={(e) => setVulnType(e.target.value)}
                className="w-full select-field"
              >
                <option value="">Select detected type...</option>
                {types.map(([t, count]) => (
                  <option key={t} value={t}>{t} ({count}×)</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => submit('ACCEPTED')}
                disabled={sending}
                className="px-5 py-2 text-sm font-semibold rounded-lg transition-all hover:scale-105 disabled:opacity-40"
                style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3B82F6' }}
              >
                {sending ? '…' : '✓ Accept'}
              </button>
              <button
                onClick={() => submit('REJECTED')}
                disabled={sending}
                className="px-5 py-2 text-sm font-semibold rounded-lg transition-all hover:scale-105 disabled:opacity-40"
                style={{ backgroundColor: 'rgba(244, 63, 94, 0.15)', color: '#F43F5E' }}
              >
                {sending ? '…' : '✗ Reject'}
              </button>
            </div>
          </div>
        </>
      ) : (
        <p className="py-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
          No findings detected{prNumber ? ` in PR #${prNumber}` : ' yet'} — nothing to rate.
        </p>
      )}
      {msg && (
        <p className={`text-xs font-medium ${msg.type === 'success' ? 'text-slate-300' : 'text-red-500'}`}>{msg.text}</p>
      )}
    </div>
  )
}

export default function RepositoryDetail() {
  const { repoId } = useParams()
  const [repo, setRepo] = useState(null)
  const [scans, setScans] = useState([])
  const [findings, setFindings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatingId, setUpdatingId] = useState(null)
  const [codeqlAction, setCodeqlAction] = useState(null)

  const handleEnableCodeql = async () => {
    setCodeqlAction('loading')
    try {
      const res = await enableCodeql(repoId)
      setCodeqlAction(res.success ? 'success' : 'error')
      if (res.pr_url) {
        window.open(res.pr_url, '_blank', 'noopener,noreferrer')
      }
    } catch (e) {
      setCodeqlAction('error')
    }
    setTimeout(() => setCodeqlAction(null), 5000)
  }

  const fetchDetail = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true)
    try {
      const [r, s, f] = await Promise.all([
        getRepo(repoId),
        getRepoScans(repoId),
        getRepoFindings(repoId),
      ])
      setRepo(r)
      setScans(s)
      setFindings(f)
      setError(null)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load repository')
    } finally {
      if (showLoader) setLoading(false)
    }
  }, [repoId])

  useEffect(() => {
    getUser().then((auth) => {
      if (auth.authenticated) {
        fetchDetail(true)
      } else {
        setLoading(false)
        setError('Please log in to view repository details')
      }
    }).catch(() => {
      setLoading(false)
      setError('Please log in to view repository details')
    })
  }, [fetchDetail])

  const setStatus = async (findingId, status) => {
    setUpdatingId(findingId)
    try {
      await updateFindingStatus(findingId, status)
      setFindings((prev) => prev.map((f) => (f.id === findingId ? { ...f, status } : f)))
    } catch {
      setError('Failed to update finding status')
    } finally {
      setUpdatingId(null)
    }
  }

  const severityChartData = useMemo(() => {
    const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 }
    findings.forEach((f) => { if (counts[f.severity] != null) counts[f.severity] += 1 })
    return {
      labels: ['Low', 'Medium', 'High'],
      datasets: [{
        data: [counts.LOW, counts.MEDIUM, counts.HIGH],
        backgroundColor: ['rgba(168, 176, 188, 0.85)', 'rgba(59, 130, 246, 0.85)', 'rgba(244, 63, 94, 0.85)'],
        borderColor: ['rgba(168,176,188,1)', 'rgba(59,130,246,1)', 'rgba(244,63,94,1)'],
        borderWidth: 1,
      }],
    }
  }, [findings])

  const typeChartData = useMemo(() => {
    const counts = {}
    findings.forEach((f) => { counts[f.vuln_type] = (counts[f.vuln_type] || 0) + 1 })
    return {
      labels: Object.keys(counts),
      datasets: [{
        label: 'Findings',
        data: Object.values(counts),
        backgroundColor: 'rgba(59, 130, 246, 0.85)',
        borderColor: 'rgba(21, 94, 239, 1)',
        borderWidth: 1,
        borderRadius: 0,
      }],
    }
  }, [findings])

  const scanVolumeData = useMemo(() => {
    const dayCounts = {}
    scans.forEach((s) => {
      const day = (s.scanned_at || '').slice(0, 10)
      if (day) dayCounts[day] = (dayCounts[day] || 0) + 1
    })
    const days = Object.keys(dayCounts).sort().slice(-14)
    return {
      labels: days.map((d) => new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
      datasets: [{
        label: 'Scans',
        data: days.map((d) => dayCounts[d]),
        backgroundColor: 'rgba(168, 176, 188, 0.7)',
        borderColor: 'rgba(209, 213, 219, 1)',
        borderWidth: 1,
        borderRadius: 0,
      }],
    }
  }, [scans])

  const openCounts = useMemo(() => ({
    high: findings.filter((f) => f.severity === 'HIGH').length,
    med: findings.filter((f) => f.severity === 'MEDIUM').length,
    low: findings.filter((f) => f.severity === 'LOW').length,
    total: findings.length,
  }), [findings])

  const githubUrl = repo?.full_name ? `https://github.com/${repo.full_name}` : null

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-4 w-32 bg-gray-700 rounded mb-4 animate-pulse" />
        <div className="h-8 w-64 bg-gray-700 rounded mb-4 animate-pulse" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[1,2,3,4].map(i => <div key={i} className="enterprise-card p-5 animate-pulse"><div className="h-3 w-16 bg-gray-700 rounded mb-2" /><div className="h-6 w-10 bg-gray-700 rounded" /></div>)}
        </div>
        <div className="enterprise-card p-6 animate-pulse"><div className="h-64 bg-gray-700/50 rounded" /></div>
      </div>
    )
  }

  if (error && !repo) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="enterprise-card p-8 text-center">
          <div className="text-5xl mb-4">📦</div>
          <h2 className="text-xl font-bold mb-2">Repository</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{error}</p>
          <Link to="/repositories" className="inline-block px-6 py-2.5 btn-primary">
            Back to Repositories
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link to="/repositories" className="text-sm font-medium mb-4 inline-block" style={{ color: 'var(--text-muted)' }}>
        ← Repositories
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-2">
        <div className="min-w-0">
          <span className="eyebrow">Repository</span>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="k-title break-all">{repo?.full_name || 'Repository'}</h1>
            <span className={`badge ${repo?.private ? 'badge-warn' : 'badge-ok'}`}>
              {repo?.private ? 'Private' : 'Public'}
            </span>
            {repo?.language && (
              <span className="badge badge-blue">{repo.language}</span>
            )}
          </div>
          <p className="mt-1 text-sm break-all" style={{ color: 'var(--text-muted)' }}>
            {repo?.owner || ''} · {repo?.description || 'No description'}
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {repo && repo.install_id && (
            <button
              onClick={handleEnableCodeql}
              disabled={codeqlAction === 'loading'}
              className="btn-accent"
              style={{
                opacity: codeqlAction === 'loading' ? 0.7 : 1,
              }}
            >
              {codeqlAction === 'loading'
                ? 'Enabling CodeQL…'
                : codeqlAction === 'success'
                ? 'CodeQL Enabled ✓'
                : 'Enable CodeQL'}
            </button>
          )}
          {githubUrl && (
            <a
              href={githubUrl}
              target="_blank"
              rel="noreferrer"
              className="btn-accent"
            >
              View on GitHub ↗
            </a>
          )}
          <button
            onClick={() => fetchDetail(true)}
            className="btn-secondary"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg text-sm font-medium" style={{ backgroundColor: 'rgba(225, 29, 72, 0.1)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
          {error}
        </div>
      )}

      {/* Repo stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <div className="enterprise-card p-5">
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Total Scans</p>
          <h3 className="stat-heading">{repo?.total_scans || 0}</h3>
        </div>
        <div className="enterprise-card p-5">
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Open Findings</p>
          <h3 className="stat-heading text-red-400">{openCounts.total}</h3>
        </div>
        <div className="enterprise-card p-5">
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>High / Med / Low</p>
          <h3 className="text-lg font-bold">
            <span className="text-red-400">{openCounts.high}</span>
            {' / '}
            <span className="text-blue-400">{openCounts.med}</span>
            {' / '}
            <span className="text-slate-300">{openCounts.low}</span>
          </h3>
        </div>
        <div className="enterprise-card p-5">
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Default Branch</p>
          <h3 className="text-lg font-bold truncate">{repo?.default_branch || '—'}</h3>
        </div>
        <div className="enterprise-card p-5">
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Last Scan</p>
          <h3 className="text-sm font-bold">{repo?.last_scan_at ? new Date(repo.last_scan_at).toLocaleDateString() : '—'}</h3>
        </div>
        <div className="enterprise-card p-5">
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Status</p>
          <h3 className={`text-lg font-bold ${openCounts.high > 0 ? 'text-red-400' : openCounts.total > 0 ? 'text-blue-400' : 'text-slate-300'}`}>
            {openCounts.high > 0 ? 'At risk' : openCounts.total > 0 ? 'Caution' : 'Healthy'}
          </h3>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
        <div className="enterprise-card p-6 flex flex-col items-center">
          <h4 className="chart-label mb-6">Open Findings by Severity</h4>
          <div className="w-44 h-44">
            <Doughnut
              data={severityChartData}
              options={{ cutout: '70%', plugins: { legend: { display: false } }, maintainAspectRatio: true }}
            />
          </div>
          {openCounts.total === 0 && (
            <p className="mt-4 text-xs" style={{ color: 'var(--text-muted)' }}>No open findings</p>
          )}
        </div>

        <div className="enterprise-card p-6">
          <h4 className="chart-label mb-6">Findings by Type</h4>
          <div className="h-44">
            {findings.length > 0 ? (
              <Bar
                data={typeChartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { display: false } },
                  scales: {
                    x: { grid: { display: false }, ticks: { color: 'var(--text-muted)', maxRotation: 45 } },
                    y: { grid: { color: 'rgba(136,136,160,0.1)' }, ticks: { color: 'var(--text-muted)' }, beginAtZero: true },
                  },
                }}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-sm" style={{ color: 'var(--text-muted)' }}>No findings yet</div>
            )}
          </div>
        </div>

        <div className="enterprise-card p-6">
          <h4 className="chart-label mb-6">Scan Volume (14 days)</h4>
          <div className="h-44">
            {scans.length > 0 ? (
              <Bar
                data={scanVolumeData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { display: false } },
                  scales: {
                    x: { grid: { display: false }, ticks: { color: 'var(--text-muted)', maxRotation: 45 } },
                    y: { grid: { color: 'rgba(136,136,160,0.1)' }, ticks: { color: 'var(--text-muted)' }, beginAtZero: true },
                  },
                }}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-sm" style={{ color: 'var(--text-muted)' }}>No scans yet</div>
            )}
          </div>
        </div>
      </div>

      {/* Feedback card */}
      <div className="mb-8">
        <FeedbackCard repoId={repo?.id} findings={findings} />
      </div>

      {/* Scans */}
      <div className="enterprise-card p-6 mb-8">
        <h4 className="chart-label mb-6">Scans ({scans.length})</h4>
        {scans.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b" style={{ borderColor: 'var(--border)' }}>
                <tr className="stat-label" style={{ color: 'var(--text-muted)' }}>
                  <th className="pb-3 px-2">PR</th>
                  <th className="pb-3 px-2">Title</th>
                  <th className="pb-3 px-2">Findings</th>
                  <th className="pb-3 px-2">Max Risk</th>
                  <th className="pb-3 px-2">Duration</th>
                  <th className="pb-3 px-2">Scanned</th>
                  <th className="pb-3 px-2"></th>
                </tr>
              </thead>
              <tbody>
                {scans.map((s) => (
                  <tr key={s.id} className="border-b" style={{ borderColor: 'var(--border)' }}>
                    <td className="py-3 px-2 font-semibold">#{s.pr_number}</td>
                    <td className="py-3 px-2 max-w-[200px] truncate">{s.pr_title || '—'}</td>
                    <td className="py-3 px-2">{s.findings_count || 0}</td>
                    <td className="py-3 px-2"><RiskScore score={s.max_risk} /></td>
                    <td className="py-3 px-2">{s.duration_ms != null ? `${(s.duration_ms / 1000).toFixed(1)}s` : '—'}</td>
                    <td className="py-3 px-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {s.scanned_at ? new Date(s.scanned_at).toLocaleString() : '—'}
                    </td>
                    <td className="py-3 px-2">
                      <Link
                        to={`/scan/${s.id}`}
                        className="text-xs font-semibold px-2.5 py-1 rounded-lg inline-flex items-center gap-1 transition-all hover:scale-105"
                        style={{ backgroundColor: 'var(--highlight)', color: 'var(--text-main)' }}
                      >
                        View <span className="text-[10px]">→</span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            No scans yet. Open a PR to trigger analysis.
          </div>
        )}
      </div>

      {/* Findings */}
      <div className="enterprise-card p-6">
        <h4 className="chart-label mb-6">Open Findings ({findings.length})</h4>
        {findings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b" style={{ borderColor: 'var(--border)' }}>
                <tr className="stat-label" style={{ color: 'var(--text-muted)' }}>
                  <th className="pb-3 px-2">Type</th>
                  <th className="pb-3 px-2">Severity</th>
                  <th className="pb-3 px-2">Risk</th>
                  <th className="pb-3 px-2">Location</th>
                  <th className="pb-3 px-2">PR</th>
                  <th className="pb-3 px-2">Status</th>
                  <th className="pb-3 px-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((f) => (
                  <motion.tr key={f.id} className="border-b" style={{ borderColor: 'var(--border)' }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <td className="py-3 px-2 font-mono text-xs">{f.vuln_type}</td>
                    <td className="py-3 px-2"><SeverityBadge severity={f.severity} /></td>
                    <td className="py-3 px-2"><RiskScore score={f.risk_score} /></td>
                    <td className="py-3 px-2 font-mono text-xs max-w-[220px] truncate">
                      {f.file_path}:{f.line_number}
                    </td>
                    <td className="py-3 px-2">
                      <Link to={`/scan/${f.scan_id || ''}`} className="hover:underline">#{f.pr_number}</Link>
                    </td>
                    <td className="py-3 px-2"><StatusBadge status={f.status} /></td>
                    <td className="py-3 px-2">
                      {f.status === 'open' ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => setStatus(f.id, 'resolved')}
                            disabled={updatingId === f.id}
                            className="text-xs font-semibold px-2 py-1 rounded-lg transition-all hover:scale-105 disabled:opacity-40"
                            style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3B82F6' }}
                          >
                            Resolve
                          </button>
                          <button
                            onClick={() => setStatus(f.id, 'dismissed')}
                            disabled={updatingId === f.id}
                            className="text-xs font-semibold px-2 py-1 rounded-lg transition-all hover:scale-105 disabled:opacity-40"
                            style={{ backgroundColor: 'rgba(148, 163, 184, 0.15)', color: 'var(--text-muted)' }}
                          >
                            Dismiss
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setStatus(f.id, 'open')}
                          disabled={updatingId === f.id}
                          className="text-xs font-semibold px-2 py-1 rounded-lg transition-all hover:scale-105 disabled:opacity-40"
                          style={{ backgroundColor: 'var(--highlight)', color: 'var(--accent)' }}
                        >
                          Reopen
                        </button>
                      )}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            No open findings — this repository is clean.
          </div>
        )}
      </div>
    </div>
  )
}
