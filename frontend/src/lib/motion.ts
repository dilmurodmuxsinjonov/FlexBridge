"use client";

import { useEffect, type RefObject } from "react";

/** True when the visitor asked the OS for less motion (or outside a browser). */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export const ACTIVE_ITEM_SELECTOR = '[aria-current="page"], .fb-nav-active';

/**
 * Slides one highlight ("glider") under the active item of a menu, so a section
 * change reads as one physical pill moving instead of two pills swapping colour.
 * Works with menus whose items are rendered elsewhere (portal pages): it only
 * watches the DOM for the active marker. The glider is positioned with inline
 * styles, never React state, and transitions are enabled after the first
 * placement so it does not fly in from the corner.
 */
export function useGlider(
  containerRef: RefObject<HTMLElement | null>,
  gliderRef: RefObject<HTMLElement | null>,
  selector: string = ACTIVE_ITEM_SELECTOR,
  /** Re-attach when the menu mounts later (portals, conditional menus). */
  ready: boolean = true
): void {
  useEffect(() => {
    const box = containerRef.current;
    const glider = gliderRef.current;
    if (!ready || !box || !glider) return;
    let frame = 0;
    let last: HTMLElement | null = null;

    const place = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const active = box.querySelector<HTMLElement>(selector);
        if (!active || active === glider) {
          glider.style.opacity = "0";
          last = null;
          return;
        }
        glider.style.opacity = "1";
        glider.style.width = `${active.offsetWidth}px`;
        glider.style.height = `${active.offsetHeight}px`;
        glider.style.transform = `translate(${active.offsetLeft}px, ${active.offsetTop}px)`;
        if (!box.hasAttribute("data-glider")) {
          requestAnimationFrame(() => box.setAttribute("data-glider", "on"));
        }
        if (active !== last) {
          const scrollable = box.scrollWidth > box.clientWidth + 2 || box.scrollHeight > box.clientHeight + 2;
          if (last && scrollable && typeof active.scrollIntoView === "function") {
            active.scrollIntoView({ block: "nearest", inline: "center", behavior: prefersReducedMotion() ? "auto" : "smooth" });
          }
          last = active;
        }
      });
    };

    place();
    const mutations = new MutationObserver(place);
    mutations.observe(box, { subtree: true, childList: true, attributes: true, attributeFilter: ["class", "aria-current"] });
    const resize = typeof ResizeObserver !== "undefined" ? new ResizeObserver(place) : null;
    resize?.observe(box);
    window.addEventListener("resize", place);
    return () => {
      cancelAnimationFrame(frame);
      mutations.disconnect();
      resize?.disconnect();
      window.removeEventListener("resize", place);
      box.removeAttribute("data-glider");
    };
  }, [containerRef, gliderRef, selector, ready]);
}
