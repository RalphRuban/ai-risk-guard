import React from 'react';

interface RuggedFrameProps {
  children: React.ReactNode;
  className?: string;
  unitCode?: string;
  title?: string;
  statusBadge?: string;
  statusColor?: 'red' | 'silver' | 'navy';
  headerAction?: React.ReactNode;
  showScrews?: boolean;
}

export const RuggedFrame: React.FC<RuggedFrameProps> = ({
  children,
  className = '',
  unitCode = 'SEC-CHASSIS // 01-A',
  title,
  statusBadge,
  statusColor = 'red',
  headerAction,
  showScrews = true
}) => {
  const statusColors = {
    red: 'bg-[#FF1E2D] text-white shadow-[0_0_10px_#FF1E2D]',
    silver: 'bg-[#D9E1EA] text-[#020B1A] shadow-[0_0_10px_rgba(217,225,234,0.8)]',
    navy: 'bg-[#007BFF] text-white shadow-[0_0_10px_#007BFF]'
  };

  return (
    <div className={`relative rounded-xl border-2 border-[#17406E] bg-gradient-to-br from-[#0B2A5E]/85 via-[#071A2E]/92 to-[#020B1A]/98 backdrop-blur-2xl shadow-[0_20px_60px_rgba(2,11,26,0.95),inset_0_1px_0_rgba(217,225,234,0.18)] ${className}`}>
      {/* 4 Machined Aerospace Hex Bolts / Screws */}
      {showScrews && (
        <>
          {/* Top Left Bolt */}
          <div className="absolute top-2.5 left-2.5 w-3 h-3 rounded-full bg-gradient-to-br from-[#D9E1EA] via-[#A7B4C4] to-[#76879D] p-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.8),0_1px_3px_rgba(0,0,0,0.8)] z-20 pointer-events-none">
            <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
              <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform rotate-45" />
            </div>
          </div>

          {/* Top Right Bolt */}
          <div className="absolute top-2.5 right-2.5 w-3 h-3 rounded-full bg-gradient-to-br from-[#D9E1EA] via-[#A7B4C4] to-[#76879D] p-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.8),0_1px_3px_rgba(0,0,0,0.8)] z-20 pointer-events-none">
            <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
              <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform -rotate-45" />
            </div>
          </div>

          {/* Bottom Left Bolt */}
          <div className="absolute bottom-2.5 left-2.5 w-3 h-3 rounded-full bg-gradient-to-br from-[#D9E1EA] via-[#A7B4C4] to-[#76879D] p-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.8),0_1px_3px_rgba(0,0,0,0.8)] z-20 pointer-events-none">
            <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
              <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform -rotate-12" />
            </div>
          </div>

          {/* Bottom Right Bolt */}
          <div className="absolute bottom-2.5 right-2.5 w-3 h-3 rounded-full bg-gradient-to-br from-[#D9E1EA] via-[#A7B4C4] to-[#76879D] p-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.8),0_1px_3px_rgba(0,0,0,0.8)] z-20 pointer-events-none">
            <div className="w-full h-full rounded-full bg-[#050B16] flex items-center justify-center">
              <span className="w-1.5 h-[1px] bg-[#D9E1EA] block transform rotate-30" />
            </div>
          </div>
        </>
      )}

      {/* Industrial Corner Chamfer Brackets (10% Silver) */}
      <span className="absolute -top-[2px] -left-[2px] w-4 h-4 border-t-2 border-l-2 border-[#D9E1EA] pointer-events-none" />
      <span className="absolute -top-[2px] -right-[2px] w-4 h-4 border-t-2 border-r-2 border-[#D9E1EA] pointer-events-none" />
      <span className="absolute -bottom-[2px] -left-[2px] w-4 h-4 border-b-2 border-l-2 border-[#D9E1EA] pointer-events-none" />
      <span className="absolute -bottom-[2px] -right-[2px] w-4 h-4 border-b-2 border-r-2 border-[#D9E1EA] pointer-events-none" />

      {/* Top Rugged Header Bar */}
      {(title || unitCode || statusBadge) && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 border-b-2 border-[#17406E] bg-[#050B16]/85 font-mono text-xs">
          <div className="flex items-center space-x-3">
            {unitCode && (
              <span className="px-2 py-0.5 rounded bg-[#0B2A5E] border border-[#D9E1EA]/30 text-[#A7B4C4] text-[10px] tracking-wider font-semibold">
                {unitCode}
              </span>
            )}
            {title && (
              <span className="font-headline font-bold text-sm tracking-wide text-[#EAF1F8]">
                {title}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {statusBadge && (
              <span className={`px-2 py-0.5 rounded text-[9px] font-bold tracking-widest uppercase ${statusColors[statusColor]}`}>
                {statusBadge}
              </span>
            )}
            {headerAction}
          </div>
        </div>
      )}

      {/* Rugged Specular Top Rim Light */}
      <div className="absolute top-0 inset-x-0 h-[1.5px] bg-gradient-to-r from-transparent via-[#D9E1EA]/70 to-transparent pointer-events-none" />

      {/* Main Inner Body */}
      <div className="p-6 sm:p-8 lg:p-10 relative z-10">
        {children}
      </div>

      {/* Bottom Technical Rulers & Dimension Hashes */}
      <div className="flex items-center justify-between px-6 py-1.5 border-t border-[#17406E]/60 bg-[#020B1A]/90 font-mono text-[9px] text-[#76879D]">
        <div className="flex items-center space-x-4">
          <span>LATENCY: 0.8MS</span>
          <span>AIRGAP ISOLATION: ACTIVE</span>
          <span className="hidden sm:inline">CGROUPS: QUOTA ENFORCED</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#FF1E2D] animate-pulse" />
          <span className="text-[#A7B4C4]">SEC-OPS-HUD // v2.4</span>
        </div>
      </div>
    </div>
  );
};
