import React from 'react';
import { ViewId } from '../../types';
import { Shield, Terminal, Wrench, Box, Lock, Activity, ArrowUpRight } from 'lucide-react';
import { HangingGlassCard } from '../common/HangingGlassCard';

interface WorkstationMatrixStripProps {
  onNavigate: (view: ViewId) => void;
}

export const WorkstationMatrixStrip: React.FC<WorkstationMatrixStripProps> = ({ onNavigate }) => {
  const cards = [
    { id: 'dashboard' as ViewId, code: 'VIEW-04', title: 'Enterprise Dashboard', desc: 'Real-time telemetry, risk severity doughnuts, and active PR gates.', icon: <Activity className="w-4 h-4 text-[#FF2A4B]" />, status: '128 REPOS', glow: 'threat' as const },
    { id: 'scanner' as ViewId, code: 'VIEW-06', title: 'Live AST Scanner', desc: 'Python compiler parsing, syntax trees, and Shannon entropy analysis.', icon: <Terminal className="w-4 h-4 text-[#CBD5E1]" />, status: '240MS AVG', glow: 'cyan' as const },
    { id: 'patch' as ViewId, code: 'VIEW-08', title: 'AST Remediation', desc: 'Deterministic NodeTransformer rules & multi-candidate patch diffs.', icon: <Wrench className="w-4 h-4 text-[#FF2A4B]" />, status: 'AUTO-REWRITE', glow: 'threat' as const },
    { id: 'sandbox' as ViewId, code: 'VIEW-09', title: 'Hardened Sandbox', desc: 'Airgapped 128MB container isolation with zero network transport.', icon: <Box className="w-4 h-4 text-[#CBD5E1]" />, status: '0.5 CPU', glow: 'cyan' as const },
    { id: 'policy' as ViewId, code: 'VIEW-10', title: 'Governance Gateway', desc: 'Banned sinks, mandatory sanitizers, and PR risk thresholds.', icon: <Lock className="w-4 h-4 text-[#FF2A4B]" />, status: 'GATE LOCKED', glow: 'threat' as const },
    { id: 'status' as ViewId, code: 'VIEW-18', title: 'System Health', desc: 'Diagnostic telemetry for 6 distributed security subsystems.', icon: <Shield className="w-4 h-4 text-[#CBD5E1]" />, status: '100% HEALTHY', glow: 'cyan' as const },
  ];

  return (
    <section className="relative pt-20 pb-16 px-4 sm:px-8 xl:px-12 max-w-[1760px] mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b-2 border-[#184384]/60 font-mono text-xs gap-3">
        <div className="flex items-center space-x-3">
          <span className="w-2.5 h-2.5 rounded-full bg-[#FF2A4B] animate-ping" />
          <span className="text-[#F8FAFC] text-sm sm:text-base tracking-widest uppercase font-headline font-bold">
            OPERATIONAL WORKSTATIONS // FLOATING MATRIX
          </span>
        </div>
        <div className="flex items-center space-x-3 text-[11px] text-[#94A3B8]">
          <span>SECURITY CHASSIS // ALL 18 VIEWPORTS ACTIVE</span>
          <span className="px-2 py-0.5 rounded bg-[#0B2556] border border-[#CBD5E1]/30 text-[#CBD5E1] font-bold">AIRGAP MESH</span>
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
                  <div className="p-1.5 rounded bg-[#030C22] border border-[#184384]">
                    {card.icon}
                  </div>
                  <span className="text-[#CBD5E1] text-[11px] tracking-widest font-bold">{card.code}</span>
                </div>
                <span className="text-[10px] text-[#F8FAFC] px-2 py-0.5 rounded bg-[#061533] border border-[#CBD5E1]/30 shadow-[0_0_10px_rgba(203,213,225,0.1)]">
                  {card.status}
                </span>
              </div>

              <div className="flex items-center justify-between pt-1">
                <h3 className="font-headline font-bold text-sm tracking-wide text-white group-hover:text-[#FF2A4B] transition-colors">
                  {card.title}
                </h3>
                <ArrowUpRight className="w-4 h-4 text-[#94A3B8] group-hover:text-[#FF2A4B] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
              </div>

              <p className="font-mono text-[11px] text-[#94A3B8] leading-relaxed line-clamp-2">
                {card.desc}
              </p>
            </div>
          </HangingGlassCard>
        ))}
      </div>
    </section>
  );
};
