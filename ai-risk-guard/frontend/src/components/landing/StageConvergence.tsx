import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { Shield, Sparkles, Activity, Layers, ArrowDown } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';

export const StageConvergence: React.FC<{ scrollProgress: number; onNavigate: (view: ViewId) => void }> = ({
  scrollProgress,
  onNavigate
}) => {
  const streams = [
    { label: 'AST Lines', code: 'AST_VECTORS', color: '#00CFFF', status: 'CONVERGED' },
    { label: 'Risk Threads', code: '7_FACTORS', color: '#087BFF', status: 'CONVERGED' },
    { label: 'Agent Connections', code: 'MESH_SYNC', color: '#65E7FF', status: 'CONVERGED' },
    { label: 'Patch Signals', code: 'TRANSFORMER_DIFF', color: '#00E699', status: 'INTEGRATED' },
    { label: 'Sandbox Validation', code: 'DOCKER_AIRGAP', color: '#00E699', status: 'VERIFIED' },
    { label: 'Policy Rings', code: 'GATE_04_LOCKED', color: '#B8C2CE', status: 'LOCKED' },
    { label: 'Telemetry Particles', code: 'TELEMETRY_BUS', color: '#00CFFF', status: 'SYNCHRONIZED' },
  ];

  return (
    <section className="relative py-20 px-4 sm:px-6 border-b border-[#1E3C5C]/40 bg-gradient-to-b from-transparent via-[#06101F]/30 to-transparent">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-[#06101F] border border-[#00CFFF]/50 font-mono text-[10px] text-[#00CFFF] tracking-widest">
            <Sparkles className="w-3.5 h-3.5 text-[#00CFFF] animate-pulse" />
            <span>FINAL CONVERGENCE // THREAD UNIFICATION</span>
          </div>

          <h2 className="font-headline font-black text-3xl sm:text-5xl text-white">
            All Intelligence Threads Converge
          </h2>

          <p className="font-mono text-xs sm:text-sm text-[#8D9AAA] leading-relaxed">
            Every isolated telemetry vector, agent decision, AST rewrite, and sandbox proof physically merges into the central geometric defense shield.
          </p>
        </div>

        {/* 7 Converging Streams Matrix */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 font-mono text-xs">
          {streams.map((s, idx) => (
            <div
              key={idx}
              className="p-3 bg-[#06101F]/80 border border-[#1E3C5C] space-y-1 relative group hover:border-[#00CFFF] transition-all"
            >
              <div
                className="absolute top-0 left-0 right-0 h-0.5"
                style={{ backgroundColor: s.color }}
              />
              <span className="text-[10px] text-[#8D9AAA] block">{s.code}</span>
              <span className="text-white font-semibold text-[11px] block">{s.label}</span>
              <span className="text-[9px] text-[#00E699] font-bold block">{s.status}</span>
            </div>
          ))}
        </div>

        {/* Convergence Vector Visual */}
        <div className="relative p-6 bg-[#030914] border border-[#1E3C5C] text-center font-mono text-xs text-[#8D9AAA] space-y-2">
          <div className="flex items-center justify-center space-x-2 text-[#65E7FF] font-semibold">
            <span>CONVERGENCE RATIO:</span>
            <span className="text-white font-bold">{Math.min(100, Math.round(scrollProgress * 105))}% COMPLETE</span>
          </div>
          <div className="w-full max-w-md mx-auto bg-[#06101F] h-2 border border-[#1E3C5C] overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#087BFF] via-[#00CFFF] to-[#65E7FF] transition-all duration-300"
              style={{ width: `${Math.min(100, scrollProgress * 100)}%` }}
            />
          </div>
          <p className="text-[10px] text-[#8D9AAA]">
            AUTONOMOUS SHIELD GEOMETRY REACHES FULL ASSEMBLED EQUILIBRIUM
          </p>
        </div>
      </div>
    </section>
  );
};
