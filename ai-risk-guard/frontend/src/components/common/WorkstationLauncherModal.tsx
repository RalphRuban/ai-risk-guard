import React from 'react';
import { ViewId, ViewMeta } from '../../types';
import { X, Lock, Terminal } from 'lucide-react';
import { TacticalBracket } from './TacticalBracket';
import { CyberButton } from './CyberButton';

interface WorkstationLauncherModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentView: ViewId;
  onSelectView: (view: ViewId) => void;
  isAuthenticated: boolean;
}

export const ALL_VIEWS: ViewMeta[] = [
  { id: 'landing', title: 'Landing / Command Center', code: 'VIEW-01', category: 'PUBLIC', protected: false, description: 'Autonomous cybersecurity command center with 3D tactical shield & scroll convergence.' },
  { id: 'login', title: 'GitHub Auth Gateway', code: 'VIEW-02', category: 'PUBLIC', protected: false, description: 'Enterprise single-provider GitHub OAuth clearance and session initialization.' },
  { id: 'signup', title: 'GitHub Onboarding Clearance', code: 'VIEW-03', category: 'PUBLIC', protected: false, description: 'Organization security clearance setup and repository binding.' },
  { id: 'dashboard', title: 'Enterprise Security Dashboard', code: 'VIEW-04', category: 'CORE', protected: true, description: 'High-density posture monitoring, risk distribution, and agent interventions.' },
  { id: 'repositories', title: 'Protected Repository Inventory', code: 'VIEW-05', category: 'CORE', protected: true, description: 'Monitored repository status matrix with active AST PR gates.' },
  { id: 'scanner', title: 'Live AST Vulnerability Scanner', code: 'VIEW-06', category: 'ENGINES', protected: true, description: 'Interactive Python AST parser & Shannon entropy detector with live test suites.' },
  { id: 'findings', title: 'Vulnerability Findings Matrix', code: 'VIEW-07', category: 'CORE', protected: true, description: 'Comprehensive inventory of AST vulnerabilities, CWE ratings, and file coordinates.' },
  { id: 'patch', title: 'Automated Code Remediation', code: 'VIEW-08', category: 'ENGINES', protected: true, description: 'Dual-engine AST NodeTransformer and LLM patch review workstation with unified diff.' },
  { id: 'sandbox', title: 'Hardened Sandbox Validation', code: 'VIEW-09', category: 'ENGINES', protected: true, description: 'Containerized validation runtime with 0.5 CPU, 128MB RAM, and zero network access.' },
  { id: 'policy', title: 'Governance & Security Policy', code: 'VIEW-10', category: 'GOVERNANCE', protected: true, description: 'Rule definitions, blocked modules/functions, mandatory sanitizers, and risk limits.' },
  { id: 'risk', title: '7-Factor Risk Intelligence', code: 'VIEW-11', category: 'ENGINES', protected: true, description: 'Mathematical breakdown of the 7-factor weighted contextual risk formulation.' },
  { id: 'telemetry', title: 'Time-Series Security Telemetry', code: 'VIEW-12', category: 'CORE', protected: true, description: 'Real-time telemetry stream, scan frequency trends, and anomaly radar.' },
  { id: 'agents', title: 'Multi-Agent Mesh Architecture', code: 'VIEW-13', category: 'SYSTEM', protected: true, description: 'Interactive topological view of all six cooperating autonomous security agents.' },
  { id: 'reports', title: 'Security Reports Hub', code: 'VIEW-14', category: 'GOVERNANCE', protected: true, description: 'Executive audit reports, compliance certifications, and security grading.' },
  { id: 'report-detail', title: 'Executive Report Detail & Export', code: 'VIEW-15', category: 'GOVERNANCE', protected: true, description: 'Detailed cryptographic audit record with JSON and printable export options.' },
  { id: 'github', title: 'GitHub App & Webhook Ingestion', code: 'VIEW-16', category: 'SYSTEM', protected: true, description: 'Live webhook dispatch listener, PR status checks, and integration health.' },
  { id: 'settings', title: 'Enterprise Operator Settings', code: 'VIEW-17', category: 'SYSTEM', protected: true, description: 'Security thresholds, audit logging levels, and container sandbox configurations.' },
  { id: 'status', title: 'System Health & Runtime Telemetry', code: 'VIEW-18', category: 'SYSTEM', protected: true, description: 'Subsystem diagnostics for Orchestrator, Scanner, Policy Engine, and Sandbox.' },
];

