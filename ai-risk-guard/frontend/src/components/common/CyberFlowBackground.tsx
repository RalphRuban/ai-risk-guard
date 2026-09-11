import React, { useEffect, useRef } from 'react';

export const CyberFlowBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    // Mouse coordinates for gentle interactive flow deflection
    let mouseX = width / 2;
    let mouseY = height / 2;
    const handleMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Particle flow stream (10% Red, 10% Silver, surrounded by 80% Navy)
    const particleCount = Math.min(80, Math.floor((width * height) / 18000));
    const particles = Array.from({ length: particleCount }, (_, idx) => {
      // 50% Silver metallic, 50% Threat red
      const isRed = idx % 2 === 0;
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.2) * 0.8 + 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        length: 15 + Math.random() * 25,
        size: 1 + Math.random() * 1.5,
        alpha: 0.2 + Math.random() * 0.5,
        isRed,
        color: isRed ? '#FF2A4B' : '#CBD5E1',
        headColor: isRed ? '#FF6B81' : '#FFFFFF'
      };
    });

    let t = 0;
    const render = () => {
      t += 0.008;

      // Crisp dark cyber clear (no long trailing blur)
      ctx.fillStyle = 'rgba(2, 7, 22, 0.92)';
      ctx.fillRect(0, 0, width, height);

      // 1. Draw organic flowing cyber wave streams (Subtle & clean)
      ctx.lineWidth = 1.2;
      for (let w = 0; w < 4; w++) {
        ctx.beginPath();
        const baseOffset = (w * height) / 4.2;
        
        if (w === 1) {
          ctx.strokeStyle = `rgba(255, 42, 75, 0.22)`;
        } else {
          ctx.strokeStyle = `rgba(0, 180, 255, ${0.08 + w * 0.03})`;
        }

        for (let x = 0; x < width; x += 25) {
          const wave1 = Math.sin(x * 0.0028 + t + w) * 40;
          const wave2 = Math.cos(x * 0.0014 - t * 0.4) * 25;
          const distToMouse = Math.hypot(x - mouseX, (baseOffset + wave1) - mouseY);
          const mouseDeflect = distToMouse < 200 ? ((200 - distToMouse) / 200) * 20 : 0;
          const y = baseOffset + wave1 + wave2 - mouseDeflect;

          if (x === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      }

      // 2. Draw clean floating cyber nodes (NO tails/streaks)
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx * 0.7;
        p.y += p.vy + Math.sin(t * 1.5 + p.x * 0.01) * 0.3;

        // Wrap around boundaries
        if (p.x > width + 20) p.x = -20;
        if (p.x < -20) p.x = width + 20;
        if (p.y > height + 20) p.y = -20;
        if (p.y < -20) p.y = height + 20;

        // Clean luminous orb (no tail)
        const nodeRadius = p.size * 1.4;
        ctx.fillStyle = p.isRed 
          ? `rgba(255, 42, 75, ${p.alpha * 0.9})` 
          : `rgba(0, 207, 255, ${p.alpha * 0.85})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, nodeRadius, 0, Math.PI * 2);
        ctx.fill();

        // Subtle soft outer corona
        ctx.fillStyle = p.isRed 
          ? `rgba(255, 42, 75, ${p.alpha * 0.25})` 
          : `rgba(0, 207, 255, ${p.alpha * 0.22})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, nodeRadius * 2.5, 0, Math.PI * 2);
        ctx.fill();
      }

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      {/* 80% Navy Blue Void Atmosphere */}
      <div className="absolute inset-0 bg-[#020716]" />

      {/* 80% Dominant Deep Navy Glow Orbs */}
      <div className="absolute -top-32 -left-32 w-[600px] h-[600px] rounded-full bg-[#0B2556]/30 blur-[140px] animate-pulse" />
      <div className="absolute -bottom-40 left-1/3 w-[800px] h-[800px] rounded-full bg-[#081D45]/35 blur-[160px] animate-pulse" style={{ animationDuration: '9s' }} />

      {/* 10% Cyber Red Threat Glow Accent Orb */}
      <div className="absolute top-1/4 -right-28 w-[500px] h-[500px] rounded-full bg-[#FF2A4B]/12 blur-[150px] animate-pulse" style={{ animationDuration: '7s' }} />

      {/* 10% Metallic Silver Sheen Accent */}
      <div className="absolute top-2/3 -left-20 w-[450px] h-[450px] rounded-full bg-[#CBD5E1]/8 blur-[160px] animate-pulse" style={{ animationDuration: '8s' }} />

      {/* Procedural Flow Canvas */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full opacity-80" />

      {/* Technical Navy Grid Overlay */}
      <div className="absolute inset-0 bg-technical-grid opacity-35" />

      {/* Cinematic Scanlines */}
      <div className="absolute inset-0 scanline-overlay opacity-20" />
    </div>
  );
};
