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
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  className = '',
  headerTitle,
  headerCode,
  statusIndicator,
  showBrackets = true,
  interactive = false,
  accentColor = '#CBD5E1'
}) => {
  const statusColors = {
    ACTIVE: 'bg-[#FF2A4B]',
    WARNING: 'bg-[#CBD5E1]',
    ALERT: 'bg-[#DC2626]',
    STANDBY: 'bg-[#94A3B8]'
  };

  return (
    <div
      className={`relative rounded-xl overflow-hidden bg-gradient-to-br from-[#0B2556]/80 via-[#061533]/90 to-[#020716]/98 backdrop-blur-2xl border border-[#184384]/60 shadow-[0_16px_40px_rgba(2,7,22,0.8),0_0_20px_rgba(203,213,225,0.06)] transition-all duration-300 ${
        interactive ? 'hover:border-[#FF2A4B]/60 hover:shadow-[0_20px_50px_rgba(255,42,75,0.2)] hover:-translate-y-1' : ''
      } ${className}`}
    >
      {/* Top Rim Specular Highlight in 10% Metallic Silver */}
      <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-[#CBD5E1]/70 to-transparent pointer-events-none" />

      {showBrackets && <TacticalBracket color={accentColor} />}

      {(headerTitle || headerCode || statusIndicator) && (
        <div className="flex items-center justify-between px-5 py-2.5 border-b border-[#184384]/40 bg-[#030C22]/75 font-mono text-[11px] tracking-wider text-[#94A3B8]">
          <div className="flex items-center space-x-2">
            {statusIndicator && (
              <span className={`w-2 h-2 rounded-full ${statusColors[statusIndicator]} shadow-[0_0_8px_currentColor] animate-pulse`} />
            )}
            {headerTitle && <span className="text-[#F8FAFC] font-headline font-semibold tracking-wide text-xs">{headerTitle}</span>}
          </div>
          {headerCode && (
            <span className="text-[#FF2A4B] font-bold text-[10px] px-2 py-0.5 rounded bg-[#FF2A4B]/10 border border-[#FF2A4B]/40 shadow-[0_0_8px_rgba(255,42,75,0.2)]">
              {headerCode}
            </span>
          )}
        </div>
      )}

      <div className="p-5 sm:p-6">{children}</div>
    </div>
  );
};
