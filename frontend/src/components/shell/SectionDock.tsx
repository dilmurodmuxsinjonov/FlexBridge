"use client";

import { useEffect, useRef, useSyncExternalStore, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useGlider } from "@/lib/motion";

const subscribeNoop = () => () => {};

/**
 * Re-houses a portal's section menu in the floating dark capsule at the bottom
 * of the screen (device-shell design, Issue #263). The buttons keep their own
 * click handlers, role checks and counters; only their place on screen moves.
 * It renders into document.body so animated or blurred ancestors never trap it,
 * and marks the body so the generic bottom navigation steps aside.
 */
export default function SectionDock({ label, children }: { label: string; children: ReactNode }) {
  const mounted = useSyncExternalStore(subscribeNoop, () => true, () => false);
  const navRef = useRef<HTMLElement>(null);
  const gliderRef = useRef<HTMLSpanElement>(null);
  // The light pill slides between sections instead of jumping.
  useGlider(navRef, gliderRef, undefined, mounted);

  useEffect(() => {
    document.body.setAttribute("data-section-dock", "");
    return () => document.body.removeAttribute("data-section-dock");
  }, []);

  if (!mounted) return null;
  return createPortal(
    <nav ref={navRef} aria-label={label} data-skeuo-dark="true" className="fb-section-dock no-scrollbar">
      <span className="fb-goo" aria-hidden="true">
        <span ref={gliderRef} className="fb-glider fb-glider-pill" />
      </span>
      {children}
    </nav>,
    document.body
  );
}
