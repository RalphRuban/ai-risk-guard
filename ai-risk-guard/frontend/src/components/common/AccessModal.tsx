import React from 'react';
import { ShieldAlert, Github, ArrowLeft, Lock } from 'lucide-react';
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#02050B]/85 backdrop-blur-xl animate-fadeIn">
      <div className="relative w-full max-w-md bg-[#030914] border border-[#FF304F]/60 p-6 sm:p-8 shadow-[0_0_50px_rgba(197,31,53,0.3)]">
        <TacticalBracket color="#FF304F" size="lg" />

        {/* Warning Badge */}
        <div className="flex items-center space-x-2 text-[#FF304F] font-mono text-xs font-semibold uppercase tracking-widest mb-4">
          <Lock className="w-4 h-4 text-[#FF304F] animate-pulse" />
          <span>ACCESS RESTRICTED — SECURITY CLEARANCE REQUIRED</span>
        </div>

        <h3 className="font-headline text-xl sm:text-2xl text-white mb-2">
          Authentication Required
        </h3>

        <p className="font-mono text-xs text-[#8D9AAA] leading-relaxed mb-6">
          Access to protected workstation <span className="text-[#65E7FF] font-semibold">[{targetViewName.toUpperCase()}]</span> requires enterprise GitHub operator credentials.
        </p>

        <div className="p-3 bg-[#06101F] border border-[#1E3C5C] mb-6 font-mono text-[11px] text-[#B8C2CE] space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[#8D9AAA]">SECURITY PROTOCOL:</span>
            <span className="text-[#00CFFF]">ARG-SEC-GATE-04</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#8D9AAA]">REQUIRED SCOPE:</span>
            <span className="text-[#F1F5F9]">read:org, repo:security</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#8D9AAA]">AUTH PROVIDER:</span>
            <span className="text-[#00E699]">GITHUB ENTERPRISE</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <CyberButton
            variant="primary"
            className="w-full"
            icon={<Github className="w-4 h-4" />}
            onClick={() => {
              onAuthenticate();
              onClose();
            }}
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
