import React from 'react';
import { X, BookOpen, Cpu, ShieldCheck, Box, Terminal } from 'lucide-react';
import { TacticalBracket } from './TacticalBracket';
import { CyberButton } from './CyberButton';

interface DocsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DocsModal: React.FC<DocsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = React.useState<'ARCHITECTURE' | 'RISK_ENGINE' | 'SANDBOX' | 'API'>('ARCHITECTURE');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-[#020B1A]/90 backdrop-blur-xl animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-[#050B16] border border-[#17406E] shadow-[0_0_50px_rgba(0,123,255,0.2)]">
        <TacticalBracket color="#00A8FF" size="lg" />

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#17406E] bg-[#050B16]">
          <div className="flex items-center space-x-3">
            <BookOpen className="w-5 h-5 text-[#00A8FF]" />
            <div>
              <h3 className="font-headline text-lg text-white">AUREX System Documentation</h3>
              <p className="font-mono text-[10px] text-[#9AA7B8]">SPECIFICATION V2.4.0-ENTERPRISE // AUTONOMOUS SECURITY MESH</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#9AA7B8] hover:text-white hover:bg-[#0B2A5E] transition-colors border border-transparent hover:border-[#17406E]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center border-b border-[#17406E] bg-[#050B16] px-6">
          {[
            { id: 'ARCHITECTURE', label: '01 ARCHITECTURE', icon: <Cpu className="w-3.5 h-3.5" /> },
            { id: 'RISK_ENGINE', label: '02 7-FACTOR RISK', icon: <ShieldCheck className="w-3.5 h-3.5" /> },
            { id: 'SANDBOX', label: '03 SANDBOX RUNTIME', icon: <Box className="w-3.5 h-3.5" /> },
            { id: 'API', label: '04 REST & WEBHOOKS', icon: <Terminal className="w-3.5 h-3.5" /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 py-3 px-4 font-mono text-xs tracking-wider border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-[#00A8FF] text-[#5BC9FF] bg-[#050B16]'
                  : 'border-transparent text-[#9AA7B8] hover:text-white'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto space-y-6 text-[#D9E1EA] font-mono text-xs leading-relaxed">
          {activeTab === 'ARCHITECTURE' && (
            <div className="space-y-4">
              <h4 className="font-headline text-base text-white">Autonomous Control Loop Pipeline</h4>
              <p className="text-[#C2CDD9]">
                AUREX runs an uninterrupted security control loop: from real-time AST code visitor inspection through LLM-assisted remediation and deterministic container validation.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-4">
                <div className="p-3 bg-[#050B16] border border-[#17406E]">
                  <span className="text-[#00A8FF] font-bold block mb-1">01 DETECTION</span>
                  <span className="text-[#9AA7B8] text-[11px]">Python `ast` AST parser + Shannon entropy regex scanners detect OWASP Top 10 vulnerabilities in milliseconds.</span>
                </div>
                <div className="p-3 bg-[#050B16] border border-[#17406E]">
                  <span className="text-[#007BFF] font-bold block mb-1">02 REMEDIATION</span>
                  <span className="text-[#9AA7B8] text-[11px]">Dual-engine patch pipeline: deterministic `NodeTransformer` rules backed by Google Gemini 1.5 Flash.</span>
                </div>
                <div className="p-3 bg-[#050B16] border border-[#17406E]">
                  <span className="text-[#00E699] font-bold block mb-1">03 VALIDATION</span>
                  <span className="text-[#9AA7B8] text-[11px]">Strict Docker sandbox isolation executes syntax verification, security re-scan, and policy threshold gating.</span>
                </div>
              </div>

              <div className="p-4 bg-[#050B16]/70 border border-[#17406E]">
                <span className="text-[#E4EBF3] font-bold block mb-2">Multi-Agent Orchestration Mesh</span>
                <p className="text-[#9AA7B8] text-[11px]">
                  Coordinated by <span className="text-[#00A8FF]">OrchestrationAgent</span> and <span className="text-[#5BC9FF]">ManagerAgent</span>, four specialized worker agents (<span className="text-[#D9E1EA]">ScannerAgent</span>, <span className="text-[#D9E1EA]">PatchAgent</span>, <span className="text-[#D9E1EA]">ValidatorAgent</span>, <span className="text-[#D9E1EA]">RiskAgent</span>) communicate asynchronously over an in-memory event mesh.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'RISK_ENGINE' && (
            <div className="space-y-4">
              <h4 className="font-headline text-base text-white">7-Factor Contextual Risk Mathematical Formulation</h4>
              <p className="text-[#C2CDD9]">
                Risk is computed dynamically per detected vulnerability using weighted dimensional analysis rather than static CVSS scores alone:
              </p>

              <div className="p-4 bg-[#020B1A] border border-[#17406E] text-[#5BC9FF]">
                <code>Risk_Score = ∑ (Factor_Weight_i × Raw_Score_i) × (1 - Confidence_Adjustment)</code>
              </div>

              <div className="space-y-2">
                {[
                  { factor: '01 Severity Factor', weight: '25%', formula: 'Critical: 10.0, High: 7.5, Med: 5.0, Low: 2.5' },
                  { factor: '02 Vulnerability Class (CWE)', weight: '20%', formula: 'RCE / Deserialization > Injection > Hardcoded Credential' },
                  { factor: '03 Sandbox Validation Result', weight: '15%', formula: 'Failed validation increases residual risk score by 1.5x' },
                  { factor: '04 Confidence Adjustment', weight: '10%', formula: 'Bayesian model feedback dampening false positives' },
                  { factor: '05 Target File Criticality', weight: '10%', formula: 'Core auth, payment gateways, and crypto modules weighted at 1.4x' },
                  { factor: '06 Environment Exposure', weight: '10%', formula: 'Public ingress routes vs internal background workers' },
                  { factor: '07 Policy Gate Violations', weight: '10%', formula: 'Direct breach of enterprise policy rules triggers immediate block' },
                ].map((f, i) => (
                  <div key={i} className="flex flex-col sm:flex-row sm:items-center justify-between p-2 bg-[#050B16] border border-[#17406E]/50">
                    <span className="text-[#E4EBF3] font-medium">{f.factor}</span>
                    <div className="flex items-center space-x-3 text-[11px]">
                      <span className="text-[#00A8FF]">WEIGHT: {f.weight}</span>
                      <span className="text-[#9AA7B8]">{f.formula}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'SANDBOX' && (
            <div className="space-y-4">
              <h4 className="font-headline text-base text-white">Hardened Container Runtime Architecture</h4>
              <p className="text-[#C2CDD9]">
                Untrusted code patches are never tested on the host system. All validation runs inside an ephemeral, locked-down Docker runtime with hard physical limits:
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-4">
                <div className="p-3 bg-[#050B16] border border-[#17406E] text-center">
                  <span className="text-[#9AA7B8] text-[10px] block">CPU QUOTA</span>
                  <span className="text-[#00A8FF] text-lg font-bold">0.5 CORE</span>
                </div>
                <div className="p-3 bg-[#050B16] border border-[#17406E] text-center">
                  <span className="text-[#9AA7B8] text-[10px] block">MEMORY LIMIT</span>
                  <span className="text-[#00A8FF] text-lg font-bold">128 MB</span>
                </div>
                <div className="p-3 bg-[#050B16] border border-[#17406E] text-center">
                  <span className="text-[#9AA7B8] text-[10px] block">NETWORK ACCESS</span>
                  <span className="text-[#FF1E2D] text-lg font-bold">DISABLED</span>
                </div>
                <div className="p-3 bg-[#050B16] border border-[#17406E] text-center">
                  <span className="text-[#9AA7B8] text-[10px] block">EXEC TIMEOUT</span>
                  <span className="text-[#00E699] text-lg font-bold">10.0 SEC</span>
                </div>
              </div>

              <div className="p-3 bg-[#050B16] border border-[#17406E] text-[11px] text-[#9AA7B8] space-y-1">
                <div><span className="text-[#00A8FF]">SECURITY FLAGS:</span> --pids-limit=32 --read-only --cap-drop=ALL --security-opt=no-new-privileges</div>
                <div><span className="text-[#00A8FF]">ISOLATION:</span> gVisor / runsc kernel syscall filtration sandbox compatible</div>
              </div>
            </div>
          )}

          {activeTab === 'API' && (
            <div className="space-y-4">
              <h4 className="font-headline text-base text-white">API Endpoints & GitHub Webhook Dispatcher</h4>
              <div className="space-y-2">
                {[
                  { method: 'POST', path: '/api/scan', desc: 'Accepts raw Python code snippet or repo file; returns AST syntax tree and CWE findings.' },
                  { method: 'POST', path: '/api/patch', desc: 'Runs dual-engine patcher generating unified diffs and AST-transformed safe code.' },
                  { method: 'POST', path: '/api/validate', desc: 'Submits patch to hardened container sandbox for execution and verification.' },
                  { method: 'GET', path: '/api/metrics', desc: 'Returns system-wide telemetry counters, scan rates, and risk distribution.' },
                  { method: 'GET', path: '/api/policy', desc: 'Fetches active organizational governance rules, blocked imports, and sanitizer mandates.' },
                  { method: 'GET', path: '/api/health', desc: 'Diagnostic health status of all 6 multi-agent security subsystems.' },
                  { method: 'POST', path: '/webhook', desc: 'GitHub App event handler for pull_request and check_run lifecycle integration.' }
                ].map((ep, i) => (
                  <div key={i} className="p-3 bg-[#050B16] border border-[#17406E] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${ep.method === 'POST' ? 'bg-[#007BFF]/20 text-[#00A8FF] border border-[#007BFF]/40' : 'bg-[#00E699]/20 text-[#00E699] border border-[#00E699]/40'}`}>
                        {ep.method}
                      </span>
                      <span className="text-white font-semibold">{ep.path}</span>
                    </div>
                    <span className="text-[#9AA7B8] text-[11px] max-w-md">{ep.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-[#17406E] bg-[#050B16]">
          <span className="font-mono text-[10px] text-[#9AA7B8]">AUTHENTICATED OPERATOR SPECIFICATION // RESTRICTED ACCESS</span>
          <CyberButton variant="secondary" size="sm" onClick={onClose}>
            CLOSE SPECIFICATION
          </CyberButton>
        </div>
      </div>
    </div>
  );
};