export const WorkstationLauncherModal: React.FC<WorkstationLauncherModalProps> = ({
  isOpen,
  onClose,
  currentView,
  onSelectView,
  isAuthenticated
}) => {
  const [filterCategory, setFilterCategory] = React.useState<string>('ALL');

  if (!isOpen) return null;

  const categories = ['ALL', 'CORE', 'ENGINES', 'GOVERNANCE', 'SYSTEM', 'PUBLIC'];

  const filteredViews = ALL_VIEWS.filter(
    (v) => filterCategory === 'ALL' || v.category === filterCategory
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-[#020B1A]/90 backdrop-blur-xl animate-fadeIn">
      <div className="relative w-full max-w-5xl max-h-[90vh] flex flex-col bg-[#050B16] border border-[#17406E] shadow-[0_0_60px_rgba(0,123,255,0.25)]">
        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-[#EAF1F8]/85 to-transparent pointer-events-none shadow-[0_2px_12px_rgba(217,225,234,0.25)]" />
        <TacticalBracket color="#00A8FF" size="lg" />

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#17406E] bg-[#050B16]">
          <div className="flex items-center space-x-3">
            <Terminal className="w-5 h-5 text-[#00A8FF]" />
            <div>
              <h3 className="font-headline text-lg text-white">Workstation Launcher — 18 Integrated Views</h3>
              <p className="font-mono text-[10px] text-[#9AA7B8]">AUTONOMOUS DEFENSE PLATFORM NAVIGATION MATRIX</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#9AA7B8] hover:text-white hover:bg-[#0B2A5E] transition-colors border border-transparent hover:border-[#17406E]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center space-x-2 border-b border-[#17406E] bg-[#050B16] px-6 py-3 overflow-x-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3 py-1 font-mono text-[11px] tracking-wider transition-all border ${
                filterCategory === cat
                  ? 'bg-[#007BFF]/30 border-[#D9E1EA]/80 text-[#EAF1F8] shadow-[0_0_12px_rgba(217,225,234,0.25)]'
                  : 'bg-transparent border-[#17406E]/60 text-[#9AA7B8] hover:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Workstations Grid */}
        <div className="p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredViews.map((view) => {
            const isCurrent = currentView === view.id;
            const isLocked = view.protected && !isAuthenticated;

            return (
              <div
                key={view.id}
                onClick={() => {
                  onSelectView(view.id);
                  onClose();
                }}
                className={`group relative p-4 border transition-all cursor-pointer ${
                  isCurrent
                    ? 'bg-[#007BFF]/20 border-[#D9E1EA]/80 shadow-[0_0_20px_rgba(217,225,234,0.25)]'
                    : isLocked
                    ? 'bg-[#050B16]/40 border-[#17406E]/50 hover:border-[#FF1E2D]/60'
                    : 'bg-[#050B16]/70 border-[#17406E] hover:border-[#00A8FF]/60 hover:bg-[#0B2A5E] hover:shadow-[0_0_16px_rgba(217,225,234,0.15)]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[10px] text-[#00A8FF] tracking-widest">{view.code}</span>
                  <div className="flex items-center space-x-1.5">
                    <span className="text-[9px] font-mono px-1.5 py-0.5 bg-[#050B16] border border-[#17406E] text-[#9AA7B8]">
                      {view.category}
                    </span>
                    {isLocked ? (
                      <Lock className="w-3.5 h-3.5 text-[#FF1E2D]" />
                    ) : isCurrent ? (
                      <span className="w-2 h-2 rounded-full bg-[#00E699] animate-pulse" />
                    ) : null}
                  </div>
                </div>

                <h4 className="font-headline text-sm text-white mb-1.5 group-hover:text-[#5BC9FF] transition-colors">
                  {view.title}
                </h4>

                <p className="font-mono text-[11px] text-[#9AA7B8] line-clamp-2 leading-relaxed">
                  {view.description}
                </p>

                {isLocked && (
                  <div className="mt-2 text-[10px] font-mono text-[#FF1E2D] flex items-center space-x-1">
                    <span>* Requires GitHub Clearance</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-[#17406E] bg-[#050B16]">
          <div className="font-mono text-[11px] text-[#9AA7B8] flex items-center space-x-2">
            <span>OPERATOR STATE:</span>
            <span className={isAuthenticated ? 'text-[#00E699]' : 'text-[#FF1E2D]'}>
              {isAuthenticated ? 'AUTHENTICATED (@octocat-secops)' : 'UNAUTHENTICATED (PUBLIC VISITOR)'}
            </span>
          </div>
          <CyberButton variant="secondary" size="sm" onClick={onClose}>
            CLOSE LAUNCHER
          </CyberButton>
        </div>
      </div>
    </div>
  );
};
