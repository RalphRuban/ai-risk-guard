import React from 'react';
import { Shield, Terminal, Cpu, CheckCircle2 } from 'lucide-react';
import { ViewId } from '../../types';
import { AurexLogo } from './AurexLogo';

interface FooterProps {
  onNavigate: (view: ViewId) => void;
  onOpenDocs: () => void;
  onOpenLauncher: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigate, onOpenDocs, onOpenLauncher }) => {
  return (
    <footer className="w-full bg-[#020716] border-t border-[#184384]/60 text-[#94A3B8] font-mono text-xs py-10 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Col */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2.5">
              <AurexLogo size={22} withGlow={false} />
              <span className="font-headline font-bold text-[#F8FAFC] text-sm tracking-wider">AUREX</span>
            </div>
            <p className="text-[11px] text-[#94A3B8] leading-relaxed">
              Autonomous cybersecurity command center. Dual-engine AST remediation, 7-factor risk scoring, and hardened container validation.
            </p>
            <div className="flex items-center space-x-2 text-[10px] text-[#E2E8F0]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#FF2A4B] animate-pulse" />
              <span>DEFENSE CORE ACTIVE // CONTINUOUS LOOP</span>
            </div>
          </div>

          {/* Workstations Links */}
          <div className="space-y-2">
            <span className="text-[#F8FAFC] font-semibold text-[11px] tracking-wider block">CORE WORKSTATIONS</span>
            <ul className="space-y-1.5 text-[11px]">
              <li><button onClick={() => onNavigate('dashboard')} className="hover:text-[#FF2A4B] transition-colors">04 Enterprise Dashboard</button></li>
              <li><button onClick={() => onNavigate('scanner')} className="hover:text-[#FF2A4B] transition-colors">06 Live AST Scanner</button></li>
              <li><button onClick={() => onNavigate('findings')} className="hover:text-[#FF2A4B] transition-colors">07 Vulnerability Findings</button></li>
              <li><button onClick={() => onNavigate('patch')} className="hover:text-[#FF2A4B] transition-colors">08 Automated Remediation</button></li>
              <li><button onClick={() => onNavigate('sandbox')} className="hover:text-[#FF2A4B] transition-colors">09 Hardened Sandbox</button></li>
            </ul>
          </div>

          {/* Engines & Governance */}
          <div className="space-y-2">
            <span className="text-[#F8FAFC] font-semibold text-[11px] tracking-wider block">ENGINES & GOVERNANCE</span>
            <ul className="space-y-1.5 text-[11px]">
              <li><button onClick={() => onNavigate('risk')} className="hover:text-[#FF2A4B] transition-colors">11 7-Factor Risk Engine</button></li>
              <li><button onClick={() => onNavigate('policy')} className="hover:text-[#FF2A4B] transition-colors">10 Governance & Policy</button></li>
              <li><button onClick={() => onNavigate('agents')} className="hover:text-[#FF2A4B] transition-colors">13 Multi-Agent Mesh</button></li>
              <li><button onClick={() => onNavigate('reports')} className="hover:text-[#FF2A4B] transition-colors">14 Security Reports Hub</button></li>
              <li><button onClick={() => onNavigate('status')} className="hover:text-[#FF2A4B] transition-colors">18 System Health Diagnostics</button></li>
            </ul>
          </div>

          {/* Telemetry & Audit */}
          <div className="space-y-2">
            <span className="text-[#F8FAFC] font-semibold text-[11px] tracking-wider block">SYSTEM SPECIFICATION</span>
            <div className="p-3 bg-[#061533] border border-[#184384] space-y-1 text-[10px]">
              <div className="flex justify-between">
                <span>VERSION:</span>
                <span className="text-[#CBD5E1]">2.4.0-ENTERPRISE</span>
              </div>
              <div className="flex justify-between">
                <span>SHA-256 AUDIT:</span>
                <span className="text-[#F8FAFC]">8f3b...9d01</span>
              </div>
              <div className="flex justify-between">
                <span>SANDBOX:</span>
                <span className="text-[#E2E8F0]">DOCKER / AIRGAP</span>
              </div>
              <div className="flex justify-between">
                <span>STATUS:</span>
                <span className="text-[#FF2A4B] font-semibold">100% OPERATIONAL</span>
              </div>
            </div>
            <div className="pt-2 flex items-center space-x-2">
              <button 
                onClick={onOpenDocs} 
                className="text-[11px] text-[#CBD5E1] hover:text-white hover:underline"
              >
                View Architecture Docs
              </button>
              <span>•</span>
              <button 
                onClick={onOpenLauncher} 
                className="text-[11px] text-[#CBD5E1] hover:text-white hover:underline"
              >
                Launcher (18 Views)
              </button>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-[#184384]/40 flex flex-col sm:flex-row items-center justify-between text-[10px] text-[#94A3B8]">
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
