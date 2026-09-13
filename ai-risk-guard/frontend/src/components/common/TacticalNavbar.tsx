import React from 'react';
import { Github, Menu, X, UserCheck } from 'lucide-react';
import { ViewId } from '../../types';
import { CyberButton } from './CyberButton';
import { AurexLogo } from './AurexLogo';

interface TacticalNavbarProps {
  currentView: ViewId;
  onNavigate: (view: ViewId) => void;
  isAuthenticated: boolean;
  operatorHandle?: string;
  operatorAvatar?: string;
  onLoginClick: () => void;
  onLogoutClick: () => void;
}

export const TacticalNavbar: React.FC<TacticalNavbarProps> = ({
  currentView,
  onNavigate,
  isAuthenticated,
  operatorHandle = 'octocat-secops',
  operatorAvatar = '',
  onLoginClick,
  onLogoutClick
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const publicLinks = [
    { label: 'PLATFORM', view: 'landing' as ViewId },
    { label: 'SIGN IN', view: 'login' as ViewId },
    { label: 'CREATE ACCOUNT', view: 'signup' as ViewId }
  ];

  return (
    <header className="sticky top-0 z-40 w-full px-3 py-2.5 sm:px-6 sm:py-3 bg-[#020B1A]/85 backdrop-blur-2xl border-b border-[#17406E]/50 shadow-[0_4px_30px_rgba(2,11,26,0.8)]">
      <div className="max-w-[1760px] mx-auto flex items-center justify-between gap-3 px-2 sm:px-4">
        {/* Module 1 (Left): Brand Identity */}
        <div
          onClick={() => onNavigate('landing')}
          className="flex items-center space-x-3 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-[#0B2A5E]/85 to-[#071A2E]/95 backdrop-blur-xl border border-[#D9E1EA]/35 hover:border-[#EAF1F8]/70 shadow-[0_0_18px_rgba(217,225,234,0.15)] cursor-pointer transition-all duration-200 group shrink-0"
        >
          <div className="relative flex items-center justify-center w-7 h-7 bg-[#071A2E] border border-[#00A8FF]/50 rounded-md shadow-[0_0_12px_rgba(0,168,255,0.25)]">
            <AurexLogo size={20} withGlow={false} />
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-[#00A8FF] rounded-full animate-ping" />
          </div>
          <div>
            <div className="font-headline font-black text-xs sm:text-sm tracking-wider text-[#EAF1F8] group-hover:text-[#00A8FF] transition-colors">
              AUREX
            </div>
            <div className="font-mono text-[9px] tracking-widest text-[#A7B4C4]">
              CYBER DEFENSE
            </div>
          </div>
        </div>

        {/* Module 2 (Right): Core Indication & GitHub Auth */}
        <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
          {/* Status Pill */}
          <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 bg-[#050B16] border border-[#17406E] shadow-[inset_0_1px_0_rgba(222,231,240,0.2)] font-mono text-[10px]">
            <span className="w-2 h-2 rounded-full bg-[#FF1E2D] animate-pulse" />
            <span className="text-[#DEE7F0] font-medium">CORE ACTIVE</span>
          </div>

          {/* GitHub Auth Pill / Operator Menu */}
          {isAuthenticated ? (
            <>
              <div
                onClick={() => onNavigate('profile')}
                className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 bg-[#0B2A5E] border border-[#D9E1EA]/50 shadow-[0_0_15px_rgba(217,225,234,0.15)] font-mono text-xs cursor-pointer hover:bg-[#1248A8] transition-all"
                title="View Operator Profile"
              >
                {operatorAvatar ? (
                  <img
                    src={operatorAvatar}
                    alt={operatorHandle}
                    className="w-5 h-5 rounded-full border border-[#00A8FF]/50 object-cover"
                  />
                ) : (
                  <UserCheck className="w-3.5 h-3.5 text-[#FF1E2D]" />
                )}
                <span className="text-[#EAF1F8] font-semibold text-[11px]">@{operatorHandle}</span>
              </div>
              <button
                onClick={onLogoutClick}
                className="px-2 py-1.5 font-mono text-[10px] text-[#A7B4C4] hover:text-[#FF1E2D] border border-[#17406E] hover:border-[#FF1E2D] transition-colors"
                title="Disconnect Operator Session"
              >
                EXIT
              </button>
            </>
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
            className="lg:hidden p-1.5 bg-[#071A2E] border border-[#17406E] text-[#DEE7F0] hover:text-[#FF1E2D]"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-x-0 top-[57px] bottom-0 bg-[#020B1A]/95 backdrop-blur-2xl border-b border-[#17406E] p-6 flex flex-col justify-between overflow-y-auto animate-fadeIn z-50">
          <div className="space-y-4">
            <div className="font-mono text-[11px] text-[#9AA7B8] tracking-widest pb-2 border-b border-[#17406E]">
              NAVIGATION CHAMBER
            </div>

            <div className="space-y-2">
              {publicLinks.map((link) => (
                <button
                  key={link.label}
                  onClick={() => {
                    onNavigate(link.view);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between p-3 font-mono text-sm border text-left ${
                    currentView === link.view
                      ? 'bg-[#007BFF]/20 border-[#00A8FF] text-[#5BC9FF]'
                      : 'bg-[#050B16] border-[#17406E] text-[#D9E1EA]'
                  }`}
                >
                  <span>{link.label}</span>
                </button>
              ))}

              {isAuthenticated && (
                <button
                  onClick={() => {
                    onNavigate('profile');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2 p-3 font-mono text-sm bg-[#050B16] border border-[#17406E] text-[#D9E1EA]"
                >
                  {operatorAvatar ? (
                    <img
                      src={operatorAvatar}
                      alt={operatorHandle}
                      className="w-5 h-5 rounded-full border border-[#00A8FF]/50 object-cover"
                    />
                  ) : (
                    <UserCheck className="w-4 h-4 text-[#FF1E2D]" />
                  )}
                  <span>@{operatorHandle}</span>
                </button>
              )}
            </div>
          </div>

          <div className="pt-6 border-t border-[#17406E] space-y-3">
            <div className="flex items-center justify-between font-mono text-xs">
              <span className="text-[#9AA7B8]">SYSTEM INTEGRITY:</span>
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