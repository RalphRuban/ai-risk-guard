import React from 'react';
import { Github, ArrowLeft, Lock } from 'lucide-react';
import { CyberButton } from './CyberButton';
import { TacticalBracket } from './TacticalBracket';

interface AccessModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthenticate: () => void;
  targetViewName?: string;
}

export const AccessModal: React.FC<AccessModalProps> = ({
  isOpen,
  onClose,
  onAuthenticate,
  targetViewName = 'WORKSTATION'
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#020B1A]/85 backdrop-blur-xl animate-fadeIn">
      <div className="relative w-full max-w-md bg-[#050B16] border border-[#FF1E2D]/60 p-6 sm:p-8 shadow-[0_0_50px_rgba(200,30,45,0.3)]">
        <TacticalBracket color="#FF1E2D" size="lg" />

        {/* Warning Badge */}
        <div className="flex items-center space-x-2 text-[#FF1E2D] font-mono text-xs font-semibold uppercase tracking-widest mb-4">
          <Lock className="w-4 h-4 text-[#FF1E2D] animate-pulse" />
          <span>ACCESS RESTRICTED — SECURITY CLEARANCE REQUIRED</span>
        </div>

        <h3 className="font-headline text-xl sm:text-2xl text-white mb-2">
          Authentication Required
        </h3>

        <p className="font-mono text-xs text-[#9AA7B8] leading-relaxed mb-6">
          Access to protected workstation <span className="text-[#5BC9FF] font-semibold">[{targetViewName.toUpperCase()}]</span> requires enterprise GitHub operator credentials.
        </p>

        <div className="p-3 bg-[#050B16] border border-[#17406E] mb-6 font-mono text-[11px] text-[#C2CDD9] space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[#9AA7B8]">SECURITY PROTOCOL:</span>
            <span className="text-[#00A8FF]">ARG-SEC-GATE-04</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#9AA7B8]">REQUIRED SCOPE:</span>
            <span className="text-[#E4EBF3]">read:org, repo:security</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#9AA7B8]">AUTH PROVIDER:</span>
            <span className="text-[#00E699]">GITHUB ENTERPRISE</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <CyberButton
            variant="primary"
            className="w-full"
            icon={<Github className="w-4 h-4" />}
            onClick={onAuthenticate}
          >
            GITHUB AUTH
          </CyberButton>

          <CyberButton
            variant="outline"
            className="w-full"
            icon={<ArrowLeft className="w-4 h-4" />}
            onClick={onClose}
          >
            RETURN TO PLATFORM
          </CyberButton>
        </div>
      </div>
    </div>
  );
};
