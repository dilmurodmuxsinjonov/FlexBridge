"use client";

import { useEffect, type RefObject } from "react";

/** True when the visitor asked the OS for less motion (or outside a browser). */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export const ACTIVE_ITEM_SELECTOR = '[aria-current="page"], .fb-nav-active';

/* ---------------------------------------------------------------------------
   Liquid glider physics (Issue #269)
   The highlight is a drop of liquid: its four edges are separate springs. The
   edge facing the direction of travel is stiff and runs ahead, the trailing
   edge is soft and follows, so the drop stretches toward the new item and then
   pulls itself together. While stretched it thins (volume is kept), and the
   lightly under-damped leading edge gives a small settle wobble. Interrupting
   mid-flight just retargets the springs from where the drop currently is.
   --------------------------------------------------------------------------- */

export interface Box {
  l: number;
  r: number;
  t: number;
  b: number;
}

type EdgeKey = keyof Box;
const EDGES: EdgeKey[] = ["l", "r", "t", "b"];

export interface LiquidState {
  pos: Box;
  vel: Box;
  /** Travel direction per axis at the last retarget: -1, 0 or 1. */
  dirX: number;
  dirY: number;
}

// Tuned (Issue #277, "3x faster"): k x9 => 3x shorter, settles in ~0.12-0.17 s
// with the same stretch shape (damping ratios unchanged).
const LEAD = { k: 8100, zeta: 0.66 };
const TRAIL = { k: 3420, zeta: 0.88 };
const NEUTRAL = { k: 5850, zeta: 0.8 };
const MAX_SPEED = 21000; // px/s

export function createLiquid(at: Box): LiquidState {
  return { pos: { ...at }, vel: { l: 0, r: 0, t: 0, b: 0 }, dirX: 0, dirY: 0 };
}

/** Point the springs at a new box; the edge facing the travel direction leads. */
export function retarget(state: LiquidState, target: Box): void {
  const cx = (state.pos.l + state.pos.r) / 2;
  const cy = (state.pos.t + state.pos.b) / 2;
  const tx = (target.l + target.r) / 2;
  const ty = (target.t + target.b) / 2;
  state.dirX = Math.abs(tx - cx) < 0.5 ? 0 : Math.sign(tx - cx);
  state.dirY = Math.abs(ty - cy) < 0.5 ? 0 : Math.sign(ty - cy);
}

function springFor(edge: EdgeKey, state: LiquidState) {
  const dir = edge === "l" || edge === "r" ? state.dirX : state.dirY;
  if (dir === 0) return NEUTRAL;
  const leading = (edge === "r" || edge === "b") === dir > 0;
  return leading ? LEAD : TRAIL;
}

/** Advance the drop by dt seconds (fixed 4 ms sub-steps). Returns true when settled. */
export function stepLiquid(state: LiquidState, target: Box, dt: number): boolean {
  const steps = Math.max(1, Math.ceil(dt / 0.004));
  const h = dt / steps;
  for (let s = 0; s < steps; s++) {
    for (const e of EDGES) {
      const { k, zeta } = springFor(e, state);
      const c = 2 * zeta * Math.sqrt(k);
      const a = k * (target[e] - state.pos[e]) - c * state.vel[e];
      // Viscosity: a drop never moves faster than MAX_SPEED, so long jumps stay smooth.
      state.vel[e] = Math.max(-MAX_SPEED, Math.min(MAX_SPEED, state.vel[e] + a * h));
      state.pos[e] += state.vel[e] * h;
    }
  }
  const settled = EDGES.every((e) => Math.abs(target[e] - state.pos[e]) < 0.25 && Math.abs(state.vel[e]) < 2);
  if (settled) {
    for (const e of EDGES) {
      state.pos[e] = target[e];
      state.vel[e] = 0;
    }
    state.dirX = 0;
    state.dirY = 0;
  }
  return settled;
}

/** Rendered box: a stretched drop gets thinner across the stretch (keeps its volume). */
export function liquidShape(state: LiquidState, target: Box): { x: number; y: number; w: number; h: number } {
  const p = state.pos;
  let w = Math.max(2, p.r - p.l);
  let h = Math.max(2, p.b - p.t);
  const tw = Math.max(1, target.r - target.l);
  const th = Math.max(1, target.b - target.t);
  const stretchX = Math.max(0, w - tw) / tw;
  const stretchY = Math.max(0, h - th) / th;
  const thinY = Math.min(0.24, stretchX * 0.35);
  const thinX = Math.min(0.24, stretchY * 0.35);
  const y = p.t + (h * thinY) / 2;
  const x = p.l + (w * thinX) / 2;
  h *= 1 - thinY;
  w *= 1 - thinX;
  return { x, y, w, h };
}

