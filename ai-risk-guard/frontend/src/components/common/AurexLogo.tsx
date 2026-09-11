// AUREX exact vector emblem (1:1 with user image)
import React from 'react';

interface AurexLogoProps {
  className?: string;
  size?: number;
  withGlow?: boolean;
}

export const AurexLogo: React.FC<AurexLogoProps> = ({
  className = '',
  size = 36,
  withGlow = true
}) => {
  return (
    <div 
      className={`relative inline-flex items-center justify-center select-none ${className}`}
      style={{ width: size, height: size }}
    >
      {withGlow && (
        <div 
          className="absolute inset-0 rounded-full blur-md opacity-75 pointer-events-none"
          style={{
            background: 'radial-gradient(circle, rgba(0,140,255,0.45) 0%, rgba(255,23,68,0.25) 60%, transparent 80%)'
          }}
        />
      )}
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full relative z-10 drop-shadow-[0_2px_12px_rgba(0,140,255,0.4)]"
      >
        <defs>
          <linearGradient id="aurexLeftBlueRim" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#00E5FF" />
            <stop offset="35%" stopColor="#0088FF" />
            <stop offset="100%" stopColor="#0044EE" />
          </linearGradient>

          <linearGradient id="aurexSilverRim" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="60%" stopColor="#CBD5E1" />
            <stop offset="100%" stopColor="#94A3B8" />
          </linearGradient>

          <linearGradient id="aurexRedAccent" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FF2A4B" />
            <stop offset="100%" stopColor="#D50000" />
          </linearGradient>

          <radialGradient id="aurexOrbGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#70E4FF" />
            <stop offset="50%" stopColor="#0088FF" />
            <stop offset="100%" stopColor="#0044CC" />
          </radialGradient>
        </defs>

        {/* 1. Dark Shield Recessed Backing */}
        <path
          d="M50 8L82 22V52C82 72 67 87 50 94C33 87 18 72 18 52V22L50 8Z"
          fill="#020612"
          stroke="#07132A"
          strokeWidth="1.5"
        />

        {/* 2. Left Electric Blue Outer Rim */}
        <path
          d="M50 8L18 22V52C18 72 33 87 50 94V86C36.5 80 25 67 25 52V27L50 16V8Z"
          fill="url(#aurexLeftBlueRim)"
        />

        {/* 3. Top-Right Silver Outer Rim */}
        <path
          d="M50 8L82 22V52C82 61 78 70 71 77.5L66 72.5C72 66.5 75 59.5 75 52V27L50 16V8Z"
          fill="url(#aurexSilverRim)"
        />

        {/* 4. Lower-Right Red Defense Accent Blade */}
        <path
          d="M66 52L50 78V86C58.5 80.5 66 73 70 63.5L75 52H66Z"
          fill="url(#aurexRedAccent)"
        />

        {/* 5. Inner White/Silver Beveled Contour */}
        <path
          d="M50 20L73 30V52C73 66.5 62 78 50 84C38 78 27 66.5 27 52V30L50 20Z"
          fill="#01040D"
          stroke="#E2E8F0"
          strokeWidth="1.8"
        />

        {/* 6. Exact 3-Circuit Tree Lines */}
        {/* Center Vertical Trunk */}
        <line x1="50" y1="36" x2="50" y2="78" stroke="#0088FF" strokeWidth="3" strokeLinecap="round" />

        {/* Left Circuit Branch */}
        <path
          d="M50 70L38 61V44"
          stroke="#0088FF"
          strokeWidth="2.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Left Terminal Ring */}
        <circle cx="38" cy="41" r="3.6" fill="#01040D" stroke="#0088FF" strokeWidth="2.4" />

        {/* Right Lower Red Circuit Segment */}
        <path
          d="M50 70L62 61V53"
          stroke="#FF2A4B"
          strokeWidth="2.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Right Upper Blue Circuit Segment */}
        <path
          d="M62 53V44"
          stroke="#0088FF"
          strokeWidth="2.8"
          strokeLinecap="round"
        />
        {/* Right Terminal Ring */}
        <circle cx="62" cy="41" r="3.6" fill="#01040D" stroke="#0088FF" strokeWidth="2.4" />

        {/* Center Top Ring */}
        <circle cx="50" cy="34" r="4.2" fill="#01040D" stroke="#0088FF" strokeWidth="2.6" />

        {/* 7. Center Radiant Energy Core Orb */}
        <circle cx="50" cy="48" r="7.5" fill="url(#aurexOrbGrad)" />
        <circle cx="50" cy="48" r="4" fill="#FFFFFF" opacity="0.85" />
      </svg>
    </div>
  );
};
