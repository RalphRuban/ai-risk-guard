import React from 'react';

interface HangingGlassCardProps {
  children: React.ReactNode;
  className?: string;
  hanging?: boolean;
  floatingDelay?: boolean;
  glowColor?: 'cyan' | 'blue' | 'threat' | 'green';
  onClick?: () => void;
}

export const HangingGlassCard: React.FC<HangingGlassCardProps> = ({
  children,
  className = '',
  hanging = true,
  floatingDelay = false,
  glowColor = 'cyan',
  onClick
}) => {
  const glowBorderClass = {
    cyan: 'border-[#D9E1EA]/25 hover:border-[#FF1E2D]/70 shadow-[0_12px_40px_rgba(2,11,26,0.8)] hover:shadow-[0_20px_50px_rgba(255,30,45,0.25)]',
    blue: 'border-[#17406E]/50 hover:border-[#FF1E2D]/70 shadow-[0_12px_40px_rgba(2,11,26,0.8)] hover:shadow-[0_20px_50px_rgba(255,30,45,0.25)]',
    threat: 'border-[#FF1E2D]/40 hover:border-[#FF1E2D]/80 shadow-[0_12px_40px_rgba(255,30,45,0.15)] hover:shadow-[0_20px_50px_rgba(255,30,45,0.35)]',
    green: 'border-[#D9E1EA]/30 hover:border-[#D9E1EA]/80 shadow-[0_12px_40px_rgba(2,11,26,0.8)] hover:shadow-[0_20px_50px_rgba(217,225,234,0.25)]'
  }[glowColor];

  return (
    <div
      className={`relative group ${
        floatingDelay ? 'animate-float-delayed' : 'animate-float'
      } transition-transform duration-300`}
    >
      {/* Tactical Hanging Tethers & Suspension Pins (10% Red Cable + 10% Silver Pin) */}
      {hanging && (
        <>
          {/* Left Tether */}
          <div className="absolute -top-5 left-6 w-[2px] h-5 bg-gradient-to-b from-[#FF1E2D]/90 via-[#FF1E2D]/40 to-transparent pointer-events-none z-10">
            <span className="absolute -top-1.5 -left-[3px] w-2 h-2 rounded-full bg-[#D9E1EA] shadow-[0_0_8px_#DEE7F0,0_0_12px_rgba(255,30,45,0.8)] animate-pulse" />
          </div>

          {/* Right Tether */}
          <div className="absolute -top-5 right-6 w-[2px] h-5 bg-gradient-to-b from-[#FF1E2D]/90 via-[#FF1E2D]/40 to-transparent pointer-events-none z-10">
            <span className="absolute -top-1.5 -left-[3px] w-2 h-2 rounded-full bg-[#D9E1EA] shadow-[0_0_8px_#DEE7F0,0_0_12px_rgba(255,30,45,0.8)] animate-pulse" />
          </div>
        </>
      )}

      {/* Main Glassmorphic Panel (80% Navy Blue Base, 10% Silver Specular Rim) */}
      <div
        onClick={onClick}
        className={`relative overflow-hidden rounded-lg bg-gradient-to-br from-[#0B2A5E]/75 via-[#071A2E]/85 to-[#020B1A]/98 backdrop-blur-2xl border transition-all duration-300 ${glowBorderClass} ${
          onClick ? 'cursor-pointer' : ''
        } ${className}`}
      >
        {/* Specular Shimmer Sweep on Hover (Silver Titanium) */}
        <div className="absolute inset-0 -translate-x-full group-hover:animate-shimmer bg-gradient-to-r from-transparent via-white/[0.09] to-transparent pointer-events-none" />

        {/* Top Rim Light Accent (10% Silver) */}
        <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-[#D9E1EA]/80 to-transparent opacity-70 group-hover:opacity-100 transition-opacity" />

        {/* Content */}
        {children}
      </div>
    </div>
  );
};
