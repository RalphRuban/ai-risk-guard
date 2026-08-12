import { useState, useEffect, useCallback } from 'react'
import PageHeader from '../components/PageHeader'
import { motion } from 'framer-motion'
import { getPolicy, getUser } from '../api/client'

function CardSkeleton() {
  return (
    <div className="enterprise-card p-6 animate-pulse">
      <div className="h-3 w-32 bg-gray-700 rounded mb-6" />
      <div className="h-4 w-2/3 bg-gray-700 rounded mb-2" />
      <div className="h-4 w-1/2 bg-gray-700 rounded" />
    </div>
  )
}

function Chip({ children }) {
  return (
    <span
      className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium mr-2 mb-2"
      style={{ backgroundColor: 'var(--highlight)', border: '1px solid var(--border)' }}
    >
      {children}
    </span>
  )
}

function SectionCard({ title, subtitle = '', children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="enterprise-card p-6"
    >
      <h2 className="stat-label mb-1">{title}</h2>
      {subtitle && <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </motion.div>
  )
}

function RuleRow({ label, value, message }) {
  return (
    <div className="py-2 border-b last:border-b-0" style={{ borderColor: 'var(--border)' }}>
      <p className="text-sm font-medium break-all">
        <span className="font-mono">{label}</span>
        {value !== undefined && value !== null && (
          <span className="ml-2 text-xs" style={{ color: 'var(--text-muted)' }}>
            {value}
          </span>
        )}
      </p>
      {message && (
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
          {message}
        </p>
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>
      None configured
    </p>
  )
}

export default function Policy() {
  const [policy, setPolicy] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchPolicy = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true)
    try {
      const result = await getPolicy()
      setPolicy(result)
      setError(null)
    } catch (err) {
      setError(err?.response?.data?.message || 'Failed to load policy')
    } finally {
      if (showLoader) setLoading(false)
    }
  }, [])

  useEffect(() => {
    getUser().then((data) => {
      if (data.authenticated) {
        fetchPolicy(true)
      } else {
        setLoading(false)
        setError('Please log in to view the policy')
      }
    }).catch(() => {
      setLoading(false)
      setError('Please log in to view the policy')
    })
  }, [fetchPolicy])

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-8 w-48 bg-gray-700 rounded mb-1 animate-pulse" />
        <div className="h-4 w-64 bg-gray-700 rounded mb-8 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <CardSkeleton />
      </div>
    )
  }

  if (error && !policy) {
    const isAuthError = error.includes('log in')
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="enterprise-card p-8 text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold mb-2">{isAuthError ? 'Authentication Required' : 'Failed to Load Policy'}</h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{error}</p>
          {isAuthError ? (
            <a
              href="/login"
              className="inline-block px-6 py-2.5 btn-primary"
            >
              Log in
            </a>
          ) : (
            <button
              onClick={() => fetchPolicy(true)}
              className="px-6 py-2.5 btn-primary"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    )
  }

  const chips = (items) =>
    items && items.length > 0
      ? items.map((item) => <Chip key={item}>{item}</Chip>)
      : <EmptyState />

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {error && (
        <div
          className="mb-4 p-3 rounded-lg text-sm font-medium"
          style={{ backgroundColor: 'rgba(225, 29, 72, 0.1)', color: '#F43F5E', border: '1px solid rgba(244, 63, 94, 0.3)' }}
        >
          {error} — <button onClick={() => fetchPolicy(false)} className="underline font-semibold">Retry</button>
        </div>
      )}

      {/* Header */}
      <PageHeader eyebrow="Guardrails" title="Security Policy"
        subtitle="Organizational guardrails enforced during PR analysis">
        <button onClick={() => fetchPolicy(true)} className="btn-outline">↻ Refresh</button>
      </PageHeader>

      {/* Overview */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="enterprise-card p-6 mb-6"
      >
        <div className="flex flex-wrap items-center gap-3 mb-2">
          <h2 className="text-lg font-bold">{policy?.policy_name || 'Security Policy'}</h2>
          {policy?.version && (
            <span className="badge badge-blue">
              v{policy.version}
            </span>
          )}
        </div>
        {policy?.description && (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{policy.description}</p>
        )}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <SectionCard title="Forbidden Modules" subtitle="Banned from import">
          {chips(policy?.forbidden_modules)}
        </SectionCard>

        <SectionCard title="Forbidden Functions" subtitle="Banned from use">
          {chips(policy?.forbidden_functions)}
        </SectionCard>

        <SectionCard title="Sensitive Paths" subtitle="Paths treated as sensitive">
          {chips(policy?.sensitive_paths)}
        </SectionCard>

        <SectionCard title="Mandatory Sanitizers" subtitle="Required keyword arguments">
          {policy?.mandatory_sanitizers && Object.keys(policy.mandatory_sanitizers).length > 0 ? (
            Object.entries(policy.mandatory_sanitizers).map(([func, reqs]) => (
              <RuleRow key={func} label={func} value={reqs.join(', ')} />
            ))
          ) : (
            <EmptyState />
          )}
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <SectionCard title="Restricted Function Arguments" subtitle="Forbidden values for specific arguments">
          {policy?.restricted_function_args && policy.restricted_function_args.length > 0 ? (
            policy.restricted_function_args.map((rule, i) => (
              <RuleRow
                key={i}
                label={`${rule.function}(${rule.arg_index})`}
                value={rule.forbidden_values?.join(', ')}
                message={rule.violation_msg}
              />
            ))
          ) : (
            <EmptyState />
          )}
        </SectionCard>

        <SectionCard title="Mandatory Call Wrappers" subtitle="Sensitive calls must be wrapped">
          {policy?.mandatory_call_wrappers && policy.mandatory_call_wrappers.length > 0 ? (
            policy.mandatory_call_wrappers.map((rule, i) => (
              <RuleRow
                key={i}
                label={rule.target}
                value={rule.wrappers?.join(', ')}
                message={rule.violation_msg}
              />
            ))
          ) : (
            <EmptyState />
          )}
        </SectionCard>

        <SectionCard title="Forbidden Assignments" subtitle="Variables that must not hold literals">
          {policy?.forbidden_assignments && policy.forbidden_assignments.length > 0 ? (
            policy.forbidden_assignments.map((rule, i) => (
              <RuleRow
                key={i}
                label={rule.pattern}
                message={rule.violation_msg}
              />
            ))
          ) : (
            <EmptyState />
          )}
        </SectionCard>

        <SectionCard title="Mandatory Query Params" subtitle="Database calls must use parameterized queries">
          {policy?.mandatory_query_params && policy.mandatory_query_params.length > 0 ? (
            policy.mandatory_query_params.map((rule, i) => (
              <RuleRow
                key={i}
                label={`${rule.function}(param ${rule.param_arg_index})`}
                message={rule.violation_msg}
              />
            ))
          ) : (
            <EmptyState />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