/* ---------------------------------------------------------------------------
   Droplet trail (Issue #271). Inside a ".fb-goo" layer an SVG metaball filter
   melts nearby shapes together, so drops near the pill hang on it by a liquid
   neck and drops further away read as separate beads. When the drop starts to
   move two large drops tear off its trailing edge and are pulled back slowly;
   while it travels it sheds small beads that stay behind and evaporate.
   --------------------------------------------------------------------------- */

export interface Drop {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r0: number;
  r: number;
  age: number;
  life: number;
  /** Spring stiffness toward the pill's trailing edge (0 = stays where shed). */
  k: number;
}

const DROP_MAX_SPEED = 4200;

/** Radius shrinks as the drop evaporates; 0 once its life is over. */
export function dropRadius(d: Drop): number {
  const left = 1 - d.age / d.life;
  return left <= 0 ? 0 : d.r0 * Math.pow(left, 0.7);
}

/** Advance one drop toward (tx, ty); returns false when it has evaporated. */
export function stepDrop(d: Drop, tx: number, ty: number, dt: number): boolean {
  d.age += dt;
  if (d.k > 0) {
    const c = 2 * 0.85 * Math.sqrt(d.k);
    d.vx = Math.max(-DROP_MAX_SPEED, Math.min(DROP_MAX_SPEED, d.vx + (d.k * (tx - d.x) - c * d.vx) * dt));
    d.vy = Math.max(-DROP_MAX_SPEED, Math.min(DROP_MAX_SPEED, d.vy + (d.k * (ty - d.y) - c * d.vy) * dt));
    d.x += d.vx * dt;
    d.y += d.vy * dt;
  }
  d.r = dropRadius(d);
  return d.r >= 1.5;
}

/** Point on the pill's trailing edge (where drops tear off / are pulled back to). */
export function trailingPoint(state: LiquidState, inset: number): { x: number; y: number } {
  const p = state.pos;
  const cx = (p.l + p.r) / 2;
  const cy = (p.t + p.b) / 2;
  if (state.dirX > 0) return { x: p.l + inset, y: cy };
  if (state.dirX < 0) return { x: p.r - inset, y: cy };
  if (state.dirY > 0) return { x: cx, y: p.t + inset };
  if (state.dirY < 0) return { x: cx, y: p.b - inset };
  return { x: cx, y: cy };
}

