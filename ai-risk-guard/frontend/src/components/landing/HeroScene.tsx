import React from 'react';
import { Terminal } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';
import { CADControls } from '../common/CADControls';
import { TacticalShield3D } from '../3d/TacticalShield3D';
import { AurexLogo } from '../common/AurexLogo';
import ScrambledText from '../bits/TextAnimations/ScrambledText/ScrambledText';
import CountUp from '../bits/TextAnimations/CountUp/CountUp';
import SpecularButton from '../bits/Components/SpecularButton/SpecularButton';
import { ShieldCADState, ViewId } from '../../types';

interface HeroSceneProps {
  onNavigate: (view: ViewId) => void;
  scrollProgress: number;
  cadState: ShieldCADState;
  onCADChange: (updates: Partial<ShieldCADState>) => void;
}

export const HeroScene: React.FC<HeroSceneProps> = ({
  onNavigate,
  scrollProgress,
  cadState,
  onCADChange
}) => {
  return (
    <section className="relative min-h-[94vh] flex flex-col justify-center px-4 sm:px-8 xl:px-12 py-10 sm:py-16 border-b-2 border-[#17406E]/50">
      <div className="max-w-[1760px] mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-16 items-center">
        {/* Left 6 Columns: Narrative & Authority */}
        <div className="lg:col-span-6 space-y-7 z-10">
          {/* Status Badge */}
          <div className="inline-flex items-center space-x-2.5 px-4 py-1.5 rounded-full bg-[#071A2E]/90 backdrop-blur-xl border border-[#D9E1EA]/35 text-[11px] font-mono tracking-widest text-[#DEE7F0] shadow-[0_0_15px_rgba(217,225,234,0.12)]">
            <span className="w-2 h-2 rounded-full bg-[#00A8FF] animate-ping" />
            <span className="font-semibold text-[#00A8FF]">AUREX DEFENSE CORE</span>
            <span className="text-[#76879D]">//</span>
            <span className="font-semibold">v2.4.0 AIRGAPPED RUNTIME</span>
          </div>

          {/* Hero Headline (Scaled Up) */}
          <div className="space-y-4">
            <h1 className="font-headline font-black text-4xl sm:text-6xl lg:text-7xl text-[#EAF1F8] tracking-wider leading-[1.08] drop-shadow-[0_4px_25px_rgba(2,11,26,0.95)]">
              AUREX <br />
              <ScrambledText className="inline-block text-transparent bg-clip-text bg-gradient-to-r from-[#00A8FF] via-[#00A8FF] to-[#D9E1EA]">
                CYBER DEFENSE
              </ScrambledText>
            </h1>
            <p className="font-mono text-xs sm:text-base tracking-widest uppercase text-[#D9E1EA] font-semibold">
              ENTERPRISE COMMAND CONSOLE // AIRGAPPED CONTAINER EXECUTION
            </p>
          </div>

          {/* Tactical Telemetry Chips */}
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] py-1">
            <span className="px-3 py-1 rounded bg-[#071A2E]/80 backdrop-blur-md border border-[#17406E] text-[#D9E1EA] shadow-[0_0_10px_rgba(217,225,234,0.05)]">
              CODE-LEVEL SYNTHESIS
            </span>
            <span className="px-3 py-1 rounded bg-[#071A2E]/80 backdrop-blur-md border border-[#FF1E2D]/40 text-[#FF1E2D] shadow-[0_0_10px_rgba(255,30,45,0.15)]">
              128MB AIRGAP ISOLATION
            </span>
            <span className="px-3 py-1 rounded bg-[#071A2E]/80 backdrop-blur-md border border-[#17406E] text-[#DEE7F0] shadow-[0_0_10px_rgba(217,225,234,0.05)]">
              ZERO RUNTIME EGRESS
            </span>
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
            <SpecularButton
              size="lg"
              radius={12}
              tint="#00A8FF"
              tintOpacity={0.1}
              blur={6}
              textColor="#EAF1F8"
              lineColor="#00A8FF"
              baseColor="#1248A8"
              autoAnimate
              proximity={360}
              onClick={() => onNavigate('dashboard')}
              className="font-mono uppercase tracking-wider"
            >
              <span className="inline-flex items-center gap-2.5">
                <AurexLogo size={18} withGlow={false} />
                ENTER SECURITY CONSOLE
              </span>
            </SpecularButton>

            <CyberButton
              variant="secondary"
              size="lg"
              icon={<Terminal className="w-4 h-4 text-[#D9E1EA]" />}
              onClick={() => onNavigate('scanner')}
            >
              RUN AST SCAN
            </CyberButton>
          </div>

          {/* Live Telemetry Counters with Glassmorphic Floating Panel (80% Navy, 10% Silver, 10% Red) */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t-2 border-[#17406E]/50 font-mono text-[11px]">
            <div className="p-4 rounded-lg bg-gradient-to-b from-[#0B2A5E]/85 to-[#050B16]/95 backdrop-blur-xl border-2 border-[#17406E] shadow-[0_6px_25px_rgba(2,11,26,0.7)] hover:border-[#D9E1EA]/60 transition-colors">
              <span className="text-[#A7B4C4] block text-[10px] tracking-wider uppercase font-semibold">PROTECTED REPOS</span>
              <span className="text-white font-headline font-bold text-lg sm:text-xl tracking-wide">
                <CountUp to={128} separator="," /> ACTIVE
              </span>
            </div>
            <div className="p-4 rounded-lg bg-gradient-to-b from-[#0B2A5E]/85 to-[#050B16]/95 backdrop-blur-xl border-2 border-[#17406E] shadow-[0_6px_25px_rgba(2,11,26,0.7)] hover:border-[#FF1E2D]/60 transition-colors">
              <span className="text-[#A7B4C4] block text-[10px] tracking-wider uppercase font-semibold">AST SCANS</span>
              <span className="text-[#FF1E2D] font-headline font-bold text-lg sm:text-xl tracking-wide">
                <CountUp to={4682} separator="," /> RUNS
              </span>
            </div>
            <div className="p-4 rounded-lg bg-gradient-to-b from-[#0B2A5E]/85 to-[#050B16]/95 backdrop-blur-xl border-2 border-[#17406E] shadow-[0_6px_25px_rgba(2,11,26,0.7)] hover:border-[#D9E1EA]/60 transition-colors">
              <span className="text-[#A7B4C4] block text-[10px] tracking-wider uppercase font-semibold">AUTO-PATCH PASS</span>
              <span className="text-[#D9E1EA] font-headline font-bold text-lg sm:text-xl tracking-wide">
                <CountUp to={94.2} separator="," />% PASS
              </span>
            </div>
          </div>
        </div>

        {/* Right 6 Columns: 3D Procedural Shield Stage + CAD Controls (Expanded Scale) */}
        <div className="lg:col-span-6 relative flex flex-col items-center justify-center min-h-[460px] sm:min-h-[540px] lg:min-h-[620px]">
          {/* CAD Controls Floating Bar */}
          <div className="absolute top-2 right-2 z-20">
            <CADControls state={cadState} onChange={onCADChange} />
          </div>

          {/* 3D Shield Canvas */}
          <div className="w-full h-full relative flex items-center justify-center">
            <TacticalShield3D
              scrollProgress={scrollProgress}
              cadState={cadState}
              onCADChange={onCADChange}
              className="h-[460px] sm:h-[540px] lg:h-[620px]"
            />
          </div>

          {/* Convergence Callout */}
          <div className="absolute bottom-2 left-2 z-20 font-mono text-[10px] text-[#D9E1EA] bg-[#050B16]/85 px-2.5 py-1 border border-[#17406E] flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-[#FF1E2D] animate-ping" />
            <span>SCROLL DOWN TO INSPECT WORKSTATIONS</span>
          </div>
        </div>
      </div>
    </section>
  );
};
