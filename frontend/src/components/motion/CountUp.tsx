"use client";

import { useLayoutEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/motion";

/**
 * A number that counts to its value like a mechanical counter: from 0 on
 * first paint, from the previous value on updates. The DOM text is written
 * directly (no re-render per frame) and server HTML already holds the final
 * value, so screen readers and no-JS views always read the real number.
 */
export default function CountUp({ value, duration = 240 }: { value: number; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const shown = useRef(0);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const target = Number.isFinite(value) ? value : 0;
    const from = shown.current;
    if (from === target || prefersReducedMotion() || typeof requestAnimationFrame !== "function") {
      el.textContent = String(target);
      shown.current = target;
      return;
    }
    let frame = 0;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const current = Math.round(from + (target - from) * eased);
      el.textContent = String(current);
      shown.current = current;
      if (t < 1) frame = requestAnimationFrame(step);
    };
    el.textContent = String(from);
    frame = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(frame);
      el.textContent = String(target);
      shown.current = target;
    };
  }, [value, duration]);

  return (
    <span ref={ref} className="tabular-nums">
      {value}
    </span>
  );
}