/**
 * Moves one highlight ("glider") under the active item of a menu as a drop of
 * liquid. Works with menus whose items are rendered elsewhere (portal pages):
 * it only watches the DOM for the active marker. Position is written to inline
 * styles from a requestAnimationFrame loop, never React state; the first
 * placement and reduced-motion visitors jump straight to the target.
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
    let measureFrame = 0;
    let animFrame = 0;
    let waitFrame = 0;
    let lastTime = 0;
    let last: HTMLElement | null = null;
    let liquid: LiquidState | null = null;
    let target: Box | null = null;

    // Droplets live in the ".fb-goo" layer around the glider (if the menu has one).
    const goo = glider.parentElement?.classList.contains("fb-goo") ? glider.parentElement : null;
    const pool: HTMLSpanElement[] = [];
    if (goo) {
      for (let i = 0; i < 14; i++) {
        const el = document.createElement("span");
        el.className = "fb-drop";
        el.setAttribute("aria-hidden", "true");
        goo.appendChild(el);
        pool.push(el);
      }
    }
    let drops: (Drop & { el: HTMLSpanElement })[] = [];
    let shedClock = 0;
    let shedFlip = false;
    const thickness = () => (target ? Math.min(target.r - target.l, target.b - target.t) : 30);
    const hideDrop = (el: HTMLSpanElement) => {
      el.style.width = "0px";
      el.style.height = "0px";
    };
    const spawn = (x: number, y: number, r0: number, life: number, k: number) => {
      const el = pool.find((e) => !drops.some((d) => d.el === e));
      if (!el) return;
      drops.push({ x, y, vx: 0, vy: 0, r0, r: r0, age: 0, life, k, el });
    };
    const clearDrops = () => {
      drops.forEach((d) => hideDrop(d.el));
      drops = [];
    };
    const stepDrops = (dt: number) => {
      if (!liquid) return;
      drops = drops.filter((d) => {
        const tp = trailingPoint(liquid as LiquidState, d.r0);
        const alive = stepDrop(d, tp.x, tp.y, dt);
        if (!alive) {
          hideDrop(d.el);
          return false;
        }
        d.el.style.width = `${d.r * 2}px`;
        d.el.style.height = `${d.r * 2}px`;
        d.el.style.transform = `translate(${d.x - d.r}px, ${d.y - d.r}px)`;
        return true;
      });
    };

    // Items the liquid currently covers get dark text; the rest stay light, so
    // a label changes colour exactly when the drop flows over it.
    const markCovered = (s: { x: number; y: number; w: number; h: number }) => {
      for (const el of Array.from(box.children) as HTMLElement[]) {
        if (el === glider || el.classList.contains("fb-goo")) continue;
        const ox = Math.min(el.offsetLeft + el.offsetWidth, s.x + s.w) - Math.max(el.offsetLeft, s.x);
        const oy = Math.min(el.offsetTop + el.offsetHeight, s.y + s.h) - Math.max(el.offsetTop, s.y);
        const covered = ox > 0 && oy > 0 && (ox * oy) / Math.max(1, el.offsetWidth * el.offsetHeight) >= 0.5;
        if (covered !== el.hasAttribute("data-under-glider")) el.toggleAttribute("data-under-glider", covered);
      }
    };

    const draw = () => {
      if (!liquid || !target) return;
      const s = liquidShape(liquid, target);
      glider.style.width = `${s.w}px`;
      glider.style.height = `${s.h}px`;
      glider.style.transform = `translate(${s.x}px, ${s.y}px)`;
      markCovered(s);
    };

    const tick = (now: number) => {
      if (!liquid || !target) return;
      // A long frame (page busy) advances the drop at most 24 ms, so it never leaps.
      const dt = Math.min(0.024, lastTime ? (now - lastTime) / 1000 : 0.016);
      lastTime = now;
      const settled = stepLiquid(liquid, target, dt);
      if (goo && !settled) {
        // While travelling fast the drop sheds small beads from its trailing edge.
        const speed = Math.max(...Object.values(liquid.vel).map(Math.abs));
        shedClock += dt;
        if (speed > 3600 && shedClock > 0.02) {
          shedClock = 0;
          shedFlip = !shedFlip;
          const t = thickness();
          const tp = trailingPoint(liquid, t * 0.3);
          const wobble = (shedFlip ? 1 : -1) * t * 0.07;
          spawn(tp.x + (liquid.dirY ? wobble : 0), tp.y + (liquid.dirX ? wobble : 0), t * (shedFlip ? 0.17 : 0.13), 0.1, 0);
        }
      }
      draw();
      stepDrops(dt);
      animFrame = settled && drops.length === 0 ? 0 : requestAnimationFrame(tick);
    };

    // A route or tab change renders a lot at once; start flowing after one calm
    // frame (or 30 ms at most) so the motion is not chopped by dropped frames.
    const startWhenSmooth = () => {
      cancelAnimationFrame(waitFrame);
      const begin = performance.now();
      let prev = 0;
      let calm = 0;
      const wait = (now: number) => {
        calm = prev && now - prev < 24 ? calm + 1 : 0;
        prev = now;
        if (calm >= 1 || now - begin > 30) {
          lastTime = 0;
          animFrame = requestAnimationFrame(tick);
          return;
        }
        waitFrame = requestAnimationFrame(wait);
      };
      waitFrame = requestAnimationFrame(wait);
    };

    const place = () => {
      cancelAnimationFrame(measureFrame);
      measureFrame = requestAnimationFrame(() => {
        const active = box.querySelector<HTMLElement>(selector);
        if (!active || active === glider) {
          glider.style.opacity = "0";
          last = null;
          return;
        }
        const next: Box = {
          l: active.offsetLeft,
          r: active.offsetLeft + active.offsetWidth,
          t: active.offsetTop,
          b: active.offsetTop + active.offsetHeight,
        };
        glider.style.opacity = "1";
        if (goo) {
          goo.style.width = `${box.scrollWidth}px`;
          goo.style.height = `${box.scrollHeight}px`;
        }
        const jump = !liquid || prefersReducedMotion() || typeof requestAnimationFrame !== "function";
        target = next;
        if (jump || !liquid) {
          liquid = createLiquid(next);
          cancelAnimationFrame(animFrame);
          cancelAnimationFrame(waitFrame);
          animFrame = 0;
          clearDrops();
          draw();
        } else {
          const wasIdle = liquid.dirX === 0 && liquid.dirY === 0;
          retarget(liquid, next);
          if (goo && wasIdle && (liquid.dirX || liquid.dirY)) {
            // One drop tears off the trailing edge and is pulled back quickly (kept subtle).
            const t = Math.min(liquid.pos.r - liquid.pos.l, liquid.pos.b - liquid.pos.t);
            const tp = trailingPoint(liquid, t * 0.4);
            spawn(tp.x, tp.y, t * 0.3, 0.16, 810);
          }
          if (!animFrame) startWhenSmooth();
        }
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
    mutations.observe(box, { subtree: true, childList: true, attributes: true, attributeFilter: ["class", "aria-current", "data-active"] });
    const resize = typeof ResizeObserver !== "undefined" ? new ResizeObserver(place) : null;
    resize?.observe(box);
    window.addEventListener("resize", place);
    return () => {
      cancelAnimationFrame(measureFrame);
      cancelAnimationFrame(animFrame);
      cancelAnimationFrame(waitFrame);
      mutations.disconnect();
      resize?.disconnect();
      window.removeEventListener("resize", place);
      box.removeAttribute("data-glider");
      pool.forEach((el) => el.remove());
    };
  }, [containerRef, gliderRef, selector, ready]);
}
