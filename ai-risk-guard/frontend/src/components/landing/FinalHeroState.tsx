import React from 'react';
import { TacticalShield3D } from '../3d/TacticalShield3D';
import { CADControls } from '../common/CADControls';
import { ShieldCADState } from '../../types';
import { Shield, CheckCircle2, Lock, Cpu, Terminal, Compass } from 'lucide-react';

interface FinalHeroStateProps {
  cadState: ShieldCADState;
  onCADChange: (updates: Partial<ShieldCADState>) => void;
}

export const FinalHeroState: React.FC<FinalHeroStateProps> = ({ cadState, onCADChange }) => {
  const systemStates = [
    { label: 'DETECTION', code: 'AST_ACTIVE', status: 'SYNCHRONIZED', desc: 'Continuous Python parser' },
    { label: 'RISK', code: '7_FACTORS', status: 'CALIBRATED', desc: 'Real-time contextual scoring' },
    { label: 'REMEDIATION', code: 'DUAL_ENGINE', status: 'ARMED', desc: 'NodeTransformer + Gemini' },
    { label: 'VALIDATION', code: 'DOCKER_AIRGAP', status: 'VERIFIED', desc: '128MB isolated runtime' },
    { label: 'POLICY', code: 'GATE_LOCKED', status: 'ENFORCED', desc: 'Zero unauthenticated egress' },
  ];

  return (
    <section className="relative py-24 px-4 sm:px-6 border-b border-[#1E3C5C]/40 bg-[#02050B]">
      <div className="max-w-7xl mx-auto space-y-12">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-[#06101F] border border-[#00CFFF]/40 text-[#00CFFF] font-mono text-[10px] tracking-widest">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E699] animate-pulse" />
            <span>SYSTEM ONLINE // DEFENSE CORE ACTIVE</span>
          </div>
          <h2 className="font-headline font-black text-3xl sm:text-5xl text-white tracking-wide">
            AUREX
          </h2>
          <p className="font-mono text-sm sm:text-base text-[#65E7FF] tracking-widest uppercase">
            Autonomous Defense Shield Assembled
          </p>
        </div>

        {/* Central Assembled Shield Showcase with Surrounding 5 System States */}
        <div className="relative grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left States: Detection & Risk */}
          <div className="lg:col-span-3 space-y-4 order-2 lg:order-1 font-mono text-xs">
            {systemStates.slice(0, 2).map((st) => (
              <div
                key={st.label}
                className="p-4 bg-[#06101F]/90 border border-[#1E3C5C] shadow-lg space-y-1 relative group hover:border-[#00CFFF] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-white font-headline font-bold text-sm">{st.label}</span>
                  <span className="text-[10px] text-[#00E699] font-bold">{st.status}</span>
                </div>
                <div className="text-[10px] text-[#00CFFF]">{st.code}</div>
                <div className="text-[#8D9AAA] text-[11px]">{st.desc}</div>
              </div>
            ))}
          </div>

          {/* Center 3D Fully Assembled Shield Stage (6 cols) */}
          <div className="lg:col-span-6 relative min-h-[560px] sm:min-h-[640px] flex flex-col items-center justify-center order-1 lg:order-2">
            <div className="absolute top-0 right-0 z-20">
              <CADControls state={cadState} onChange={onCADChange} />
            </div>

            <TacticalShield3D
              scrollProgress={1.0}
              cadState={{ ...cadState, assemblyStage: 7 }}
              onCADChange={onCADChange}
              className="h-[560px] sm:h-[640px]"
            />
          </div>

          {/* Right States: Remediation, Validation & Policy */}
          <div className="lg:col-span-3 space-y-4 order-3 font-mono text-xs">
            {systemStates.slice(2).map((st) => (
              <div
                key={st.label}
                className="p-4 bg-[#06101F]/90 border border-[#1E3C5C] shadow-lg space-y-1 relative group hover:border-[#00CFFF] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-white font-headline font-bold text-sm">{st.label}</span>
                  <span className="text-[10px] text-[#00E699] font-bold">{st.status}</span>
                </div>
                <div className="text-[10px] text-[#00CFFF]">{st.code}</div>
                <div className="text-[#8D9AAA] text-[11px]">{st.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
