import React from 'react';
import { Github, Menu, X, ChevronDown, ChevronRight, Lock, UserCheck, BookOpen } from 'lucide-react';
import { ViewId } from '../../types';
import { CyberButton } from './CyberButton';
import { AurexLogo } from './AurexLogo';
import { ALL_VIEWS } from './WorkstationLauncherModal';

interface TacticalSidebarProps {
  currentView: ViewId;
  onNavigate: (view: ViewId) => void;
  isAuthenticated: boolean;
  operatorHandle?: string;
  operatorAvatar?: string;
  onOpenDocs: () => void;
  onLoginClick: () => void;
  onLogoutClick: () => void;
}

const GROUP_LABELS = ['CORE', 'GOVERNANCE', 'SYSTEM'] as const;

export const SHORT_LABELS: Record<string, string> = {
  landing: 'ANCHOR',
  login: 'LOGIN',
  signup: 'SIGNUP',
  dashboard: 'OVERVIEW',
  repositories: 'REPOS',
  findings: 'FINDINGS',
  policy: 'POLICY',
  risk: 'RISK',
  agents: 'AGENTS',
  reports: 'REPORTS',
  'report-detail': 'REPORT DETAIL',
  github: 'SCAN ACTIVITY',
  settings: 'SETTINGS',
  status: 'HEALTH',
  profile: 'PROFILE'
};

export const getGroupedViews = () =>
  GROUP_LABELS.map((group) => ({
    label: group,
    views: ALL_VIEWS.filter((v) => v.category === group && !v.hiddenFromNav)
  }));

