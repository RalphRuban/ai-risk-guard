import React, { useEffect, useMemo, useState } from 'react';
import { AurexLogo } from './AurexLogo';

interface CinematicIntroProps {
  onComplete: () => void;
}

const BOOT_LINES = [
  'INITIALIZING DEFENSE CORE',
  'CHARGING ARC ENERGY GRID',
  'SYNCING AUREX COMMAND SHIELD',
  'CALIBRATING THREAT SENSORS',
  'ARMING AUTONOMOUS PROTOCOLS'
];

const AUREX_LETTERS = ['A', 'U', 'R', 'E', 'X'];

export const CinematicIntro: React.FC<CinematicIntroProps> = ({ onComplete }) => {
  const [exiting, setExiting] = useState(false);
  const [showLogo, setShowLogo] = useState(false);
  const [bootIndex, setBootIndex] = useState(0);

  const particles = useMemo(
    () =>
      Array.from({ length: 16 }, (_, i) => {
        const angle = Math.random() * Math.PI * 2;
        const dist = 60 + Math.random() * 220;
        return {
          left: 50 + Math.cos(angle) * (dist / 5),
          top: 50 + Math.sin(angle) * (dist / 5),
          driftX: `${(Math.random() * 60 - 30).toFixed(1)}px`,
          driftY: `${(Math.random() * 60 - 30).toFixed(1)}px`,
          dur: `${(1.8 + Math.random() * 2.2).toFixed(2)}s`,
          delay: `${(Math.random() * 1.6).toFixed(2)}s`,
          size: 1.5 + Math.random() * 2.5,
          color: i % 4 === 0 ? '#FF1E2D' : i % 3 === 0 ? '#D9E1EA' : '#00A8FF',
          key: i
        };
      }),
    []
  );

  useEffect(() => {
    let cancelled = false;
    const bootTimer = window.setInterval(() => {
      if (!cancelled) setBootIndex((prev) => Math.min(prev + 1, BOOT_LINES.length - 1));
    }, 420);

    // Letters finish animating ~1.6s; switch to the logo phase shortly after.
    const logoTimer = window.setTimeout(() => {
      if (!cancelled) setShowLogo(true);
    }, 1750);

    const exitTimer = window.setTimeout(() => {
      if (!cancelled) setExiting(true);
    }, 2900);

    const completeTimer = window.setTimeout(() => {
      if (!cancelled) onComplete();
    }, 3500);

    return () => {
      cancelled = true;
      window.clearInterval(bootTimer);
      window.clearTimeout(logoTimer);
      window.clearTimeout(exitTimer);
      window.clearTimeout(completeTimer);
    };
  }, [onComplete]);

  const bootProgress = ((bootIndex + 1) / BOOT_LINES.length) * 100;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-hidden bg-[#020B1A] pointer-events-none">
      {/* Ambient radial vignette */}
      <div className="absolute inset-0 bg-radial-vignette" />
      {/* Technical grid plane */}
      <div className="absolute inset-0 bg-technical-grid opacity-60" />
      {/* Scanning bar with trailing beam */}
      <div className="absolute inset-0 intro-scanner-beam">
        <div className="relative w-full h-full">
          <div className="absolute inset-y-0 left-1/2 w-px bg-gradient-to-b from-transparent via-[#00A8FF]/60 to-transparent -translate-x-1/2" />
          <div className="absolute left-1/2 -translate-x-1/2 top-1/2 w-[92vw] max-w-4xl h-[2px] bg-[#00A8FF] shadow-[0_0_18px_rgba(0,168,255,0.9),0_0_40px_rgba(0,168,255,0.5)]" />
          <div className="absolute left-1/2 -translate-x-1/2 top-1/2 w-[92vw] max-w-4xl h-40 bg-gradient-to-b from-transparent via-[#00A8FF]/10 to-transparent" />
        </div>
      </div>

      {/* Radar sweep disc behind the emblem */}
      <div className="absolute rounded-full border border-[#007BFF]/25"
        style={{ width: 420, height: 420, left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}>
        <div className="absolute inset-0 rounded-full overflow-hidden">
          <div className="absolute inset-0 intro-radar"
            style={{ background: 'conic-gradient(from 0deg, rgba(0,168,255,0.25) 0deg, transparent 60deg)' }} />
        </div>
        <div className="absolute inset-6 rounded-full border border-[#007BFF]/20" />
        <div className="absolute inset-16 rounded-full border border-[#007BFF]/15" />
        <div className="absolute inset-0 rounded-full intro-radar-ping bg-[radial-gradient(circle,rgba(0,168,255,0.15)_0%,transparent_70%)]" />
      </div>

      {/* Floating charge particles */}
      {particles.map((p) => (
        <span
          key={p.key}
          className="absolute rounded-full intro-particle"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            width: p.size,
            height: p.size,
            background: p.color,
            boxShadow: `0 0 ${p.size * 2}px ${p.color}`,
            ['--drift-x' as string]: p.driftX,
            ['--drift-y' as string]: p.driftY,
            ['--dur' as string]: p.dur,
            ['--delay' as string]: p.delay
          }}
        />
      ))}

      {/* Center content: letters, then logo */}
      <div className={`relative flex flex-col items-center ${exiting ? 'intro-fade-out' : ''}`}>
        {/* Letter-by-letter AUREX */}
        {!showLogo && (
          <div className="flex items-center">
            {AUREX_LETTERS.map((letter, i) => (
              <span
                key={i}
                className="intro-letter font-headline font-black text-5xl sm:text-7xl font-mono text-[#EAF1F8]"
                style={{
                  textShadow: '0 0 22px rgba(0,168,255,0.6)',
                  animationDelay: `${0.25 + i * 0.18}s`
                }}
              >
                {letter}
              </span>
            ))}
          </div>
        )}

        {/* Logo pop-in */}
        {showLogo && (
          <div className="intro-logo-pop">
            <div className="relative flex items-center justify-center w-36 h-36 sm:w-48 sm:h-48"
              style={{ filter: 'drop-shadow(0 0 40px rgba(0,168,255,0.45))' }}>
              <AurexLogo size={170} withGlow />
            </div>
          </div>
        )}

        <p className="intro-sub-reveal opacity-0 mt-4 font-mono text-[10px] sm:text-xs tracking-[0.4em] text-[#00A8FF] text-center">
          AUTONOMOUS CYBER DEFENSE COMMAND PLATFORM
        </p>

        <div className="intro-sub-reveal opacity-0 mt-6 w-64 sm:w-80">
          <div className="h-[3px] bg-[#0B2A5E] border border-[#17406E] overflow-hidden">
            <div className="h-full bg-gradient-to-r from-[#00A8FF] via-[#5BC9FF] to-[#FF1E2D] intro-progress" />
          </div>
          <div className="mt-2 flex items-center justify-between font-mono text-[9px] tracking-widest text-[#9AA7B8]">
            <span>BOOT SEQUENCE</span>
            <span className="text-[#00A8FF]">{Math.round(bootProgress).toString().padStart(3, '0')}%</span>
          </div>
          <div className="mt-1 font-mono text-[10px] text-[#DEE7F0] truncate">
            {BOOT_LINES[bootIndex]}
            <span className="inline-block w-2 h-3 bg-[#00A8FF] ml-1 animate-pulse align-middle" />
          </div>
        </div>
      </div>

      {/* HUD corner brackets */}
      <div className="intro-corner absolute top-6 left-6 w-10 h-10 border-t-2 border-l-2 border-[#00A8FF]" />
      <div className="intro-corner absolute top-6 right-6 w-10 h-10 border-t-2 border-r-2 border-[#FF1E2D]" style={{ animationDelay: '0.4s' }} />
      <div className="intro-corner absolute bottom-6 left-6 w-10 h-10 border-b-2 border-l-2 border-[#FF1E2D]" style={{ animationDelay: '0.8s' }} />
      <div className="intro-corner absolute bottom-6 right-6 w-10 h-10 border-b-2 border-r-2 border-[#00A8FF]" style={{ animationDelay: '1.2s' }} />

      {/* Status strip at bottom */}
      <div className="absolute bottom-0 inset-x-0 px-6 py-3 flex items-center justify-between font-mono text-[9px] tracking-widest text-[#A7B4C4] border-t border-[#17406E]/50 bg-[#020B1A]/80">
        <span className="flex items-center space-x-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#FF1E2D] animate-pulse" />
          <span>DEFENSE CORE: ONLINE</span>
        </span>
        <span className="hidden sm:block">ENCRYPTION: AES-256-GCM</span>
        <span className="flex items-center space-x-2">
          <span>AUREX v2.4.0</span>
          <span className="text-[#FF1E2D]">●</span>
        </span>
      </div>
    </div>
  );
};