"use client";

import { useEffect } from "react";
import { prefersReducedMotion } from "@/lib/motion";

const PRESSABLE =
  'button, [role="button"], [role="switch"], [role="tab"], a.skeuo-btn-obsidian, a.skeuo-btn-accent, a.skeuo-btn-secondary, a.skeuo-btn-tone, a.fb-nav-item, a.fb-rail-btn, a.fb-icon-btn, a.fb-topbar-chip';
const BUSY_WATCH_MS = 15000;
const watching = new WeakSet<HTMLElement>();

function isDisabled(el: Element): boolean {
  return (el as HTMLButtonElement).disabled === true || el.getAttribute("aria-disabled") === "true";
}

/** The ripple and busy sheen draw in ::before; only use it where it is free and clipped. */
export function canPaintInside(el: HTMLElement): boolean {
  const style = getComputedStyle(el);
  if (style.overflow !== "hidden" && style.overflowX !== "hidden") return false;
  if (style.position === "static") return false;
  const before = getComputedStyle(el, "::before").content;
  return !before || before === "none" || before === "normal";
}

function restartClass(el: HTMLElement, cls: string, ms: number) {
  el.classList.remove(cls);
  void el.offsetWidth; // restart the CSS animation
  el.classList.add(cls);
  window.setTimeout(() => el.classList.remove(cls), ms);
}

/** Ripple from the pointer, like light spreading across a pressed key. */
export function ripple(el: HTMLElement, clientX: number, clientY: number) {
  if (prefersReducedMotion() || !canPaintInside(el)) return;
  const box = el.getBoundingClientRect();
  const x = clientX - box.left;
  const y = clientY - box.top;
  const reach = Math.hypot(Math.max(x, box.width - x), Math.max(y, box.height - y));
  el.style.setProperty("--fb-rx", `${x}px`);
  el.style.setProperty("--fb-ry", `${y}px`);
  el.style.setProperty("--fb-rs", String(Math.max(1, reach / 6)));
  restartClass(el, "fb-ripple", 620);
}

/**
 * After a click, a button that turns disabled is waiting on the server: show a
 * busy sheen until it is enabled again, then a short "settled" glow. Pages need
 * no changes; they already disable buttons while submitting.
 */
export function watchBusy(el: HTMLElement): () => void {
  if (isDisabled(el) || watching.has(el)) return () => undefined;
  watching.add(el);
  let busy = false;
  const update = () => {
    const now = isDisabled(el);
    if (now && !busy) {
      busy = true;
      el.classList.add("fb-busy");
      if (canPaintInside(el)) el.classList.add("fb-busy-sheen");
      el.setAttribute("aria-busy", "true");
    } else if (!now && busy) {
      busy = false;
      el.classList.remove("fb-busy", "fb-busy-sheen");
      el.removeAttribute("aria-busy");
      if (!prefersReducedMotion() && el.isConnected) restartClass(el, "fb-settle", 700);
      stop();
    }
  };
  const observer = new MutationObserver(update);
  observer.observe(el, { attributes: true, attributeFilter: ["disabled", "aria-disabled"] });
  const timer = window.setTimeout(() => {
    if (!busy) stop();
  }, BUSY_WATCH_MS);
  function stop() {
    watching.delete(el);
    observer.disconnect();
    window.clearTimeout(timer);
  }
  return stop;
}

/** Global, page-agnostic tactile feedback for every button in the app. */
export default function InteractionLayer() {
  useEffect(() => {
    const target = (ev: Event) => {
      const el = (ev.target as Element | null)?.closest?.(PRESSABLE);
      return el instanceof HTMLElement && !isDisabled(el) ? el : null;
    };
    const onPointerDown = (ev: PointerEvent) => {
      if (ev.button !== 0) return;
      const el = target(ev);
      if (el) ripple(el, ev.clientX, ev.clientY);
    };
    const onClick = (ev: MouseEvent) => {
      const el = target(ev);
      if (el && el.tagName === "BUTTON") watchBusy(el);
    };
    // Keyboard presses get the same "key goes down" depth as the mouse.
    const onKeyDown = (ev: KeyboardEvent) => {
      if (ev.key !== " " && ev.key !== "Enter") return;
      const el = target(ev);
      if (el) el.classList.add("fb-pressed");
    };
    const onKeyUp = () => {
      document.querySelectorAll(".fb-pressed").forEach((el) => el.classList.remove("fb-pressed"));
    };
    document.addEventListener("pointerdown", onPointerDown, { passive: true });
    document.addEventListener("click", onClick, true);
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", onKeyUp);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("click", onClick, true);
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onKeyUp);
    };
  }, []);
  return null;
}
