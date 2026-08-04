import { useCallback, useEffect, useRef, useState } from 'react';

interface UseAnimateNumberOptions {
  duration?: number;
  delay?: number;
}

export function useAnimateNumber(target: number, options: UseAnimateNumberOptions = {}) {
  const { duration = 1000, delay = 0 } = options;
  const [value, setValue] = useState(0);
  const frameRef = useRef<number>(0);

  const animate = useCallback(() => {
    const startTime = performance.now() + delay;
    const tick = (now: number) => {
      const elapsed = now - startTime;
      if (elapsed < 0) {
        frameRef.current = requestAnimationFrame(tick);
        return;
      }
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setValue(Math.round(eased * target));
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick);
      }
    };
    frameRef.current = requestAnimationFrame(tick);
  }, [target, duration, delay]);

  useEffect(() => {
    animate();
    return () => cancelAnimationFrame(frameRef.current);
  }, [animate]);

  return value;
}
