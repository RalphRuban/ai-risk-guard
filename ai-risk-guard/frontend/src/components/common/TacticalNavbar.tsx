import React from 'react';
import { Shield, Terminal, Github, Menu, X, Cpu, ChevronRight, Lock, UserCheck } from 'lucide-react';
import { ViewId } from '../../types';
import { CyberButton } from './CyberButton';
import { AurexLogo } from './AurexLogo';

interface TacticalNavbarProps {
  currentView: ViewId;
  onNavigate: (view: ViewId) => void;
  isAuthenticated: boolean;
  operatorHandle?: string;
  onOpenLauncher: () => void;
  onOpenDocs: () => void;
  onLoginClick: () => void;
  onLogoutClick: () => void;
}

export const TacticalNavbar: React.FC<TacticalNavbarProps> = ({
  currentView,
  onNavigate,
  isAuthenticated,
  operatorHandle = 'octocat-secops',
  onOpenLauncher,
  onOpenDocs,
  onLoginClick,
  onLogoutClick
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const navLinks = [
    { label: 'PLATFORM', view: 'landing' as ViewId },
    { label: 'DASHBOARD', view: 'dashboard' as ViewId, protected: true },
    { label: 'SCANNER', view: 'scanner' as ViewId, protected: true },
    { label: 'REMEDIATION', view: 'patch' as ViewId, protected: true },
    { label: 'SANDBOX', view: 'sandbox' as ViewId, protected: true },
    { label: 'POLICY', view: 'policy' as ViewId, protected: true },
    { label: 'SETTINGS', view: 'settings' as ViewId, protected: true },
  ];

  return (
    <header className="sticky top-0 z-40 w-full px-3 py-2.5 sm:px-6 sm:py-3 bg-[#020716]/85 backdrop-blur-2xl border-b border-[#184384]/50 shadow-[0_4px_30px_rgba(2,7,22,0.8)]">
      <div className="max-w-[1760px] mx-auto flex items-center justify-between gap-3 px-2 sm:px-4">
        {/* Module 1 (Left): Brand Identity */}
        <div 
          onClick={() => onNavigate('landing')}
          className="flex items-center space-x-3 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-[#0B2556]/85 to-[#061533]/95 backdrop-blur-xl border border-[#CBD5E1]/30 hover:border-[#00CFFF]/80 shadow-[0_0_15px_rgba(203,213,225,0.08)] cursor-pointer transition-all duration-200 group shrink-0"
        >
          <div className="relative flex items-center justify-center w-7 h-7 bg-[#061533] border border-[#00CFFF]/50 rounded-md shadow-[0_0_12px_rgba(0,207,255,0.25)]">
            <AurexLogo size={20} withGlow={false} />
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-[#00CFFF] rounded-full animate-ping" />
          </div>
          <div>
            <div className="font-headline font-black text-xs sm:text-sm tracking-wider text-[#F8FAFC] group-hover:text-[#00CFFF] transition-colors">
              AUREX
            </div>
            <div className="font-mono text-[9px] tracking-widest text-[#94A3B8]">
              CYBER DEFENSE
            </div>
          </div>
        </div>

        {/* Module 2 (Center): Navigation Links (Desktop) */}
        <nav className="hidden lg:flex items-center space-x-1 px-3 py-1 rounded-lg bg-[#061533]/85 backdrop-blur-xl border border-[#184384]/60 shadow-lg">
          {navLinks.map((link) => {
            const isActive = currentView === link.view;
            return (
              <button
                key={link.label}
                onClick={() => onNavigate(link.view)}
                className={`relative px-3 py-1 font-mono text-[11px] tracking-widest transition-all ${
                  isActive
                    ? 'text-white font-semibold bg-[#FF2A4B]/20'
                    : 'text-[#94A3B8] hover:text-white hover:bg-[#0B2556]/60'
                }`}
              >
                {link.label}
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#FF2A4B] shadow-[0_0_8px_#FF2A4B]" />
                )}
                {link.protected && !isAuthenticated && (
                  <Lock className="inline-block w-2.5 h-2.5 ml-1 text-[#94A3B8]/70" />
                )}
              </button>
            );
          })}

          <button
            onClick={onOpenDocs}
            className="px-3 py-1 font-mono text-[11px] tracking-widest text-[#94A3B8] hover:text-white hover:bg-[#0B2556]/60 transition-all"
          >
            DOCUMENTATION
          </button>
        </nav>

        {/* Module 3 (Right): Status, Workstations & GitHub Auth */}
        <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
          {/* Status Pill */}
          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 bg-[#030C22] border border-[#184384] font-mono text-[10px]">
            <span className="w-2 h-2 rounded-full bg-[#FF2A4B] animate-pulse" />
            <span className="text-[#E2E8F0] font-medium">CORE ACTIVE</span>
          </div>

          {/* Workstations Modal Trigger (Silver Secondary) */}
          <CyberButton
            variant="secondary"
            size="sm"
            onClick={onOpenLauncher}
            icon={<Terminal className="w-3.5 h-3.5 text-[#CBD5E1]" />}
          >
            <span className="hidden md:inline">18</span> WORKSTATIONS
          </CyberButton>

          {/* GitHub Auth Pill / Operator Menu */}
          {isAuthenticated ? (
            <div className="flex items-center space-x-1">
              <div 
                onClick={() => onNavigate('dashboard')}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-[#0B2556] border border-[#CBD5E1]/50 shadow-[0_0_15px_rgba(203,213,225,0.15)] font-mono text-xs cursor-pointer hover:bg-[#12356B] transition-all"
              >
                <UserCheck className="w-3.5 h-3.5 text-[#FF2A4B]" />
                <span className="text-[#F8FAFC] font-semibold text-[11px]">@{operatorHandle}</span>
              </div>
              <button
                onClick={onLogoutClick}
                className="px-2 py-1.5 font-mono text-[10px] text-[#94A3B8] hover:text-[#FF2A4B] border border-[#184384] hover:border-[#FF2A4B] transition-colors"
                title="Disconnect Operator Session"
              >
                EXIT
              </button>
            </div>
          ) : (
            <CyberButton
              variant="primary"
              size="sm"
              icon={<Github className="w-3.5 h-3.5" />}
              onClick={onLoginClick}
            >
              GITHUB SIGN IN
            </CyberButton>
          )}

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-1.5 bg-[#061533] border border-[#184384] text-[#E2E8F0] hover:text-[#FF2A4B]"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-x-0 top-[57px] bottom-0 bg-[#02050B]/95 backdrop-blur-2xl border-b border-[#1E3C5C] p-6 flex flex-col justify-between overflow-y-auto animate-fadeIn z-50">
          <div className="space-y-4">
            <div className="font-mono text-[11px] text-[#8D9AAA] tracking-widest pb-2 border-b border-[#1E3C5C]">
              NAVIGATION CHAMBER
            </div>

            <div className="space-y-2">
              {navLinks.map((link) => (
                <button
                  key={link.label}
                  onClick={() => {
                    onNavigate(link.view);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between p-3 font-mono text-sm border text-left ${
                    currentView === link.view
                      ? 'bg-[#087BFF]/20 border-[#00CFFF] text-[#65E7FF]'
                      : 'bg-[#06101F] border-[#1E3C5C] text-[#D7DEE7]'
                  }`}
                >
                  <span>{link.label}</span>
                  <ChevronRight className="w-4 h-4 text-[#8D9AAA]" />
                </button>
              ))}

              <button
                onClick={() => {
                  onOpenDocs();
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center justify-between p-3 font-mono text-sm bg-[#06101F] border border-[#1E3C5C] text-[#D7DEE7]"
              >
                <span>DOCUMENTATION</span>
                <ChevronRight className="w-4 h-4 text-[#8D9AAA]" />
              </button>

              <button
                onClick={() => {
                  onOpenLauncher();
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center justify-between p-3 font-mono text-sm bg-[#08172A] border border-[#00CFFF]/50 text-[#00CFFF]"
              >
                <span>ALL 18 WORKSTATIONS</span>
                <Terminal className="w-4 h-4 text-[#00CFFF]" />
              </button>
            </div>
          </div>

          <div className="pt-6 border-t border-[#1E3C5C] space-y-3">
            <div className="flex items-center justify-between font-mono text-xs">
              <span className="text-[#8D9AAA]">SYSTEM INTEGRITY:</span>
              <span className="text-[#00E699]">100% OPERATIONAL</span>
            </div>
            {isAuthenticated ? (
              <CyberButton
                variant="threat"
                className="w-full"
                onClick={() => {
                  onLogoutClick();
                  setMobileMenuOpen(false);
                }}
              >
                DISCONNECT OPERATOR
              </CyberButton>
            ) : (
              <CyberButton
                variant="primary"
                className="w-full"
                icon={<Github className="w-4 h-4" />}
                onClick={() => {
                  onLoginClick();
                  setMobileMenuOpen(false);
                }}
              >
                AUTHENTICATE GITHUB
              </CyberButton>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
