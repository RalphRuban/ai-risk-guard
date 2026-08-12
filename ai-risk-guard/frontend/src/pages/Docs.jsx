import { motion } from 'framer-motion'

function Section({ id, title, subtitle = '', children }) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="enterprise-card p-6 mb-6"
    >
      <h2 className="text-lg font-bold mb-1">{title}</h2>
      {subtitle && <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{subtitle}</p>}
      <div className="space-y-3">{children}</div>
    </motion.section>
  )
}

function EnvRow({ name, desc }) {
  return (
    <div className="py-2 border-b last:border-b-0" style={{ borderColor: 'var(--border)' }}>
      <p className="text-sm font-mono font-semibold" style={{ color: 'var(--text-main)' }}>{name}</p>
      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{desc}</p>
    </div>
  )
}

const code = 'code'.replace('code', 'text-[13px] font-mono px-2 py-1 rounded bg-black/20')

export default function Docs() {
  const toc = [
    ['overview', 'Overview'],
    ['install', 'Install the GitHub App'],
    ['configure', 'Configuration'],
    ['how-it-works', 'How Scanning Works'],
    ['sandbox', 'Security Sandbox'],
    ['policy', 'Security Policy'],
    ['faq', 'FAQ'],
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col lg:flex-row gap-8">
        {/* TOC */}
        <aside className="lg:w-56 shrink-0">
          <nav className="lg:sticky lg:top-8 space-y-1">
            <p className="stat-label mb-2" style={{ color: 'var(--text-muted)' }}>On this page</p>
            {toc.map(([id, label]) => (
              <a
                key={id}
                href={`#${id}`}
                className="block px-3 py-1.5 text-sm rounded-lg hover:opacity-80 transition-all"
                style={{ color: 'var(--text-muted)' }}
              >
                {label}
              </a>
            ))}
          </nav>
        </aside>

        <div className="flex-1 min-w-0">
          <div className="mb-8">
            <span className="eyebrow">Documentation</span>
            <h1 className="k-title">Getting Started</h1>
            <p className="k-sub">
              Detect, patch, and validate security vulnerabilities in your Python code — fully automated through GitHub pull requests.
            </p>
          </div>

          <Section id="overview" title="Overview">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              AI Risk Guard is a multi-agent security tool that analyzes code changed in a pull request. It scans for
              vulnerabilities using abstract syntax tree (AST) analysis, generates patches with deterministic fixers and
              Google Gemini, validates them in an isolated Docker sandbox, and reports findings back as structured PR comments.
            </p>
          </Section>

          <Section id="install" title="Install the GitHub App">
            <ol className="list-decimal list-inside space-y-2 text-sm" style={{ color: 'var(--text-muted)' }}>
              <li>Log in to AI Risk Guard with your GitHub account.</li>
              <li>Install the AI Risk Guard GitHub App on the repositories you want to scan.</li>
              <li>Open a pull request against any installed repository.</li>
              <li>AI Risk Guard analyzes the diff and posts findings, patches, and validation status.</li>
              <li>Review the PR comment and accept or reject suggested patches to help the model learn.</li>
            </ol>
          </Section>

          <Section id="configure" title="Configuration">
            <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
              The server reads configuration from environment variables and YAML files.
            </p>
            <EnvRow name="GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET" desc="GitHub OAuth App credentials used for login and API access." />
            <EnvRow name="GITHUB_WEBHOOK_SECRET" desc="Secret shared with GitHub to verify signed webhook payloads." />
            <EnvRow name="GEMINI_API_KEY" desc="Google Gemini API key used to generate context-aware patch candidates." />
            <EnvRow name="GITHUB_APP_SLUG" desc="GitHub App slug used to build the installation URL shown in-app." />
          </Section>

          <Section id="how-it-works" title="How Scanning Works">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Each pull request runs through a pipeline of agents:
            </p>
            <ul className="list-disc list-inside space-y-2 text-sm" style={{ color: 'var(--text-muted)' }}>
              <li><strong>Scanner</strong> — parses changed Python files into ASTs and detects vulnerability patterns.</li>
              <li><strong>Patcher</strong> — applies deterministic AST fixers and proposes Gemini alternatives.</li>
              <li><strong>Validator</strong> — checks syntax, runs patched code in the sandbox, re-scans, verifies policy, and runs regression tests.</li>
              <li><strong>Risk agent</strong> — scores each finding from 0–10 using severity, confidence, and exposure.</li>
              <li><strong>Reporter</strong> — posts PR comments, SARIF reports, and security labels.</li>
            </ul>
          </Section>

          <Section id="sandbox" title="Security Sandbox">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Generated patches and tests execute in an isolated Docker container with strict limits:
            </p>
            <ul className="list-disc list-inside space-y-2 text-sm" style={{ color: 'var(--text-muted)' }}>
              <li>No network access (reads/external services are mocked in tests).</li>
              <li>Read-only filesystem with a small tmpfs for runtime storage.</li>
              <li>Memory, CPU, and process-count limits.</li>
              <li>All Linux capabilities dropped and unsafe syscalls restricted.</li>
              <li>If Docker is unavailable, a hardened local fallback applies resource limits where supported.</li>
            </ul>
            <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
              You can inspect the live sandbox mode on the <a href="/status" className="underline">System Status</a> page.
            </p>
          </Section>

          <Section id="policy" title="Security Policy">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              An organizational policy defines guardrails enforced during validation: forbidden modules and functions,
              sensitive paths, mandatory sanitizers, restricted function arguments, mandatory call wrappers, forbidden
              assignments, and required parameterized queries. Patches that violate the policy fail validation.
            </p>
          </Section>

          <Section id="faq" title="FAQ">
            <div className="space-y-3">
              <div>
                <p className="text-sm font-semibold">Which languages are supported?</p>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Python is fully supported via AST analysis.</p>
              </div>
              <div>
                <p className="text-sm font-semibold">Do you store my code?</p>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Only scan metadata and findings are persisted. Patch feedback helps the model improve.</p>
              </div>
              <div>
                <p className="text-sm font-semibold">Is Docker required?</p>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No — the tool falls back to a local sandbox when Docker is unavailable.</p>
              </div>
              <div>
                <p className="text-sm font-semibold">How do I give feedback on a patch?</p>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Use the patch feedback form on a repository's detail page (or a scan's detail page) to accept or reject a suggested fix for the vulnerability types actually detected there.</p>
              </div>
            </div>
          </Section>
        </div>
      </div>
    </div>
  )
}