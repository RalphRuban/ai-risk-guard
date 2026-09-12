import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

export interface BitsPillNavItem {
  id: string;
  label: React.ReactNode;
  locked?: boolean;
}

interface BitsPillNavProps {
  items: BitsPillNavItem[];
  activeId?: string;
  onSelect: (id: string) => void;
  className?: string;
}

const BitsPillNav: React.FC<BitsPillNavProps> = ({
  items,
  activeId,
  onSelect,
  className = ''
}) => {
  const circleRefs = useRef<Array<HTMLSpanElement | null>>([]);
  const tlRefs = useRef<Array<gsap.core.Timeline | null>>([]);
  const activeTweenRefs = useRef<Array<gsap.core.Tween | null>>([]);

  useEffect(() => {
    const layout = () => {
      circleRefs.current.forEach((circle, index) => {
        if (!circle?.parentElement) return;

        const pill = circle.parentElement as HTMLElement;
        const rect = pill.getBoundingClientRect();
        const { width: w, height: h } = rect;
        const R = ((w * w) / 4 + h * h) / (2 * h);
        const D = Math.ceil(2 * R) + 2;
        const delta = Math.ceil(R - Math.sqrt(Math.max(0, R * R - (w * w) / 4))) + 1;
        const originY = D - delta;

        circle.style.width = `${D}px`;
        circle.style.height = `${D}px`;
        circle.style.bottom = `-${delta}px`;

        gsap.set(circle, {
          xPercent: -50,
          scale: 0,
          transformOrigin: `50% ${originY}px`
        });

        const label = pill.querySelector<HTMLElement>('.pill-label');
        const hover = pill.querySelector<HTMLElement>('.pill-label-hover');

        if (label) gsap.set(label, { y: 0 });
        if (hover) gsap.set(hover, { y: Math.ceil(h + 100), opacity: 0 });

        tlRefs.current[index]?.kill();
        const tl = gsap.timeline({ paused: true });

        tl.to(circle, { scale: 1.2, xPercent: -50, duration: 2, ease: 'power3.easeOut', overwrite: 'auto' }, 0);
        if (label) tl.to(label, { y: -(h + 8), duration: 2, ease: 'power3.easeOut', overwrite: 'auto' }, 0);
        if (hover) tl.to(hover, { y: 0, opacity: 1, duration: 2, ease: 'power3.easeOut', overwrite: 'auto' }, 0);

        tlRefs.current[index] = tl;
      });
    };

    layout();

    const onResize = () => layout();
    window.addEventListener('resize', onResize);
    if (document.fonts) {
      document.fonts.ready.then(layout).catch(() => {});
    }

    return () => {
      window.removeEventListener('resize', onResize);
      tlRefs.current.forEach(tl => tl?.kill());
      tlRefs.current = [];
    };
  }, [items]);

  const handleEnter = (i: number) => {
    const tl = tlRefs.current[i];
    if (!tl) return;
    activeTweenRefs.current[i]?.kill();
    activeTweenRefs.current[i] = tl.tweenTo(tl.duration(), {
      duration: 0.3,
      ease: 'power3.easeOut',
      overwrite: 'auto'
    });
  };

  const handleLeave = (i: number) => {
    const tl = tlRefs.current[i];
    if (!tl) return;
    activeTweenRefs.current[i]?.kill();
    activeTweenRefs.current[i] = tl.tweenTo(0, {
      duration: 0.25,
      ease: 'power3.easeOut',
      overwrite: 'auto'
    });
  };

  return (
    <nav
      className={`relative items-stretch rounded-full px-1.5 py-1 bg-[#071A2E]/85 backdrop-blur-xl border border-[#17406E]/60 shadow-lg ${className}`}
      aria-label="Primary"
    >
      {items.map((item, i) => {
        const isActive = activeId === item.id;
        return (
          <button
            key={item.id}
            role="menuitem"
            onClick={() => onSelect(item.id)}
            onMouseEnter={() => handleEnter(i)}
            onMouseLeave={() => handleLeave(i)}
            className={`relative overflow-hidden inline-flex items-center justify-center h-full no-underline rounded-full box-border font-mono text-[11px] tracking-widest whitespace-nowrap cursor-pointer px-3 leading-[0] ${
              isActive ? 'text-[#00A8FF]' : 'text-[#A7B4C4]'
            }`}
            style={{ background: 'var(--pill-bg, #0B2A5E)' }}
          >
            <span
              className="hover-circle absolute left-1/2 bottom-0 rounded-full z-[1] block pointer-events-none"
              style={{ background: 'var(--base, #00A8FF)', willChange: 'transform' }}
              aria-hidden="true"
              ref={el => {
                circleRefs.current[i] = el;
              }}
            />
            <span className="label-stack relative inline-block leading-[1] z-[2]">
              <span className="pill-label relative z-[2] inline-block leading-[1]" style={{ willChange: 'transform' }}>
                {item.label}
              </span>
              <span
                className="pill-label-hover absolute left-0 top-0 z-[3] inline-block"
                style={{ color: 'var(--hover-text, #020B1A)', willChange: 'transform, opacity' }}
                aria-hidden="true"
              >
                {item.label}
              </span>
            </span>
            {isActive && (
              <span
                className="absolute left-1/2 -bottom-[5px] -translate-x-1/2 w-2.5 h-2.5 rounded-full z-[4] bg-[#00A8FF] shadow-[0_0_6px_#00A8FF]"
                aria-hidden="true"
              />
            )}
          </button>
        );
      })}
    </nav>
  );
};

export default BitsPillNav;