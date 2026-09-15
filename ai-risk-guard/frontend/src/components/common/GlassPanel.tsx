import React from 'react';
import { TacticalBracket } from './TacticalBracket';

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
  headerTitle?: string;
  headerCode?: string;
  statusIndicator?: 'ACTIVE' | 'WARNING' | 'ALERT' | 'STANDBY';
  showBrackets?: boolean;
  interactive?: boolean;
  accentColor?: string;
  onClick?: () => void;
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  className = '',
  headerTitle,
  headerCode,
  statusIndicator,
  showBrackets = true,
  interactive = false,
  accentColor = '#D9E1EA',
  onClick
}) => {
  const statusColors = {
    ACTIVE: 'bg-[#FF1E2D]',
    WARNING: 'bg-[#D9E1EA] shadow-[0_0_8px_rgba(217,225,234,0.7)]',
    ALERT: 'bg-[#E31424]',
    STANDBY: 'bg-[#A7B4C4]'
  };

  return (
    <div
      onClick={onClick}
      className={`relative rounded-xl overflow-hidden bg-gradient-to-br from-[#0B2A5E]/80 via-[#071A2E]/90 to-[#020B1A]/98 backdrop-blur-2xl border border-[#17406E]/60 shadow-[0_16px_40px_rgba(2,11,26,0.8),0_0_20px_rgba(217,225,234,0.06)] transition-all duration-300 ${
        interactive ? 'hover:border-[#FF1E2D]/60 hover:shadow-[0_20px_50px_rgba(255,30,45,0.2)] hover:-translate-y-1' : ''
      } ${className}`}
    >
      {/* Top Rim Specular Highlight in 10% Metallic Silver */}
      <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-[#EAF1F8]/85 to-transparent pointer-events-none shadow-[0_2px_12px_rgba(217,225,234,0.25)]" />

      {showBrackets && <TacticalBracket color={accentColor} />}

      {(headerTitle || headerCode || statusIndicator) && (
        <div className="flex items-center justify-between px-5 py-2.5 border-b border-[#17406E]/40 bg-[#050B16]/75 font-mono text-[11px] tracking-wider text-[#A7B4C4]">
          <div className="flex items-center space-x-2">
            {statusIndicator && (
              <span className={`w-2 h-2 rounded-full ${statusColors[statusIndicator]} shadow-[0_0_8px_currentColor] animate-pulse`} />
            )}
            {headerTitle && <span className="text-[#EAF1F8] font-headline font-semibold tracking-wide text-xs">{headerTitle}</span>}
          </div>
          {headerCode && (
            <span className="text-[#FF1E2D] font-bold text-[10px] px-2 py-0.5 rounded bg-[#FF1E2D]/10 border border-[#FF1E2D]/40 shadow-[0_0_8px_rgba(255,30,45,0.2)]">
              {headerCode}
            </span>
          )}
        </div>
      )}

      <div className="p-5 sm:p-6">{children}</div>
    </div>
  );
};
