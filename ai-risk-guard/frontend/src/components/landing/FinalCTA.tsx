import React from 'react';
import { BookOpen } from 'lucide-react';
import { CyberButton } from '../common/CyberButton';
import { AurexLogo } from '../common/AurexLogo';
import { ViewId } from '../../types';
import { TacticalBracket } from '../common/TacticalBracket';

interface FinalCTAProps {
  onNavigate: (view: ViewId) => void;
  onOpenDocs: () => void;
}

export const FinalCTA: React.FC<FinalCTAProps> = ({ onNavigate, onOpenDocs }) => {
  return (
    <section className="relative py-28 px-4 sm:px-8 xl:px-12">
      <div className="max-w-[1500px] mx-auto text-center relative p-8 sm:p-16 rounded-2xl bg-gradient-to-br from-[#0B2A5E]/85 via-[#071A2E]/92 to-[#020B1A]/98 backdrop-blur-2xl border-2 border-[#17406E] shadow-[0_25px_70px_rgba(2,11,26,0.95)]">
        {/* 4 Corner Hex Bolts */}
        <div className="absolute top-3 left-3 w-3 h-3 rounded-full bg-[#D9E1EA] p-[1px] shadow-[0_0_6px_rgba(217,225,234,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform rotate-45" />
          </div>
        </div>
        <div className="absolute top-3 right-3 w-3 h-3 rounded-full bg-[#D9E1EA] p-[1px] shadow-[0_0_6px_rgba(217,225,234,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform -rotate-45" />
          </div>
        </div>
        <div className="absolute bottom-3 left-3 w-3 h-3 rounded-full bg-[#D9E1EA] p-[1px] shadow-[0_0_6px_rgba(217,225,234,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform -rotate-12" />
          </div>
        </div>
        <div className="absolute bottom-3 right-3 w-3 h-3 rounded-full bg-[#D9E1EA] p-[1px] shadow-[0_0_6px_rgba(217,225,234,0.6)] z-20 pointer-events-none">
          <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
            <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform rotate-30" />
          </div>
        </div>

        <TacticalBracket color="#D9E1EA" size="lg" />

        <div className="inline-flex items-center space-x-2 px-4 py-1.5 bg-[#050B16]/90 border border-[#D9E1EA]/30 rounded-full font-mono text-[11px] text-[#DEE7F0] tracking-widest mb-4 shadow-[0_0_12px_rgba(217,225,234,0.1)]">
          <span className="w-2 h-2 rounded-full bg-[#FF1E2D] animate-pulse" />
          <span>AUTONOMOUS SYSTEM READY FOR REPO INGESTION</span>
        </div>

        <h2 className="font-headline font-black text-3xl sm:text-5xl lg:text-6xl text-[#EAF1F8] tracking-wider leading-tight mb-4 drop-shadow-[0_4px_25px_rgba(2,11,26,0.9)]">
          SECURE WHAT <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF1E2D] via-[#E31424] to-[#D9E1EA]">
            MATTERS NEXT.
          </span>
        </h2>

        <p className="font-mono text-xs sm:text-sm text-[#A7B4C4] max-w-xl mx-auto leading-relaxed mb-8">
          Continuous AST compiler parsing, deterministic patch synthesis, and airgapped container validation.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <CyberButton
            variant="primary"
            size="lg"
            icon={<AurexLogo size={18} withGlow={false} />}
            onClick={() => onNavigate('dashboard')}
            className="w-full sm:w-auto"
          >
            ENTER SECURITY CONSOLE
          </CyberButton>

          <CyberButton
            variant="secondary"
            size="lg"
            icon={<BookOpen className="w-4 h-4 text-[#D9E1EA]" />}
            onClick={onOpenDocs}
            className="w-full sm:w-auto"
          >
            VIEW ARCHITECTURE
          </CyberButton>
        </div>

        <div className="mt-8 pt-6 border-t border-[#17406E]/50 flex flex-wrap items-center justify-center gap-6 font-mono text-[10px] text-[#A7B4C4]">
          <span>PROTECTED REPOSITORIES: 128</span>
          <span>•</span>
          <span>MITIGATED SINK NODES: 2,357</span>
          <span>•</span>
          <span>REMEDIATION PASS RATE: 94.2%</span>
          <span>•</span>
          <span>SANDBOX TIMEOUT: 10.0S</span>
        </div>
      </div>
    </section>
  );
};
