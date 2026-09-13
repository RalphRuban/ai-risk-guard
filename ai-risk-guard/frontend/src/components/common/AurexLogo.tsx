// AUREX authentic emblem — renders the real logo PNG (transparent background,
// generated from "Aurex Logo.png" via tools/make_aurex_logo.py).
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
            background: 'radial-gradient(circle, rgba(0,168,255,0.45) 0%, rgba(255,30,45,0.25) 60%, transparent 80%)'
          }}
        />
      )}
      <img
        src="/aurex-logo.png"
        alt="AUREX"
        className="relative z-10 w-full h-full object-contain pointer-events-none"
        style={{ filter: withGlow ? 'drop-shadow(0 2px 12px rgba(0,168,255,0.4))' : undefined }}
        draggable={false}
      />
    </div>
  );
};