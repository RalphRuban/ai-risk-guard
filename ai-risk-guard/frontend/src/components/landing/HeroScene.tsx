import React from 'react';
import { Shield, ArrowRight, Terminal, Activity, Cpu, Lock } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';
import { CADControls } from '../common/CADControls';
import { TacticalShield3D } from '../3d/TacticalShield3D';
import { AurexLogo } from '../common/AurexLogo';
import { ShieldCADState, ViewId } from '../../types';

interface HeroSceneProps {
  onNavigate: (view: ViewId) => void;
  scrollProgress: number;
  cadState: ShieldCADState;
  onCADChange: (updates: Partial<ShieldCADState>) => void;
  onOpenDocs: () => void;
}

export const HeroScene: React.FC<HeroSceneProps> = ({
  onNavigate,
  scrollProgress,
  cadState,
  onCADChange,
  onOpenDocs
}) => {
  return (
    <section className="relative min-h-[94vh] flex flex-col justify-center px-4 sm:px-8 xl:px-12 py-10 sm:py-16 border-b-2 border-[#184384]/50">
      <div className="max-w-[1760px] mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-16 items-center">
        {/* Left 6 Columns: Narrative & Authority */}
        <div className="lg:col-span-6 space-y-7 z-10">
          {/* Status Badge */}
          <div className="inline-flex items-center space-x-2.5 px-4 py-1.5 rounded-full bg-[#061533]/90 backdrop-blur-xl border border-[#CBD5E1]/35 text-[11px] font-mono tracking-widest text-[#E2E8F0] shadow-[0_0_15px_rgba(203,213,225,0.12)]">
            <span className="w-2 h-2 rounded-full bg-[#00CFFF] animate-ping" />
            <span className="font-semibold text-[#00CFFF]">AUREX DEFENSE CORE</span>
            <span className="text-[#64748B]">//</span>
            <span className="font-semibold">v2.4.0 AIRGAPPED RUNTIME</span>
          </div>

          {/* Hero Headline (Scaled Up) */}
          <div className="space-y-4">
            <h1 className="font-headline font-black text-4xl sm:text-6xl lg:text-7xl text-[#F8FAFC] tracking-wider leading-[1.08] drop-shadow-[0_4px_25px_rgba(2,7,22,0.95)]">
              AUREX <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00CFFF] via-[#0077FE] to-[#CBD5E1]">
                CYBER DEFENSE
              </span>
            </h1>
            <p className="font-mono text-xs sm:text-base tracking-widest uppercase text-[#CBD5E1] font-semibold">
              ENTERPRISE COMMAND CONSOLE // AIRGAPPED CONTAINER EXECUTION
            </p>
          </div>

          {/* Tactical Telemetry Chips */}
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] py-1">
            <span className="px-3 py-1 rounded bg-[#061533]/80 backdrop-blur-md border border-[#184384] text-[#CBD5E1] shadow-[0_0_10px_rgba(203,213,225,0.05)]">
              CODE-LEVEL SYNTHESIS
            </span>
            <span className="px-3 py-1 rounded bg-[#061533]/80 backdrop-blur-md border border-[#FF2A4B]/40 text-[#FF2A4B] shadow-[0_0_10px_rgba(255,42,75,0.15)]">
              128MB AIRGAP ISOLATION
            </span>
            <span className="px-3 py-1 rounded bg-[#061533]/80 backdrop-blur-md border border-[#184384] text-[#E2E8F0] shadow-[0_0_10px_rgba(203,213,225,0.05)]">
              ZERO RUNTIME EGRESS
            </span>
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
            <CyberButton
              variant="primary"
              size="lg"
              icon={<AurexLogo size={18} withGlow={false} />}
              onClick={() => onNavigate('dashboard')}
            >
              ENTER SECURITY CONSOLE
            </CyberButton>

            <CyberButton
              variant="secondary"
              size="lg"
              icon={<Terminal className="w-4 h-4 text-[#CBD5E1]" />}
              onClick={() => onNavigate('scanner')}
            >
              RUN AST SCAN
            </CyberButton>
          </div>

          {/* Live Telemetry Counters with Glassmorphic Floating Panel (80% Navy, 10% Silver, 10% Red) */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t-2 border-[#184384]/50 font-mono text-[11px]">
            <div className="p-4 rounded-lg bg-gradient-to-b from-[#0B2556]/85 to-[#030C22]/95 backdrop-blur-xl border-2 border-[#184384] shadow-[0_6px_25px_rgba(2,7,22,0.7)] hover:border-[#CBD5E1]/60 transition-colors">
              <span className="text-[#94A3B8] block text-[10px] tracking-wider uppercase font-semibold">PROTECTED REPOS</span>
              <span className="text-white font-headline font-bold text-lg sm:text-xl tracking-wide">128 ACTIVE</span>
            </div>
            <div className="p-4 rounded-lg bg-gradient-to-b from-[#0B2556]/85 to-[#030C22]/95 backdrop-blur-xl border-2 border-[#184384] shadow-[0_6px_25px_rgba(2,7,22,0.7)] hover:border-[#FF2A4B]/60 transition-colors">
              <span className="text-[#94A3B8] block text-[10px] tracking-wider uppercase font-semibold">AST SCANS</span>
              <span className="text-[#FF2A4B] font-headline font-bold text-lg sm:text-xl tracking-wide">4,682 RUNS</span>
            </div>
            <div className="p-4 rounded-lg bg-gradient-to-b from-[#0B2556]/85 to-[#030C22]/95 backdrop-blur-xl border-2 border-[#184384] shadow-[0_6px_25px_rgba(2,7,22,0.7)] hover:border-[#CBD5E1]/60 transition-colors">
              <span className="text-[#94A3B8] block text-[10px] tracking-wider uppercase font-semibold">AUTO-PATCH PASS</span>
              <span className="text-[#CBD5E1] font-headline font-bold text-lg sm:text-xl tracking-wide">94.2% PASS</span>
            </div>
          </div>
        </div>

        {/* Right 6 Columns: 3D Procedural Shield Stage + CAD Controls (Expanded Scale) */}
        <div className="lg:col-span-6 relative flex flex-col items-center justify-center min-h-[620px] sm:min-h-[720px] lg:min-h-[820px]">
          {/* CAD Controls Floating Bar */}
          <div className="absolute top-0 right-0 z-20">
            <CADControls state={cadState} onChange={onCADChange} />
          </div>

          {/* 3D Shield Canvas */}
          <div className="w-full h-full relative flex items-center justify-center">
            <TacticalShield3D
              scrollProgress={scrollProgress}
              cadState={cadState}
              onCADChange={onCADChange}
              className="h-[620px] sm:h-[720px] lg:h-[820px]"
            />
          </div>

          {/* Convergence Callout */}
          <div className="absolute bottom-2 left-2 z-20 font-mono text-[10px] text-[#CBD5E1] bg-[#030C22]/85 px-2.5 py-1 border border-[#184384] flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-[#FF2A4B] animate-ping" />
            <span>SCROLL DOWN TO INSPECT WORKSTATIONS</span>
          </div>
        </div>
      </div>
    </section>
  );
};
