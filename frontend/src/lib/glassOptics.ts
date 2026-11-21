/**
 * Optical Snell refraction and Fresnel specular map generator for SVG
 * `backdrop-filter: url(#fb-glass-*)` surfaces.
 *
 * All displacement is strictly confined to the rounded bezel (`bezelWidth`);
 * the flat interior emits neutral `(128, 128)` vectors so UI typography stays
 * completely crisp.
 */

export type GlassFilterKind = "pill" | "rail" | "card" | "modal" | "orb";

export interface GlassSurfaceSpec {
  id: GlassFilterKind;
  width: number;
  height: number;
  radius: number;
  bezelWidth: number;
  ior?: number;
}

export interface GlassMapUrls {
  displacement: string;
  specular: string;
}

export const GLASS_SURFACE_SPECS: Record<GlassFilterKind, GlassSurfaceSpec> = {
  pill: { id: "pill", width: 320, height: 64, radius: 32, bezelWidth: 14, ior: 1.52 },
  rail: { id: "rail", width: 64, height: 320, radius: 32, bezelWidth: 14, ior: 1.52 },
  card: { id: "card", width: 256, height: 256, radius: 34, bezelWidth: 20, ior: 1.5 },
  modal: { id: "modal", width: 256, height: 256, radius: 30, bezelWidth: 22, ior: 1.5 },
  orb: { id: "orb", width: 128, height: 128, radius: 64, bezelWidth: 42, ior: 1.56 },
};

function clampByte(v: number): number {
  if (v <= 0) return 0;
  if (v >= 255) return 255;
  return Math.round(v);
}

/**
 * Exact Euclidean signed distance to an axis-aligned rounded rectangle centered
 * at `(0, 0)`. Negative inside, `0` on the boundary, positive outside.
 */
export function signedDistanceRoundedRect(
  px: number,
  py: number,
  halfW: number,
  halfH: number,
  radius: number
): number {
  const rx = Math.max(0, halfW - radius);
  const ry = Math.max(0, halfH - radius);
  const qx = Math.abs(px) - rx;
  const qy = Math.abs(py) - ry;
  const outside = Math.hypot(Math.max(qx, 0), Math.max(qy, 0));
  const inside = Math.min(Math.max(qx, qy), 0);
  return outside + inside - radius;
}

/**
 * Evaluates normalized Snell bevel displacement and outward surface normal at
 * texture pixel `(px, py)`. Interior pixels beyond `bezelWidth` return zero.
 */
export function bevelRefractionVector(
  px: number,
  py: number,
  spec: GlassSurfaceSpec
): { dx: number; dy: number; nx: number; ny: number; edgeDepth: number } {
  const halfW = spec.width / 2;
  const halfH = spec.height / 2;
  const cx = px - halfW;
  const cy = py - halfH;

  const sdf = signedDistanceRoundedRect(cx, cy, halfW, halfH, spec.radius);
  const distFromEdge = -sdf;
  if (distFromEdge <= 0 || distFromEdge >= spec.bezelWidth) {
    return { dx: 0, dy: 0, nx: 0, ny: 0, edgeDepth: 0 };
  }

  const eps = 0.75;
  const gx =
    signedDistanceRoundedRect(cx + eps, cy, halfW, halfH, spec.radius) -
    signedDistanceRoundedRect(cx - eps, cy, halfW, halfH, spec.radius);
  const gy =
    signedDistanceRoundedRect(cx, cy + eps, halfW, halfH, spec.radius) -
    signedDistanceRoundedRect(cx, cy - eps, halfW, halfH, spec.radius);
  const len = Math.hypot(gx, gy) || 1;
  const nx = gx / len;
  const ny = gy / len;

  const t = distFromEdge / spec.bezelWidth;
  const edgeDepth = 1 - t;
  const slope = edgeDepth / Math.sqrt(Math.max(0.06, 1 - edgeDepth * edgeDepth));
  const sinI = slope / Math.sqrt(1 + slope * slope);
  const ior = spec.ior ?? 1.5;
  const mag = Math.min(1, sinI * (1 - 1 / ior) * 2.4 * Math.pow(edgeDepth, 0.3));

  return {
    // Inward convex lens deflection guarantees every feDisplacementMap sample
    // stays inside the backdrop filter region (zero edge-clamp color fringe).
    dx: -nx * mag,
    dy: -ny * mag,
    nx,
    ny,
    edgeDepth,
  };
}

/**
 * Computes crisp Fresnel studio key + bounce rim specular highlight RGBA for a
 * bevel pixel. Returns fully transparent `[0, 0, 0, 0]` in the interior.
 */
