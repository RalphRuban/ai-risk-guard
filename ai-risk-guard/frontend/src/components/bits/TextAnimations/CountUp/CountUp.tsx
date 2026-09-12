import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface CountUpProps {
  to: number;
  from?: number;
  direction?: 'up' | 'down';
  delay?: number;
  duration?: number;
  className?: string;
  separator?: string;
  startWhen?: boolean;
  onStart?: () => void;
  onEnd?: () => void;
}

export default function CountUp({
  to,
  from = 0,
  direction = 'up',
  delay = 0,
  duration = 2,
  className = '',
  separator = '',
  startWhen = true,
  onStart,
  onEnd
}: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);

  const getDecimalPlaces = (num: number): number => {
    const str = num.toString();
    if (str.includes('.')) {
      const decimals = str.split('.')[1];
      if (parseInt(decimals) !== 0) {
        return decimals.length;
      }
    }
    return 0;
  };

  const maxDecimals = Math.max(getDecimalPlaces(from), getDecimalPlaces(to));

  const formatValue = (latest: number): string => {
    const hasDecimals = maxDecimals > 0;

    const options: Intl.NumberFormatOptions = {
      useGrouping: !!separator,
      minimumFractionDigits: hasDecimals ? maxDecimals : 0,
      maximumFractionDigits: hasDecimals ? maxDecimals : 0
    };

    const formattedNumber = Intl.NumberFormat('en-US', options).format(latest);
    return separator ? formattedNumber.replace(/,/g, separator) : formattedNumber;
  };

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const startAt = direction === 'down' ? to : from;
    const endAt = direction === 'down' ? from : to;

    el.textContent = formatValue(startAt);

    if (!startWhen) return;

    const proxy = { val: startAt };

    const tween = gsap.to(proxy, {
      val: endAt,
      duration,
      ease: 'power2.out',
      delay,
      onStart: () => {
        if (typeof onStart === 'function') onStart();
      },
      onUpdate: () => {
        el.textContent = formatValue(proxy.val);
      },
      onComplete: () => {
        el.textContent = formatValue(endAt);
        if (typeof onEnd === 'function') onEnd();
      },
      scrollTrigger: {
        trigger: el,
        start: 'top 90%',
        once: true,
        toggleActions: 'play none none none'
      }
    });

    return () => {
      tween.scrollTrigger?.kill();
      tween.kill();
    };
  }, [to, from, direction, duration, delay, separator, startWhen, maxDecimals, onStart, onEnd]);

  return <span ref={ref} className={className} />;
}