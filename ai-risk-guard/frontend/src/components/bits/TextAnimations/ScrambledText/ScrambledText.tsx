import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

export interface ScrambledTextProps {
  radius?: number;
  duration?: number;
  speed?: number;
  scrambleChars?: string;
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

const ScrambledText: React.FC<ScrambledTextProps> = ({
  radius = 120,
  duration = 1.1,
  speed = 0.5,
  scrambleChars = '!<>-_\\/[]{}—=+*^?#________',
  className = '',
  style = {},
  children
}) => {
  const textRef = useRef<HTMLSpanElement | null>(null);
  const textValue = typeof children === 'string' ? children : '';

  useEffect(() => {
    const el = textRef.current;
    if (!el || !textValue) return;

    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    el.textContent = textValue;

    const randomChar = () =>
      scrambleChars[Math.floor(Math.random() * scrambleChars.length)];

    const render = (p: number) => {
      const resolved = Math.max(0, Math.min(textValue.length, Math.floor(p * textValue.length)));
      let out = '';
      for (let i = 0; i < textValue.length; i++) {
        if (i < resolved) {
          out += textValue[i];
        } else {
          out += textValue[i] === ' ' ? ' ' : randomChar();
        }
      }
      el.textContent = out;
    };

    if (reduced) return undefined;

    const state = { p: 0 };
    let currentTween: ReturnType<typeof gsap.to> | null = null;

    const runDecrypt = (from: number, delay: number, dur: number) => {
      currentTween?.kill();
      state.p = from;
      currentTween = gsap.to(state, {
        p: 1,
        duration: dur,
        delay,
        ease: 'power1.out',
        overwrite: true,
        onUpdate: () => render(state.p)
      });
      return currentTween;
    };

    runDecrypt(0, 0.35, duration / Math.max(0.25, speed));

    let lastTrigger = 0;
    const handleMove = (e: PointerEvent) => {
      const now = performance.now();
      if (now - lastTrigger < 140) return;

      const node = el.firstChild;
      if (!node || node.nodeType !== Node.TEXT_NODE) return;
      const len = node.textContent?.length ?? 0;
      if (len === 0) return;

      for (let i = 0; i < Math.min(textValue.length, len); i++) {
        let rect: DOMRect;
        try {
          const range = document.createRange();
          range.setStart(node, i);
          range.setEnd(node, i + 1);
          rect = range.getBoundingClientRect();
        } catch {
          continue;
        }
        if (!rect.width && !rect.height) continue;

        const dx = e.clientX - (rect.left + rect.width / 2);
        const dy = e.clientY - (rect.top + rect.height / 2);
        if (Math.hypot(dx, dy) < radius) {
          lastTrigger = now;
          const from = Math.min(0.8, i / textValue.length);
          const dur = Math.max(0.2, Math.min(0.55, duration * 0.4));
          runDecrypt(from, 0, dur);
          break;
        }
      }
    };

    el.addEventListener('pointermove', handleMove);

    return () => {
      el.removeEventListener('pointermove', handleMove);
      currentTween?.kill();
      gsap.killTweensOf(state);
      el.textContent = textValue;
    };
  }, [radius, duration, speed, scrambleChars, textValue]);

  return <span ref={textRef} className={className} style={style} />;
};

export default ScrambledText;