export function specularRimRgba(
  nx: number,
  ny: number,
  edgeDepth: number
): [number, number, number, number] {
  if (edgeDepth <= 0.45) {
    return [0, 0, 0, 0];
  }

  const rim = Math.pow((edgeDepth - 0.45) / 0.55, 1.8);
  const key = Math.pow(Math.max(0, nx * -0.64 + ny * -0.77), 2.2);
  const bounce = Math.pow(Math.max(0, nx * 0.58 + ny * 0.81), 3.0) * 0.48;

  const totalWeight = key + bounce + 0.0001;
  const warmMix = key / totalWeight;
  const coolMix = bounce / totalWeight;

  const r = clampByte(255 * warmMix + 236 * coolMix + 248 * Math.max(0, 1 - warmMix - coolMix));
  const g = clampByte(251 * warmMix + 246 * coolMix + 250 * Math.max(0, 1 - warmMix - coolMix));
  const b = clampByte(246 * warmMix + 255 * coolMix + 253 * Math.max(0, 1 - warmMix - coolMix));
  const a = Math.min(185, Math.round(rim * (0.22 + key * 0.56 + bounce * 0.34) * 255));

  return [r, g, b, a];
}

/** Builds raw RGBA pixel buffers for displacement and specular PNG generation. */
export function buildGlassMapBuffers(spec: GlassSurfaceSpec): {
  displacement: Uint8ClampedArray;
  specular: Uint8ClampedArray;
} {
  const totalPixels = spec.width * spec.height;
  const displacement = new Uint8ClampedArray(totalPixels * 4);
  const specular = new Uint8ClampedArray(totalPixels * 4);

  for (let y = 0; y < spec.height; y++) {
    for (let x = 0; x < spec.width; x++) {
      const idx = (y * spec.width + x) * 4;
      const vec = bevelRefractionVector(x + 0.5, y + 0.5, spec);

      displacement[idx] = clampByte(128 + vec.dx * 127);
      displacement[idx + 1] = clampByte(128 + vec.dy * 127);
      displacement[idx + 2] = 128;
      displacement[idx + 3] = 255;

      const [sr, sg, sb, sa] = specularRimRgba(vec.nx, vec.ny, vec.edgeDepth);
      specular[idx] = sr;
      specular[idx + 1] = sg;
      specular[idx + 2] = sb;
      specular[idx + 3] = sa;
    }
  }

  return { displacement, specular };
}

let cachedMaps: Record<GlassFilterKind, GlassMapUrls> | null = null;
let cachedFailed = false;

function encodeBufferToDataUrl(
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  bytes: Uint8ClampedArray
): string {
  canvas.width = width;
  canvas.height = height;
  const imageData = ctx.createImageData(width, height);
  imageData.data.set(bytes);
  ctx.putImageData(imageData, 0, 0);
  return canvas.toDataURL("image/png");
}

/**
 * Generates and caches PNG data URLs for all five optical glass surfaces.
 * Returns `null` cleanly under SSR or environments without 2D canvas support.
 */
export function generateAllGlassMaps(): Record<GlassFilterKind, GlassMapUrls> | null {
  if (cachedMaps) return cachedMaps;
  if (cachedFailed) return null;
  if (typeof document === "undefined") return null;

  try {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      cachedFailed = true;
      return null;
    }

    const result = {} as Record<GlassFilterKind, GlassMapUrls>;
    for (const kind of Object.keys(GLASS_SURFACE_SPECS) as GlassFilterKind[]) {
      const spec = GLASS_SURFACE_SPECS[kind];
      const { displacement, specular } = buildGlassMapBuffers(spec);
      result[kind] = {
        displacement: encodeBufferToDataUrl(canvas, ctx, spec.width, spec.height, displacement),
        specular: encodeBufferToDataUrl(canvas, ctx, spec.width, spec.height, specular),
      };
    }

    cachedMaps = result;
    return cachedMaps;
  } catch {
    cachedFailed = true;
    return null;
  }
}

/**
 * Checks whether the current browser reliably composites SVG `backdrop-filter:
 * url(#...)` without Firefox/Safari partial-support tearing or reduced-motion/
 * reduced-transparency accessibility overrides.
 */
export function supportsOpticalBackdropFilter(): boolean {
  if (typeof window === "undefined" || typeof document === "undefined") return false;
  if (typeof CSS === "undefined" || typeof CSS.supports !== "function") return false;

  if (typeof window.matchMedia === "function") {
    if (window.matchMedia("(prefers-reduced-transparency: reduce)").matches) return false;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
  }

  const ua = typeof navigator !== "undefined" ? navigator.userAgent : "";
  const isChromium = (/Chrome\/|Edg\/|Chromium\//i.test(ua)) && !/Firefox/i.test(ua);
  if (!isChromium) return false;

  return CSS.supports("backdrop-filter", "url(#fb-glass-pill)");
}
