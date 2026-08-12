import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const stages = [
  {
    id: 'scanner',
    title: 'Scanner Agent',
    subtitle: 'AST-based Vulnerability Detection',
    color: 'blue',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    details: [
      'Parses Python source code into Abstract Syntax Trees (AST)',
      'Traverses each node to detect vulnerability patterns',
      'Detects 8+ types: SQL injection, command injection, secrets, path traversal, SSRF, etc.',
      'Context validator distinguishes real vulns from test code',
      'Diff-aware scanning on changed lines only',
    ],
  },
  {
    id: 'patcher',
    title: 'Patch Agent',
    subtitle: 'AST Fixers + Gemini LLM',
    color: 'purple',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    details: [
      'Deterministic AST fixers for each vulnerability type',
      'shell=False for command injection, path sanitization for path traversal',
      'Hardcoded secrets replaced with os.getenv references',
      'Google Gemini generates context-aware alternative patches',
      'Fallback chain: tries multiple Gemini models in sequence',
      'Patches cached to avoid redundant API calls',
    ],
  },
  {
    id: 'validator',
    title: 'Validator Agent',
    subtitle: '5-Stage Validation Pipeline',
    color: 'green',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    details: [
      'Stage 1: Syntax validation — verifies patch parses correctly',
      'Stage 2: Sandbox execution — runs code in Docker with no network',
      'Stage 3: Security re-scan — checks for remaining vulnerabilities',
      'Stage 4: Policy compliance — verifies mandatory sanitizers applied',
      'Stage 5: Regression testing — runs synthesized test files',
      'Docker unavailable? Falls back to local with environment-aware scoring',
    ],
  },
  {
    id: 'risk',
    title: 'Risk Agent',
    subtitle: 'Multi-Factor Risk Scoring',
    color: 'orange',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    ),
    details: [
      'Calculates risk score (0-10) from 7 weighted factors',
      'Severity (0.22), Type (0.14), Validation (0.16), Confidence (0.12)',
      'Sensitivity (0.12), Exposure (0.12), Quality (0.12)',
      'Confidence score (0.2-0.95) from validation + tests + historical learning',
      'Winner selection: quality_score - avg_risk, prefers LLM on ties',
      'Candidates with ranking_score < 0.1 are suppressed',
    ],
  },
  {
    id: 'reporter',
    title: 'Reporter',
    subtitle: 'GitHub PR Integration + SARIF',
    color: 'cyan',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
    details: [
      'Posts structured PR comments with collapsible finding cards',
      'Severity emojis, risk badges, validation status icons',
      'Syntax-highlighted diff blocks showing suggested fixes',
      'SARIF output uploaded to GitHub Code Scanning API',
      'Security risk labels applied to PRs (high/medium/low)',
      'Existing comments updated instead of creating duplicates',
    ],
  },
]

export default function Pipeline({ embedded }) {
  const [activeStage, setActiveStage] = useState('scanner')

  const stage = stages.find((s) => s.id === activeStage)
  const activeIndex = stages.findIndex((s) => s.id === activeStage)

  return (
    <div className={`${embedded ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}`}>
      {!embedded && (
        <div className="mb-8">
          <span className="eyebrow">Architecture</span>
          <h1 className="k-title">Pipeline Architecture</h1>
          <p className="k-sub">
            End-to-end automated security analysis flow — click a stage for details
          </p>
        </div>
      )}

      {/* Flowchart */}
      <div className="enterprise-card p-8 mb-8 overflow-x-auto">
        <div className="flex items-center min-w-[600px] justify-center">
          {stages.map((s, i) => (
            <div key={s.id} className="flex items-center">
              <button
                onClick={() => setActiveStage(s.id)}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-300 cursor-pointer ${
                  activeStage === s.id
                    ? 'scale-110 shadow-lg'
                    : 'opacity-60 hover:opacity-100'
                }`}
                style={{
                  backgroundColor: activeStage === s.id
                    ? `var(--highlight)`
                    : 'transparent',
                  border: activeStage === s.id
                    ? `2px solid var(--accent)`
                    : '2px solid transparent',
                }}
              >
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center text-white"
                  style={{
                    backgroundColor:
                      s.color === 'blue' ? '#3B82F6' :
                      s.color === 'purple' ? '#4A94FF' :
                      s.color === 'green' ? '#3B82F6' :
                      s.color === 'orange' ? '#F43F5E' :
                      '#3B82F6',
                  }}
                >
                  {s.icon}
                </div>
                <span className="text-xs font-semibold">{s.title.split(' ')[0]}</span>
              </button>
              {i < stages.length - 1 && (
                <div className="flex items-center mx-2">
                  <div className="w-12 h-0.5" style={{ backgroundColor: 'var(--border)' }} />
                  <motion.div
                    animate={{ x: [0, 4, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: 'var(--accent)' }}
                  />
                  <div className="w-12 h-0.5" style={{ backgroundColor: 'var(--border)' }} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Active Stage Details */}
      <AnimatePresence mode="wait">
        {stage && (
          <motion.div
            key={stage.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="enterprise-card p-8"
          >
            <div className="flex items-center gap-4 mb-6">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center text-white"
                style={{
                  backgroundColor:
                    stage.color === 'blue' ? '#3B82F6' :
                    stage.color === 'purple' ? '#4A94FF' :
                    stage.color === 'green' ? '#3B82F6' :
                    stage.color === 'orange' ? '#F43F5E' :
                    '#3B82F6',
                }}
              >
                {stage.icon}
              </div>
              <div>
                <h2 className="k-sub text-lg font-bold" style={{ color: 'var(--text-main)' }}>{stage.title}</h2>
                <p style={{ color: 'var(--text-muted)' }}>{stage.subtitle}</p>
              </div>
              <div className="ml-auto">
                <span
                  className="px-3 py-1 rounded-full text-xs font-semibold"
                  style={{
                    backgroundColor: `var(--highlight)`,
                    color: 'var(--accent-bright)',
                  }}
                >
                  Stage {activeIndex + 1} of {stages.length}
                </span>
              </div>
            </div>

            <ul className="space-y-3">
              {stage.details.map((d, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-start gap-3"
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0"
                    style={{ backgroundColor: 'var(--accent)' }}
                  />
                  <span style={{ color: 'var(--text-muted)' }}>{d}</span>
                </motion.li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Navigation Dots */}
      <div className="flex justify-center gap-2 mt-6">
        {stages.map((s, i) => (
          <button
            key={s.id}
            onClick={() => setActiveStage(s.id)}
            className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${
              activeStage === s.id ? 'scale-150' : 'opacity-30 hover:opacity-60'
            }`}
            style={{
              backgroundColor:
                s.color === 'blue' ? '#3B82F6' :
                s.color === 'purple' ? '#4A94FF' :
                s.color === 'green' ? '#3B82F6' :
                s.color === 'orange' ? '#F43F5E' :
                '#3B82F6',
            }}
          />
        ))}
      </div>
    </div>
  )
}
