"use client";

import { useEffect, useSyncExternalStore, type ReactNode } from "react";
import { createPortal } from "react-dom";

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

  useEffect(() => {
    document.body.setAttribute("data-section-dock", "");
    return () => document.body.removeAttribute("data-section-dock");
  }, []);

  if (!mounted) return null;
  return createPortal(
    <nav aria-label={label} data-skeuo-dark="true" className="fb-section-dock no-scrollbar">
      {children}
    </nav>,
    document.body
  );
}
