import { describe, expect, it } from "vitest";
import {
  GLASS_SURFACE_SPECS,
  bevelRefractionVector,
  buildGlassMapBuffers,
  signedDistanceRoundedRect,
  specularRimRgba,
} from "./glassOptics";

describe("glassOptics", () => {
  it("computes accurate signed distance for rounded rectangles", () => {
    expect(signedDistanceRoundedRect(0, 0, 100, 50, 20)).toBe(-50);
    expect(signedDistanceRoundedRect(100, 0, 100, 50, 20)).toBe(0);
    expect(signedDistanceRoundedRect(0, -50, 100, 50, 20)).toBe(0);
    expect(signedDistanceRoundedRect(108, 0, 100, 50, 20)).toBe(8);
  });

  it("keeps the flat interior distortion strictly zero so text stays razor sharp", () => {
    for (const kind of ["pill", "rail", "card", "modal"] as const) {
      const spec = GLASS_SURFACE_SPECS[kind];
      const cx = spec.width / 2;
      const cy = spec.height / 2;
      for (const [px, py] of [
        [cx, cy],
        [cx - 8, cy],
        [cx + 8, cy - 6],
      ]) {
        const vec = bevelRefractionVector(px, py, spec);
        expect(vec.dx).toBe(0);
        expect(vec.dy).toBe(0);
        expect(vec.edgeDepth).toBe(0);
      }
    }
  });

  it("produces inward symmetric Snell refraction vectors on opposite bevel edges", () => {
    const spec = GLASS_SURFACE_SPECS.card;
    const midY = spec.height / 2;
    const left = bevelRefractionVector(4, midY, spec);
    const right = bevelRefractionVector(spec.width - 4, midY, spec);
    expect(left.dx).toBeGreaterThan(0);
    expect(right.dx).toBeLessThan(0);
    expect(left.dx).toBeCloseTo(-right.dx, 5);
    expect(left.dy).toBeCloseTo(0, 5);
    expect(right.dy).toBeCloseTo(0, 5);

    const midX = spec.width / 2;
    const top = bevelRefractionVector(midX, 4, spec);
    const bottom = bevelRefractionVector(midX, spec.height - 4, spec);
    expect(top.dy).toBeGreaterThan(0);
    expect(bottom.dy).toBeLessThan(0);
    expect(top.dy).toBeCloseTo(-bottom.dy, 5);
  });

  it("keeps specular rim alpha zero in interior and non-zero at grazing bevel rim", () => {
    expect(specularRimRgba(0, 0, 0)).toEqual([0, 0, 0, 0]);
    expect(specularRimRgba(-1, 0, 0.45)).toEqual([0, 0, 0, 0]);

    const topLeftRim = specularRimRgba(-0.707, -0.707, 0.92);
    expect(topLeftRim[3]).toBeGreaterThan(100);
    expect(topLeftRim[0]).toBeGreaterThanOrEqual(topLeftRim[2]);

    const bottomRightRim = specularRimRgba(0.707, 0.707, 0.92);
    expect(bottomRightRim[3]).toBeGreaterThan(40);
    expect(bottomRightRim[2]).toBeGreaterThanOrEqual(bottomRightRim[0]);
  });

  it("encodes neutral 128 displacement in center pixels and real offsets at the rim", () => {
    const spec = { id: "card" as const, width: 64, height: 64, radius: 14, bezelWidth: 10, ior: 1.5 };
    const { displacement, specular } = buildGlassMapBuffers(spec);

    const centerIdx = (32 * spec.width + 32) * 4;
    expect(displacement[centerIdx]).toBe(128);
    expect(displacement[centerIdx + 1]).toBe(128);
    expect(displacement[centerIdx + 2]).toBe(128);
    expect(displacement[centerIdx + 3]).toBe(255);
    expect(specular[centerIdx + 3]).toBe(0);

    const leftRimIdx = (32 * spec.width + 2) * 4;
    expect(displacement[leftRimIdx]).toBeGreaterThan(128);
    expect(displacement[leftRimIdx + 3]).toBe(255);
  });
});
