import { useState, useEffect, useCallback } from 'react'
import PageHeader from '../components/PageHeader'
import { motion } from 'framer-motion'
import { getUser, getRepos, getSettings, updateSettings } from '../api/client'

const defaultAvatar = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2394a3b8'%3E%3Cpath d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E"

function Card({ title, children }) {
  return (
    <motion.div className="enterprise-card p-6" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <h4 className="chart-label mb-6">{title}</h4>
      {children}
    </motion.div>
  )
}

export default function Settings() {
  const [user, setUser] = useState(null)
  const [installations, setInstallations] = useState(-1)
  const [installUrl, setInstallUrl] = useState('')
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [settings, setSettings] = useState(null)
  const [settingsOptions, setSettingsOptions] = useState({ scan_modes: [], networks: [] })
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState(null)

  const fetchData = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true)
    try {
      const auth = await getUser()
      if (!auth.authenticated) {
        setError('Please log in to view settings')
        setLoading(false)
        return
      }
      setUser(auth.user)
      setInstallations(typeof auth.installations === 'number' ? auth.installations : -1)
      setInstallUrl(auth.install_url || '')
      const reposList = await getRepos()
      setRepos(reposList)

      const settingsData = await getSettings()
      setSettings(settingsData.settings || {})
      setSettingsOptions(settingsData.options || { scan_modes: [], networks: [] })

      setError(null)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load settings')
    } finally {
      if (showLoader) setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData(true)
  }, [fetchData])

  const handleSave = async () => {
    setSaving(true)
    setSaveMsg(null)
    try {
      const res = await updateSettings({
        scan_mode: settings?.scan_mode,
        sandbox_network: settings?.sandbox_network,
      })
      setSettings(res.settings)
      setSaveMsg({ type: 'success', text: 'Scan configuration saved.' })
    } catch (err) {
      setSaveMsg({ type: 'error', text: err?.response?.data?.error || 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    fetchData(true)
  }, [fetchData])

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-48 bg-gray-700 rounded mb-1 animate-pulse" />
        <div className="h-4 w-64 bg-gray-700 rounded mb-8 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="enterprise-card p-6 animate-pulse"><div className="h-64 bg-gray-700/50 rounded" /></div>
          <div className="enterprise-card p-6 animate-pulse"><div className="h-64 bg-gray-700/50 rounded" /></div>
        </div>
      </div>
    )
  }

  if (error && !user) {
    const isAuthError = error.includes('log in')
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="enterprise-card p-8 text-center">
          <div className="text-5xl mb-4">⚙️</div>
          <h2 className="text-xl font-bold mb-2">{isAuthError ? 'Authentication Required' : 'Failed to Load Settings'}</h2>
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

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader eyebrow="Configuration" title="Settings"
        subtitle="Profile, GitHub App, and connected repositories">
        <a href="/auth/logout" className="btn-secondary">Sign out</a>
        <button onClick={() => fetchData(true)} className="btn-secondary">↻ Refresh</button>
      </PageHeader>

      {error && (
        <div className="mb-4 p-3 rounded-lg text-sm font-medium" style={{ backgroundColor: 'rgba(225, 29, 72, 0.1)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.3)' }}>
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Profile */}
        <Card title="Profile">
          <div className="flex items-center gap-4 mb-6">
            <img
              src={user?.avatar_url || defaultAvatar}
              alt={user?.login}
              className="w-16 h-16 rounded-full"
              onError={(e) => { if (e.target.src !== defaultAvatar) e.target.src = defaultAvatar }}
            />
            <div>
              <p className="text-lg font-bold">{user?.name || user?.login}</p>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>@{user?.login}</p>
            </div>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt style={{ color: 'var(--text-muted)' }}>GitHub ID</dt>
              <dd className="font-mono">{user?.github_id ?? '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt style={{ color: 'var(--text-muted)' }}>Sign-in</dt>
              <dd>GitHub OAuth</dd>
            </div>
          </dl>
        </Card>

        {/* GitHub App */}
        <Card title="GitHub App">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-lg font-bold mb-1">AI Risk Guard App</p>
              <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
                Installations: {installations < 0 ? 'unknown' : installations}
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                The app receives webhook events when PRs are opened so scans run automatically. Repositories are only
                analyzed once the app is installed on them.
              </p>
            </div>
            <span className={`w-2.5 h-2.5 rounded-full mt-2 flex-shrink-0 ${installations > 0 ? 'bg-blue-400' : 'bg-red-400'}`} />
          </div>
          {installUrl && (
            <a
              href={installUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-6 btn-accent"
            >
              {installations > 0 ? 'Manage installations ↗' : 'Install App ↗'}
            </a>
          )}
        </Card>

        {/* Scan Configuration */}
        <Card title="Scan Configuration">
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
            Applies to scans from your repositories.
          </p>

          <div className="text-xs mb-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{ border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            <span className={`w-2 h-2 rounded-full ${settingsOptions.docker_available ? 'bg-blue-400' : 'bg-red-400'}`} />
            Docker {settingsOptions.docker_available ? 'available' : 'unavailable — local fallback active'}
          </div>

          <label className="block stat-label mb-2">Scan mode</label>
          <div className="space-y-3 mb-6">
            {[
              { id: 'sandbox_with_local_fallback', label: 'Sandbox with local fallback', desc: 'Run in Docker, fall back to local automatically when Docker is unavailable. (default)' },
              { id: 'sandbox_and_local_comparison', label: 'Sandbox + local comparison', desc: 'Always run tests locally alongside Docker and show the comparison on the PR.' },
            ].map((mode) => (
              <label key={mode.id} className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="scan_mode"
                  className="mt-0.5 accent-blue-600"
                  checked={settings?.scan_mode === mode.id}
                  onChange={() => setSettings((s) => ({ ...s, scan_mode: mode.id }))}
                />
                <span>
                  <span className="text-sm font-medium block">{mode.label}</span>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{mode.desc}</span>
                </span>
              </label>
            ))}
          </div>

          <label className="block stat-label mb-2">Sandbox network</label>
          <div className="space-y-3 mb-6">
            {[
              { id: 'none', label: 'None (secure)', desc: 'No network access inside the sandbox — most secure. (default)' },
              { id: 'bridge', label: 'Bridge', desc: 'Allow outbound network inside the sandbox. Only needed for dependency installs.' },
            ].map((net) => (
              <label key={net.id} className="flex items-start gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="sandbox_network"
                  className="mt-0.5 accent-blue-600"
                  checked={settings?.sandbox_network === net.id}
                  onChange={() => setSettings((s) => ({ ...s, sandbox_network: net.id }))}
                />
                <span>
                  <span className="text-sm font-medium block">{net.label}</span>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{net.desc}</span>
                </span>
              </label>
            ))}
          </div>

          {saveMsg && (
            <div className={`mb-4 p-3 rounded-lg text-sm font-medium ${saveMsg.type === 'success' ? 'text-slate-300' : 'text-red-400'}`}
              style={{ backgroundColor: saveMsg.type === 'success' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', border: `1px solid ${saveMsg.type === 'success' ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}` }}>
              {saveMsg.text}
            </div>
          )}

          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-accent disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save configuration'}
          </button>
        </Card>
      </div>

      {/* Connected repositories */}
      <Card title={`Connected Repositories (${repos.length})`}>
        {repos.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b" style={{ borderColor: 'var(--border)' }}>
                <tr className="stat-label" style={{ color: 'var(--text-muted)' }}>
                  <th className="pb-3 px-2">Repository</th>
                  <th className="pb-3 px-2">Language</th>
                  <th className="pb-3 px-2">Visibility</th>
                  <th className="pb-3 px-2">Scans</th>
                  <th className="pb-3 px-2">Last Scan</th>
                </tr>
              </thead>
              <tbody>
                {repos.map((r) => (
                  <tr key={r.id} className="border-b" style={{ borderColor: 'var(--border)' }}>
                    <td className="py-3 px-2 font-medium">{r.full_name}</td>
                    <td className="py-3 px-2">{r.language || '—'}</td>
                    <td className="py-3 px-2">
                      <span className={`badge ${r.private ? 'badge-blue' : 'badge-ok'}`}>
                        {r.private ? 'Private' : 'Public'}
                      </span>
                    </td>
                    <td className="py-3 px-2">{r.total_scans || 0}</td>
                    <td className="py-3 px-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {r.last_scan_at ? new Date(r.last_scan_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
            No repositories connected yet. Install the app to start scanning.
          </div>
        )}
      </Card>
    </div>
  )
}