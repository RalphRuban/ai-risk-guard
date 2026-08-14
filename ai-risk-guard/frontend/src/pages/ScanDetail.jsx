import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Link, useParams } from 'react-router-dom'
import { getScan, getScanFindings, getUser, submitFeedback } from '../api/client'

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

function RiskScore({ score }) {
  const color = score >= 7 ? '#F43F5E' : score >= 4 ? '#3B82F6' : '#A8B0BC'
  return <span className="font-bold" style={{ color }}>{score != null ? score.toFixed(1) : '—'}</span>
}

function StatBox({ label, value, color = '' }) {
  return (
    <div className="enterprise-card p-5">
      <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
      <h3 className={`stat-heading ${color}`}>{value}</h3>
    </div>
  )
}

function FeedbackCard({ repoId, prNumber, scanId, findings }) {
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
    <div className="enterprise-card p-5 mb-8">
      <h4 className="chart-label mb-2">Patch Feedback</h4>
      {types.length > 0 ? (
        <>
          <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
            Vulnerability types detected in PR #{prNumber} — only what was actually detected is listed.
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
          No findings detected in this scan — nothing to rate.
        </p>
      )}
      {msg && (
        <p className={`text-xs font-medium ${msg.type === 'success' ? 'text-slate-300' : 'text-red-500'}`}>{msg.text}</p>
      )}
    </div>
  )
}

export default function ScanDetail() {
  const { scanId } = useParams()
  const [scan, setScan] = useState(null)
  const [findings, setFindings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchDetail = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true)
    try {
      const [s, f] = await Promise.all([
        getScan(scanId),
        getScanFindings(scanId),
      ])
      setScan(s)
      setFindings(f)
      setError(null)
    } catch (err) {
      setError(err?.response?.status === 404 ? 'Scan not found' : 'Failed to load scan')
    } finally {
      if (showLoader) setLoading(false)
    }
  }, [scanId])

  useEffect(() => {
    getUser().then((auth) => {
      if (auth.authenticated) {
        fetchDetail(true)
      } else {
        setLoading(false)
        setError('Please log in to view scan details')
      }
    }).catch(() => {
      setLoading(false)
      setError('Please log in to view scan details')
    })
  }, [fetchDetail])

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

  if (error && !scan) {
    const isAuthError = error.includes('log in')
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="enterprise-card p-8 text-center">
          <div className="text-5xl mb-4">🔍</div>
          <h2 className="text-xl font-bold mb-2">{isAuthError ? 'Authentication Required' : 'Scan Not Found'}</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{error}</p>
          {isAuthError ? (
            <a href="/login" className="inline-block px-6 py-2.5 btn-primary">
              Log in
            </a>
          ) : (
            <Link to="/repositories" className="inline-block px-6 py-2.5 btn-primary">
              Back to Repositories
            </Link>
          )}
        </div>
      </div>
    )
  }

  const prUrl = scan?.repo_full_name
    ? `https://github.com/${scan.repo_full_name}/pull/${scan.pr_number}`
    : null

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link to={`/repositories/${scan?.repo_id}`} className="text-sm font-medium mb-4 inline-block" style={{ color: 'var(--text-muted)' }}>
        ← {scan?.repo_full_name || 'Repository'}
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-2">
        <div className="min-w-0">
          <span className="eyebrow">Scan Report</span>
          <h1 className="k-title break-words">
            {scan?.pr_title || 'Scan'} <span className="text-blue-500">#{scan?.pr_number}</span>
          </h1>
          <p className="k-sub">
            {scan?.repo_full_name} · PR #{scan?.pr_number} · {scan?.branch || 'unknown'} branch
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {prUrl && (
            <a
              href={prUrl}
              target="_blank"
              rel="noreferrer"
              className="btn-accent"
            >
              Open PR ↗
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

      {/* Scan stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        <StatBox label="Findings" value={scan?.findings_count ?? findings.length} color="text-blue-400" />
        <StatBox label="Max Risk" value={scan?.max_risk != null ? scan.max_risk.toFixed(1) : '—'} color="text-red-400" />
        <StatBox label="Duration" value={scan?.duration_ms != null ? `${(scan.duration_ms / 1000).toFixed(1)}s` : '—'} />
        <StatBox label="Status" value={(scan?.status || '—').toUpperCase()} color={scan?.status === 'completed' ? 'text-slate-300' : 'text-blue-400'} />
        <StatBox label="Validation" value={scan?.validation_status === 'pending' ? 'PENDING RE-VALIDATION' : 'VALIDATED'} color={scan?.validation_status === 'pending' ? 'text-amber-400' : 'text-emerald-400'} />
      </div>

      {/* Commit details */}
      <div className="enterprise-card p-5 mb-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Commit</p>
          <p className="font-mono text-sm truncate">{scan?.commit_sha || '—'}</p>
        </div>
        <div>
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Branch</p>
          <p className="text-sm font-medium truncate">{scan?.branch || '—'}</p>
        </div>
        <div>
          <p className="stat-label mb-1" style={{ color: 'var(--text-muted)' }}>Scanned At</p>
          <p className="text-sm font-medium">{scan?.scanned_at ? new Date(scan.scanned_at).toLocaleString() : '—'}</p>
        </div>
      </div>

      {/* Feedback */}
      <FeedbackCard
        repoId={scan?.repo_id}
        prNumber={scan?.pr_number}
        scanId={scan?.id}
        findings={findings}
      />

      {/* Findings */}
      <div className="enterprise-card p-6">
        <h4 className="chart-label mb-6">Findings ({findings.length})</h4>
        {findings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b" style={{ borderColor: 'var(--border)' }}>
                <tr className="stat-label" style={{ color: 'var(--text-muted)' }}>
                  <th className="pb-3 px-2">Type</th>
                  <th className="pb-3 px-2">Severity</th>
                  <th className="pb-3 px-2">Risk</th>
                  <th className="pb-3 px-2">Location</th>
                  <th className="pb-3 px-2">Status</th>
                  <th className="pb-3 px-2">New</th>
                  <th className="pb-3 px-2">Found</th>
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
                    <td className="py-3 px-2 font-mono text-xs max-w-[240px] truncate">
                      {f.file_path}:{f.line_number}
                    </td>
                    <td className="py-3 px-2 text-xs capitalize">{f.status}</td>
                    <td className="py-3 px-2">
                      {f.is_new
                        ? <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">NEW</span>
                        : <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>—</span>}
                    </td>
                    <td className="py-3 px-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {f.created_at ? new Date(f.created_at).toLocaleDateString() : '—'}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            No findings in this scan — the PR was clean.
          </div>
        )}
      </div>
    </div>
  )
}