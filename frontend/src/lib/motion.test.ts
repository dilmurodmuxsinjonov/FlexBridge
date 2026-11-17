import { describe, expect, it } from "vitest";
import { createLiquid, liquidShape, retarget, stepLiquid, type Box } from "./motion";

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
    const early = frames[6];
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
    expect(settledAt).toBeLessThan(900);
    expect(s.pos).toEqual(B);
  });

  it("moving left mirrors the stretch (left edge leads)", () => {
    const { frames } = run(A, B);
    const early = frames[6];
    expect(B.l - early.l).toBeGreaterThan(B.r - early.r + 40);
  });

  it("retargets mid-flight from where the drop is, without jumping", () => {
    const s = createLiquid(A);
    retarget(s, B);
    for (let i = 0; i < 8; i++) stepLiquid(s, B, 0.016);
    const before = { ...s.pos };
    retarget(s, A);
    stepLiquid(s, A, 0.016);
    expect(Math.abs(s.pos.l - before.l)).toBeLessThan(25);
    expect(Math.abs(s.pos.r - before.r)).toBeLessThan(25);
    for (let i = 0; i < 120; i++) stepLiquid(s, A, 0.016);
    expect(s.pos).toEqual(A);
  });

  it("works vertically for the rail knob", () => {
    const top: Box = { l: 0, r: 40, t: 0, b: 40 };
    const down: Box = { l: 0, r: 40, t: 200, b: 240 };
    const { frames } = run(down, top);
    const early = frames[6];
    expect(early.w).toBeLessThan(40);
  });
});
