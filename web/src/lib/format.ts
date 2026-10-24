"use client";
import { useEffect, useRef, useState } from "react";

export const usd = (cents: number) =>
  (cents < 0 ? "-$" : "$") + (Math.abs(cents) / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const ms = (v: number) => (v < 1 ? `${Math.round(v * 1000)}µs` : v < 100 ? `${v.toFixed(1)}ms` : `${Math.round(v).toLocaleString()}ms`);

/** Eases a displayed number toward `target` (for the jackpot counter). */
export function useTween(target: number, durationMs = 900): number {
  const [val, setVal] = useState(target);
  const fromRef = useRef(target);
  const valRef = useRef(target);
  valRef.current = val;

  useEffect(() => {
    fromRef.current = valRef.current;
    const from = fromRef.current;
    if (from === target) return;
    const t0 = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / durationMs);
      const e = 1 - Math.pow(1 - p, 3);
      setVal(from + (target - from) * e);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);

  return val;
}
