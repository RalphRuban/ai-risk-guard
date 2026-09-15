import React from 'react';
import { ViewId } from '../../types';
import { Shield, Terminal, Lock, Github, Activity, ArrowUpRight } from 'lucide-react';
import { HangingGlassCard } from '../common/HangingGlassCard';

interface WorkstationMatrixStripProps {
  onNavigate: (view: ViewId) => void;
}

export const WorkstationMatrixStrip: React.FC<WorkstationMatrixStripProps> = ({ onNavigate }) => {
  const cards = [
    { id: 'dashboard' as ViewId, code: 'VIEW-04', title: 'Enterprise Dashboard', desc: 'Real-time telemetry, risk severity doughnuts, and active PR gates.', icon: <Activity className="w-4 h-4 text-[#FF1E2D]" />, status: 'REAL-TIME', glow: 'threat' as const },
    { id: 'findings' as ViewId, code: 'VIEW-07', title: 'Scan Findings Matrix', desc: 'Per-scan vulnerability inventory with severity ratings, file coordinates, and feedback.', icon: <Terminal className="w-4 h-4 text-[#D9E1EA]" />, status: 'LIVE SCANS', glow: 'cyan' as const },
    { id: 'risk' as ViewId, code: 'VIEW-11', title: '7-Factor Risk Engine', desc: 'Weighted contextual risk formulation derived from live dashboard aggregates.', icon: <Shield className="w-4 h-4 text-[#FF1E2D]" />, status: 'COMPUTED', glow: 'threat' as const },
    { id: 'policy' as ViewId, code: 'VIEW-10', title: 'Governance Gateway', desc: 'Banned sinks, mandatory sanitizers, and PR risk thresholds.', icon: <Lock className="w-4 h-4 text-[#FF1E2D]" />, status: 'GATE LOCKED', glow: 'threat' as const },
    { id: 'github' as ViewId, code: 'VIEW-16', title: 'GitHub App & Scan Activity', desc: 'Webhook dispatch listener, PR status checks, and installation health.', icon: <Github className="w-4 h-4 text-[#D9E1EA]" />, status: 'INGESTION', glow: 'cyan' as const },
    { id: 'status' as ViewId, code: 'VIEW-18', title: 'System Health', desc: 'Diagnostic telemetry for distributed security subsystems.', icon: <Shield className="w-4 h-4 text-[#D9E1EA]" />, status: 'LIVE PROBES', glow: 'cyan' as const },
  ];

  return (
    <section className="relative pt-20 pb-16 px-4 sm:px-8 xl:px-12 max-w-[1760px] mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b-2 border-[#17406E]/60 font-mono text-xs gap-3">
        <div className="flex items-center space-x-3">
          <span className="w-2.5 h-2.5 rounded-full bg-[#FF1E2D] animate-ping" />
          <span className="text-[#EAF1F8] text-sm sm:text-base tracking-widest uppercase font-headline font-bold">
            OPERATIONAL WORKSTATIONS // FLOATING MATRIX
          </span>
        </div>
        <div className="flex items-center space-x-3 text-[11px] text-[#A7B4C4]">
          <span>SECURITY CHASSIS // ALL 14 VIEWPORTS ACTIVE</span>
          <span className="px-2 py-0.5 rounded bg-[#0B2A5E] border border-[#D9E1EA]/30 text-[#D9E1EA] font-bold">AIRGAP MESH</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 pt-4">
        {cards.map((card, idx) => (
          <HangingGlassCard
            key={card.id}
            hanging={true}
            floatingDelay={idx % 2 !== 0}
            glowColor={card.glow}
            onClick={() => onNavigate(card.id)}
          >
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between font-mono text-xs">
                <div className="flex items-center space-x-2">
                  <div className="p-1.5 rounded bg-[#050B16] border border-[#17406E]">
                    {card.icon}
                  </div>
                  <span className="text-[#D9E1EA] text-[11px] tracking-widest font-bold">{card.code}</span>
                </div>
                <span className="text-[10px] text-[#EAF1F8] px-2 py-0.5 rounded bg-[#071A2E] border border-[#D9E1EA]/30 shadow-[0_0_10px_rgba(217,225,234,0.1)]">
                  {card.status}
                </span>
              </div>

              <div className="flex items-center justify-between pt-1">
                <h3 className="font-headline font-bold text-sm tracking-wide text-white group-hover:text-[#FF1E2D] transition-colors">
                  {card.title}
                </h3>
                <ArrowUpRight className="w-4 h-4 text-[#A7B4C4] group-hover:text-[#FF1E2D] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
              </div>

              <p className="font-mono text-[11px] text-[#A7B4C4] leading-relaxed line-clamp-2">
                {card.desc}
              </p>
            </div>
          </HangingGlassCard>
        ))}
      </div>
    </section>
  );
};
