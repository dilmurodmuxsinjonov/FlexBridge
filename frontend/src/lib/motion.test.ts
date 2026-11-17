import { describe, expect, it } from "vitest";
import { createLiquid, dropRadius, liquidShape, retarget, stepDrop, stepLiquid, trailingPoint, type Box, type Drop } from "./motion";

const A: Box = { l: 0, r: 100, t: 0, b: 36 };
const B: Box = { l: 300, r: 380, t: 0, b: 36 };

function run(target: Box, from = A, ms = 1500) {
  const s = createLiquid(from);
  retarget(s, target);
  const frames: { l: number; r: number; w: number; h: number }[] = [];
  let settledAt = -1;
  for (let t = 0; t < ms; t += 16) {
    const done = stepLiquid(s, target, 0.016);
    const shape = liquidShape(s, target);
    frames.push({ l: s.pos.l, r: s.pos.r, w: shape.w, h: shape.h });
    if (done && settledAt < 0) settledAt = t;
  }
  return { s, frames, settledAt };
}

describe("liquid glider", () => {
  it("leading edge runs ahead, so the drop stretches toward the new item", () => {
    const { frames } = run(B);
    const early = frames[1]; // ~32 ms (springs are 3x faster since #277)
    expect(early.r - A.r).toBeGreaterThan(early.l - A.l + 40);
    const widest = Math.max(...frames.map((f) => f.r - f.l));
    expect(widest).toBeGreaterThan(160);
  });

  it("thins while stretched and keeps its height when at rest", () => {
    const { frames } = run(B);
    const minH = Math.min(...frames.map((f) => f.h));
    expect(minH).toBeLessThan(36);
    expect(minH).toBeGreaterThan(36 * 0.74);
    expect(frames[frames.length - 1].h).toBeCloseTo(36, 5);
  });

  it("settles exactly on the target in well under a second", () => {
    const { s, settledAt } = run(B);
    expect(settledAt).toBeGreaterThan(0);
    // Issues #275/#277: the move must feel quick (user: "3x faster").
    expect(settledAt).toBeLessThan(200);
    expect(s.pos).toEqual(B);
  });

  it("moving left mirrors the stretch (left edge leads)", () => {
    const { frames } = run(A, B);
    const early = frames[2];
    expect(B.l - early.l).toBeGreaterThan(B.r - early.r + 40);
  });

  it("retargets mid-flight from where the drop is, without jumping", () => {
    const s = createLiquid(A);
    retarget(s, B);
    for (let i = 0; i < 3; i++) stepLiquid(s, B, 0.016);
    const before = { ...s.pos };
    retarget(s, A);
    stepLiquid(s, A, 0.004);
    // No teleport: one 4 ms step moves at most MAX_SPEED (21000 px/s) x 4 ms = 84 px.
    expect(Math.abs(s.pos.l - before.l)).toBeLessThanOrEqual(84);
    expect(Math.abs(s.pos.r - before.r)).toBeLessThanOrEqual(84);
    for (let i = 0; i < 120; i++) stepLiquid(s, A, 0.016);
    expect(s.pos).toEqual(A);
  });

  it("works vertically for the rail knob", () => {
    const top: Box = { l: 0, r: 40, t: 0, b: 40 };
    const down: Box = { l: 0, r: 40, t: 200, b: 240 };
    const { frames } = run(down, top);
    const early = frames[2];
    expect(early.w).toBeLessThan(40);
  });
});

describe("droplet trail", () => {
  const drop = (over: Partial<Drop> = {}): Drop => ({ x: 0, y: 18, vx: 0, vy: 0, r0: 12, r: 12, age: 0, life: 1, k: 0, ...over });

  it("a shed bead stays where it fell and evaporates", () => {
    const d = drop();
    const sizes: number[] = [];
    let alive = true;
    for (let i = 0; i < 80 && alive; i++) {
      alive = stepDrop(d, 300, 18, 0.016);
      sizes.push(d.r);
    }
    expect(d.x).toBe(0);
    expect(sizes[5]).toBeLessThan(12);
    expect(sizes[20]).toBeLessThan(sizes[5]);
    expect(alive).toBe(false);
  });

  it("a torn-off drop is pulled back toward the trailing edge while shrinking", () => {
    const d = drop({ k: 26, life: 1.1 });
    for (let i = 0; i < 20; i++) stepDrop(d, 200, 18, 0.016);
    expect(d.x).toBeGreaterThan(20);
    expect(d.x).toBeLessThan(200);
    expect(d.r).toBeLessThan(12);
    expect(dropRadius({ ...d, age: 2 })).toBe(0);
  });

  it("drops tear off the edge opposite to the travel direction", () => {
    const s = createLiquid({ l: 0, r: 100, t: 0, b: 36 });
    retarget(s, { l: 300, r: 380, t: 0, b: 36 });
    expect(trailingPoint(s, 10)).toEqual({ x: 10, y: 18 });
    retarget(s, { l: -300, r: -200, t: 0, b: 36 });
    expect(trailingPoint(s, 10)).toEqual({ x: 90, y: 18 });
    const rail = createLiquid({ l: 0, r: 40, t: 0, b: 40 });
    retarget(rail, { l: 0, r: 40, t: 200, b: 240 });
    expect(trailingPoint(rail, 5)).toEqual({ x: 20, y: 5 });
  });
});
