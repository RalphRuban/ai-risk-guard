import React from 'react';

interface FooterProps {
  onOpenDocs: () => void;
  onOpenLauncher: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenDocs, onOpenLauncher }) => {
  return (
    <footer className="w-full bg-[#020B1A] border-t border-[#17406E]/60 text-[#A7B4C4] font-mono text-xs py-10 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Brand Col */}
          <div className="space-y-3">
            <span className="font-headline font-bold text-[#EAF1F8] text-sm tracking-wider flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00A8FF] animate-pulse" />
              AUREX
            </span>
            <p className="text-[11px] text-[#A7B4C4] leading-relaxed">
              Autonomous cybersecurity command center. Dual-engine AST remediation, 7-factor risk scoring, and hardened container validation.
            </p>
            <div className="flex items-center space-x-2 text-[10px] text-[#DEE7F0]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#FF1E2D] animate-pulse" />
              <span>DEFENSE CORE ACTIVE // CONTINUOUS LOOP</span>
            </div>
            <div className="pt-2 flex items-center space-x-2">
              <button
                onClick={onOpenDocs}
                className="text-[11px] text-[#D9E1EA] hover:text-white hover:underline"
              >
                View Architecture Docs
              </button>
              <span>•</span>
              <button
                onClick={onOpenLauncher}
                className="text-[11px] text-[#D9E1EA] hover:text-white hover:underline"
              >
                Launcher (All Workstations)
              </button>
            </div>
          </div>

          {/* Telemetry & Audit */}
          <div className="space-y-2">
            <span className="text-[#EAF1F8] font-semibold text-[11px] tracking-wider block">SYSTEM SPECIFICATION</span>
            <div className="p-3 bg-[#071A2E] border border-[#17406E] space-y-1 text-[10px] max-w-sm">
              <div className="flex justify-between">
                <span>VERSION:</span>
                <span className="text-[#D9E1EA]">2.4.0-ENTERPRISE</span>
              </div>
              <div className="flex justify-between">
                <span>SHA-256 AUDIT:</span>
                <span className="text-[#EAF1F8]">8f3b...9d01</span>
              </div>
              <div className="flex justify-between">
                <span>SANDBOX:</span>
                <span className="text-[#DEE7F0]">DOCKER / AIRGAP</span>
              </div>
              <div className="flex justify-between">
                <span>STATUS:</span>
                <span className="text-[#FF1E2D] font-semibold">100% OPERATIONAL</span>
              </div>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-[#17406E]/40 flex flex-col sm:flex-row items-center justify-between text-[10px] text-[#A7B4C4]">
          <div>
            © 2026 AUREX. Autonomous Cybersecurity Command Platform. All rights reserved.
          </div>
          <div className="flex items-center space-x-4 mt-2 sm:mt-0 font-mono">
            <span>CLASSIFICATION: ENTERPRISE RESTRICTED</span>
            <span>ENCRYPTION: AES-256-GCM</span>
          </div>
        </div>
      </div>
    </footer>
  );
};