"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { prefersReducedMotion } from "@/lib/motion";

/** A soft light band sweeps down the screen, like a display refreshing. */
export function sweepScreen(sheen: HTMLElement | null): void {
  if (!sheen || typeof sheen.animate !== "function" || prefersReducedMotion()) return;
  sheen.animate(
    [
      { backgroundPosition: "0 -40%", opacity: 0 },
      { opacity: 1, offset: 0.2 },
      { backgroundPosition: "0 140%", opacity: 0 },
    ],
    { duration: 700, easing: "cubic-bezier(0.4, 0, 0.2, 1)" }
  );
}

const CARD_SELECTOR = ".skeuo-card, .skeuo-stage, .fb-panel, .fb-ink-card";

/**
 * Staggered "power-on" of the cards visible in the slab, like the reference
 * video when a section changes. Only outermost cards in the viewport animate,
 * nothing is remounted (form state survives) and the transform is dropped as
 * soon as each animation ends.
 */
export function revealCards(root: HTMLElement): number {
  if (typeof window === "undefined" || typeof root.animate !== "function") return 0;
  if (prefersReducedMotion()) return 0;
  const viewport = window.innerHeight || 800;
  const cards = Array.from(root.querySelectorAll<HTMLElement>(CARD_SELECTOR))
    .filter((el) => {
      const parentCard = el.parentElement?.closest(CARD_SELECTOR);
      if (parentCard && root.contains(parentCard)) return false;
      const box = el.getBoundingClientRect();
      return box.width > 0 && box.height > 0 && box.top < viewport && box.bottom > 0;
    })
    .slice(0, 18);
  cards.forEach((el, i) => {
    el.animate(
      [
        { opacity: 0, transform: "translateY(14px) scale(0.985)" },
        { opacity: 1, transform: "none" },
      ],
      { duration: 520, delay: i * 45, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)", fill: "backwards" }
    );
  });
  return cards.length;
}

/** The single screen slab (with corner screws) every page renders into. */
export default function AppStage({ children }: { children: ReactNode }) {
  const slabRef = useRef<HTMLDivElement>(null);
  const sheenRef = useRef<HTMLSpanElement>(null);
  const pathname = usePathname();

  useEffect(() => {
    let frame = 0;
    const schedule = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (slabRef.current) revealCards(slabRef.current);
        sweepScreen(sheenRef.current);
      });
    };
    schedule();
    window.addEventListener("flexbridge:portal-tab-changed", schedule);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("flexbridge:portal-tab-changed", schedule);
    };
  }, [pathname]);

  return (
    <div className="fb-stage-shell">
      <div ref={slabRef} className="fb-slab">
        <span ref={sheenRef} className="fb-slab-sheen" aria-hidden="true" />
        {children}
      </div>
    </div>
  );
}