export const TacticalSidebar: React.FC<TacticalSidebarProps> = ({
  currentView,
  onNavigate,
  isAuthenticated,
  operatorHandle = 'octocat-secops',
  operatorAvatar = '',
  onOpenDocs,
  onLoginClick,
  onLogoutClick
}) => {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [expandedGroup, setExpandedGroup] = React.useState<string>(() => {
    const meta = ALL_VIEWS.find((v) => v.id === currentView);
    return meta?.category ?? 'CORE';
  });

  const grouped = React.useMemo(() => getGroupedViews(), []);

  const toggleGroup = (label: string) =>
    setExpandedGroup((prev) => (prev === label ? '' : label));

  const renderGroupButton = (view: ViewMetaLike, onDone?: () => void) => {
    const isActive = currentView === view.id;
    const isLocked = view.protected && !isAuthenticated;
    return (
      <button
        key={view.id}
        onClick={() => {
          if (!isLocked) onNavigate(view.id);
          onDone?.();
        }}
        disabled={isLocked}
        title={isLocked ? 'Requires GitHub Clearance' : undefined}
        className={`w-full flex items-center gap-2 px-2 py-1.5 font-mono text-[10px] tracking-widest text-left transition-all border ${
          isActive
            ? 'bg-[#0B2A5E]/90 border-[#D9E1EA]/70 text-[#EAF1F8] shadow-[inset_0_1px_0_rgba(240,245,250,0.25),0_0_12px_rgba(217,225,234,0.2)]'
            : isLocked
            ? 'bg-transparent border-transparent text-[#9AA7B8]/55 cursor-not-allowed'
            : 'bg-transparent border-transparent text-[#C2CDD9] hover:bg-[#0B2A5E]/50 hover:text-white'
        }`}
      >
        <span className="flex-1">{SHORT_LABELS[view.id] ?? view.title.split(' ')[0]}</span>
        {isLocked && <Lock className="w-2.5 h-2.5 text-[#FF1E2D]/80 shrink-0" />}
        {isActive && <span className="w-1.5 h-1.5 rounded-full bg-[#00E699] animate-pulse shrink-0" />}
      </button>
    );
  };

  const sideContent = (
    <div className="flex flex-col h-full">
      {/* Brand Chip */}
      <div
        onClick={() => onNavigate('landing')}
        className="flex items-center space-x-3 px-3 py-4 mx-3 my-3 rounded-lg bg-gradient-to-r from-[#0B2A5E]/85 to-[#071A2E]/95 backdrop-blur-xl border border-[#D9E1EA]/35 hover:border-[#EAF1F8]/70 shadow-[0_0_18px_rgba(217,225,234,0.15)] cursor-pointer transition-all duration-200 group"
      >
        <div className="relative flex items-center justify-center w-8 h-8 bg-[#071A2E] border border-[#00A8FF]/50 rounded-md shadow-[0_0_12px_rgba(0,168,255,0.25)]">
          <AurexLogo size={22} withGlow={false} />
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

      {/* Grouped Dropdown Sub-Nav */}
      <nav className="flex-1 overflow-y-auto px-3 pb-2 no-scrollbar">
        <div className="font-mono text-[10px] text-[#9AA7B8] tracking-widest px-2 pb-2 border-b border-[#17406E] mb-2">
          COMMAND CHAMBER
        </div>
        <div className="space-y-1">
          {grouped.map(({ label, views }) => {
            const isOpen = expandedGroup === label;
            const activeInGroup = views.some((v) => v.id === currentView);
            return (
              <div key={label} className="space-y-0.5">
                <button
                  onClick={() => toggleGroup(label)}
                  className={`w-full flex items-center justify-between px-2 py-1.5 font-mono text-[10px] tracking-widest transition-all border ${
                    isOpen
                      ? 'bg-[#0B2A5E]/50 border-[#D9E1EA]/40 text-[#EAF1F8]'
                      : 'bg-transparent border-transparent text-[#A7B4C4] hover:bg-[#0B2A5E]/40 hover:text-white'
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    {isOpen ? (
                      <ChevronDown className="w-3 h-3 text-[#00A8FF]" />
                    ) : (
                      <ChevronRight className="w-3 h-3 text-[#9AA7B8]" />
                    )}
                    <span>{label} //</span>
                  </span>
                  {activeInGroup && <span className="w-1.5 h-1.5 rounded-full bg-[#00A8FF] animate-pulse" />}
                </button>
                {isOpen && <div className="space-y-0.5 pl-2 border-l border-[#17406E]/60 ml-3">{views.map((v) => renderGroupButton(v))}</div>}
              </div>
            );
          })}
        </div>
      </nav>

      <div className="space-y-2 px-3 pb-3">
        <button
          onClick={onOpenDocs}
          className="w-full flex items-center justify-between px-2 py-1.5 font-mono text-[10px] tracking-widest text-[#A7B4C4] hover:text-white hover:bg-[#0B2A5E]/60 border border-transparent hover:border-[#17406E] transition-all"
        >
          <span className="flex items-center gap-1.5">
            <BookOpen className="w-3 h-3" />
            DOCUMENTATION
          </span>
          <ChevronRight className="w-3 h-3 text-[#9AA7B8]" />
        </button>
      </div>

      {/* Status + Auth Block */}
      <div className="border-t border-[#17406E]/50 p-3 space-y-3 bg-[#020B1A]/70">
        <div className="flex items-center space-x-1.5 px-2 font-mono text-[10px]">
          <span className="w-2 h-2 rounded-full bg-[#FF1E2D] animate-pulse" />
          <span className="text-[#DEE7F0]">CORE ACTIVE</span>
          <span className="text-[#00E699] ml-auto">100%</span>
        </div>
        {isAuthenticated ? (
          <div className="space-y-1.5">
            <div
              onClick={() => onNavigate('profile')}
              className="flex items-center space-x-2 px-2 py-1.5 bg-[#0B2A5E] border border-[#D9E1EA]/50 shadow-[0_0_15px_rgba(217,225,234,0.15)] font-mono text-xs cursor-pointer hover:bg-[#1248A8] transition-all"
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
            <CyberButton
              variant="threat"
              size="sm"
              className="w-full"
              onClick={onLogoutClick}
            >
              DISCONNECT
            </CyberButton>
          </div>
        ) : (
          <CyberButton
            variant="primary"
            size="sm"
            className="w-full"
            icon={<Github className="w-3.5 h-3.5" />}
            onClick={onLoginClick}
          >
            GITHUB SIGN IN
          </CyberButton>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:w-64 lg:shrink-0 lg:flex-col lg:sticky lg:top-0 lg:h-screen bg-[#020B1A]/95 backdrop-blur-2xl border-r border-[#17406E]/60 z-40">
        {sideContent}
      </aside>

      {/* Mobile Slim Bar */}
      <div className="lg:hidden relative z-40 flex items-center justify-between gap-3 px-4 py-2.5 bg-[#020B1A]/85 backdrop-blur-2xl border-b border-[#17406E]/50">
        <div
          onClick={() => onNavigate('landing')}
          className="flex items-center space-x-2 cursor-pointer"
        >
          <div className="flex items-center justify-center w-7 h-7 bg-[#071A2E] border border-[#00A8FF]/50 rounded-md">
            <AurexLogo size={18} withGlow={false} />
          </div>
          <div className="font-headline font-black text-xs tracking-wider text-[#EAF1F8]">
            AUREX
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {isAuthenticated ? (
            <button
              onClick={onLogoutClick}
              className="px-2 py-1.5 font-mono text-[10px] text-[#A7B4C4] hover:text-[#FF1E2D] border border-[#17406E] hover:border-[#FF1E2D] transition-colors"
            >
              EXIT
            </button>
          ) : (
            <CyberButton
              variant="primary"
              size="sm"
              icon={<Github className="w-3.5 h-3.5" />}
              onClick={onLoginClick}
            >
              SIGN IN
            </CyberButton>
          )}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="p-1.5 bg-[#071A2E] border border-[#17406E] text-[#DEE7F0] hover:text-[#FF1E2D]"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 top-[49px] bottom-0 bg-[#020B1A]/95 backdrop-blur-2xl border-b border-[#17406E] p-4 flex flex-col justify-between overflow-y-auto z-40 animate-fadeIn">
          <div className="space-y-2">
            <div className="font-mono text-[10px] tracking-widest text-[#9AA7B8] pb-2 border-b border-[#17406E]">
              NAVIGATION CHAMBER
            </div>
            {grouped.map(({ label, views }) => (
              <div key={label} className="mb-2">
                <div className="font-mono text-[10px] tracking-widest text-[#A7B4C4] mb-1 border-b border-[#17406E]/60 pb-1">
                  {label} //
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {views.map((view) => renderGroupButton(view, () => setMobileOpen(false)))}
                </div>
              </div>
            ))}
          </div>
          <div className="pt-4 border-t border-[#17406E] space-y-2">
            <div className="flex items-center justify-between font-mono text-xs">
              <span className="text-[#9AA7B8]">SYSTEM INTEGRITY:</span>
              <span className="text-[#00E699]">100% OPERATIONAL</span>
            </div>
            {isAuthenticated ? (
              <CyberButton
                variant="threat"
                className="w-full"
                onClick={onLogoutClick}
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
                  setMobileOpen(false);
                }}
              >
                AUTHENTICATE GITHUB
              </CyberButton>
            )}
          </div>
        </div>
      )}
    </>
  );
};

type ViewMetaLike = {
  id: ViewId;
  code: string;
  title: string;
  protected: boolean;
};