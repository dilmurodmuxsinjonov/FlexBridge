"use client";

import { useEffect, useRef, useState } from "react";

const VERTEX_SHADER = `#version 300 es
layout(location = 0) in vec2 a_pos;
void main() {
  gl_Position = vec4(a_pos, 0.0, 1.0);
}
`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;

uniform vec2 u_resolution;
uniform float u_time;
uniform vec2 u_pointer;
uniform float u_dark;

out vec4 fragColor;

float smin(float a, float b, float k) {
  float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
  return mix(b, a, h) - k * h * (1.0 - h);
}

float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
  vec3 pa = p - a;
  vec3 ba = b - a;
  float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
  return length(pa - ba * h) - r;
}

float mapScene(vec3 p, float t, vec2 ptr) {
  vec3 shifted = p;
  shifted.x -= ptr.x * 0.25;
  shifted.y -= ptr.y * 0.14;

  float cap = sdCapsule(shifted, vec3(-0.72, 0.0, 0.0), vec3(0.62, 0.0, 0.0), 0.34);

  float orbit = t * 0.9;
  vec3 dropPos = vec3(
    0.96 + sin(orbit) * 0.12 + ptr.x * 0.35,
    cos(orbit * 1.15) * 0.09 + ptr.y * 0.22,
    0.05
  );
  float drop = length(p - dropPos) - 0.185;
  return smin(cap, drop, 0.24);
}

vec3 calcNormal(vec3 p, float t, vec2 ptr) {
  const float e = 0.002;
  return normalize(vec3(
    mapScene(p + vec3(e, 0.0, 0.0), t, ptr) - mapScene(p - vec3(e, 0.0, 0.0), t, ptr),
    mapScene(p + vec3(0.0, e, 0.0), t, ptr) - mapScene(p - vec3(0.0, e, 0.0), t, ptr),
    mapScene(p + vec3(0.0, 0.0, e), t, ptr) - mapScene(p - vec3(0.0, 0.0, e), t, ptr)
  ));
}

vec3 sampleBackdrop(vec2 uv, float t, float darkMode) {
  // Architectural coordinate grid + warm terracotta & emerald optical silk ribbon behind the lens
  vec2 gridUv = uv * vec2(10.0, 5.0);
  vec2 grid = abs(fract(gridUv - 0.5) - 0.5) / fwidth(gridUv);
  float line = 1.0 - min(min(grid.x, grid.y), 1.0);

  float wave1 = sin(uv.x * 4.5 + t * 0.7 + cos(uv.y * 3.5)) * 0.5 + 0.5;
  float wave2 = cos(uv.x * 3.2 - uv.y * 4.1 - t * 0.5) * 0.5 + 0.5;

  vec3 darkBg = vec3(0.045, 0.055, 0.075);
  vec3 darkGrid = vec3(0.16, 0.20, 0.26);
  vec3 accentTerracotta = vec3(0.92, 0.42, 0.18);
  vec3 accentEmerald = vec3(0.08, 0.72, 0.51);

  vec3 col = mix(darkBg, darkGrid, line * 0.35);
  col += accentTerracotta * pow(wave1, 2.2) * 0.58;
  col += accentEmerald * pow(wave2, 2.5) * 0.44;

  // Keep slight lift if page is light mode while still reading well inside .fb-ink-card
  return mix(col * 1.12, col, darkMode);
}

void main() {
  vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution) / max(u_resolution.y, 1.0);
  vec3 ro = vec3(0.0, 0.0, 2.25);
  vec3 rd = normalize(vec3(uv, -1.65));

  vec3 bg = sampleBackdrop(uv, u_time, u_dark);

  float dist = 0.0;
  bool hit = false;
  for (int i = 0; i < 48; i++) {
    float d = mapScene(ro + rd * dist, u_time, u_pointer);
    if (d < 0.002) {
      hit = true;
      break;
    }
    if (dist > 5.0) break;
    dist += d;
  }

  if (!hit) {
    fragColor = vec4(bg, 1.0);
    return;
  }

  vec3 pos = ro + rd * dist;
  vec3 normal = calcNormal(pos, u_time, u_pointer);
  float ndotv = max(dot(normal, -rd), 0.0);
  float fresnel = 0.04 + 0.96 * pow(1.0 - ndotv, 4.0);

  // Snell's law RGB spectral refraction
  vec3 refrR = refract(rd, normal, 1.0 / 1.45);
  vec3 refrG = refract(rd, normal, 1.0 / 1.50);
  vec3 refrB = refract(rd, normal, 1.0 / 1.56);

  float r = sampleBackdrop(uv + refrR.xy * 0.42, u_time, u_dark).r;
  float g = sampleBackdrop(uv + refrG.xy * 0.42, u_time, u_dark).g;
  float b = sampleBackdrop(uv + refrB.xy * 0.42, u_time, u_dark).b;
  vec3 refracted = vec3(r, g, b);

  // Caustic terracotta & crystal teal inner refraction glow
  vec3 caustic = vec3(0.95, 0.46, 0.22) * pow(max(0.0, -normal.x * 0.6 + normal.y * 0.7), 2.5) * 0.34;
  vec3 rimBounce = vec3(0.45, 0.92, 0.85) * pow(max(0.0, normal.x * 0.6 - normal.y * 0.7), 2.8) * 0.26;

  // Dual studio specular highlights
  vec3 lightDir1 = normalize(vec3(-0.65, 0.78, 0.65));
  vec3 lightDir2 = normalize(vec3(0.60, -0.75, 0.55));
  vec3 half1 = normalize(lightDir1 - rd);
  vec3 half2 = normalize(lightDir2 - rd);
  float spec1 = pow(max(dot(normal, half1), 0.0), 72.0);
  float spec2 = pow(max(dot(normal, half2), 0.0), 36.0) * 0.42;

  vec3 color = mix(refracted * 1.15 + caustic + rimBounce, vec3(0.92, 0.97, 1.0), fresnel * 0.52);
  color += vec3(1.0, 0.98, 0.95) * spec1 + vec3(0.68, 0.93, 1.0) * spec2;

  fragColor = vec4(color, 1.0);
}
`;

function compileShader(gl: WebGL2RenderingContext, type: number, source: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

/**
 * Compact WebGL2 ray-traced 3D liquid glass showcase component with RGB
 * chromatic Snell refraction, Schlick Fresnel rims, and pointer parallax.
 */
export default function LiquidGlass3D({
  className = "",
  label = "3D optik shisha",
}: {
  className?: string;
  label?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [webglReady, setWebglReady] = useState(true);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    let gl: WebGL2RenderingContext | null = null;
    try {
      gl = canvas.getContext("webgl2", {
        alpha: false,
        antialias: true,
        depth: false,
        stencil: false,
        powerPreference: "low-power",
      });
    } catch {
      gl = null;
    }

    if (!gl) {
      const frame = window.requestAnimationFrame(() => setWebglReady(false));
      return () => window.cancelAnimationFrame(frame);
    }

    const vert = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
    const frag = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
    if (!vert || !frag) {
      if (vert) gl.deleteShader(vert);
      if (frag) gl.deleteShader(frag);
      const frame = window.requestAnimationFrame(() => setWebglReady(false));
      return () => window.cancelAnimationFrame(frame);
    }

    const program = gl.createProgram();
    if (!program) {
      gl.deleteShader(vert);
      gl.deleteShader(frag);
      const frame = window.requestAnimationFrame(() => setWebglReady(false));
      return () => window.cancelAnimationFrame(frame);
    }
    gl.attachShader(program, vert);
    gl.attachShader(program, frag);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      gl.deleteProgram(program);
      gl.deleteShader(vert);
      gl.deleteShader(frag);
      const frame = window.requestAnimationFrame(() => setWebglReady(false));
      return () => window.cancelAnimationFrame(frame);
    }

    const vao = gl.createVertexArray();
    const vbo = gl.createBuffer();
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    const uRes = gl.getUniformLocation(program, "u_resolution");
    const uTime = gl.getUniformLocation(program, "u_time");
    const uPointer = gl.getUniformLocation(program, "u_pointer");
    const uDark = gl.getUniformLocation(program, "u_dark");

    let targetDark = document.documentElement.classList.contains("dark") ? 1 : 0;
    let px = 0;
    let py = 0;
    let targetPx = 0;
    let targetPy = 0;
    let visible = true;
    let rafId = 0;
    let elapsed = 0;
    let lastTs = 0;
    let disposed = false;

    const hasMatchMedia = typeof window.matchMedia === "function";
    const reducedQuery = hasMatchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
    const isReduced = () => Boolean(reducedQuery?.matches);

    const resize = () => {
      const box = container.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 1.75);
      const w = Math.max(1, Math.round((box.width || 240) * dpr));
      const h = Math.max(1, Math.round((box.height || 88) * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
    };

    const drawFrame = (dt: number) => {
      if (disposed) return;
      if (!isReduced()) elapsed += dt;
      px += (targetPx - px) * 0.1;
      py += (targetPy - py) * 0.1;

      gl.useProgram(program);
      gl.bindVertexArray(vao);
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uTime, elapsed);
      gl.uniform2f(uPointer, px, py);
      gl.uniform1f(uDark, targetDark);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };

    const tick = (ts: number) => {
      if (disposed || !visible || document.hidden || isReduced()) {
        rafId = 0;
        return;
      }
      const dt = Math.min(0.05, lastTs ? (ts - lastTs) / 1000 : 0.016);
      lastTs = ts;
      drawFrame(dt);
      rafId = window.requestAnimationFrame(tick);
    };

    const ensureLoop = () => {
      if (disposed) return;
      if (isReduced()) {
        if (rafId) {
          window.cancelAnimationFrame(rafId);
          rafId = 0;
        }
        drawFrame(0);
        return;
      }
      if (visible && !document.hidden && !rafId) {
        lastTs = 0;
        rafId = window.requestAnimationFrame(tick);
      }
    };

    const onPointerMove = (ev: PointerEvent) => {
      if (isReduced()) return;
      const box = container.getBoundingClientRect();
      if (!box.width || !box.height) return;
      targetPx = Math.max(-1, Math.min(1, ((ev.clientX - box.left) / box.width - 0.5) * 2));
      targetPy = Math.max(-1, Math.min(1, -((ev.clientY - box.top) / box.height - 0.5) * 2));
    };

    const onPointerLeave = () => {
      targetPx = 0;
      targetPy = 0;
    };

    const onThemeSync = () => {
      targetDark = document.documentElement.classList.contains("dark") ? 1 : 0;
      if (isReduced()) drawFrame(0);
    };

    const io =
      typeof IntersectionObserver !== "undefined"
        ? new IntersectionObserver((entries) => {
            visible = Boolean(entries[0]?.isIntersecting);
            if (!visible && rafId) {
              window.cancelAnimationFrame(rafId);
              rafId = 0;
            } else {
              ensureLoop();
            }
          })
        : null;
    io?.observe(container);

    resize();
    drawFrame(0);
    ensureLoop();

    const mutObserver = new MutationObserver(onThemeSync);
    mutObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    container.addEventListener("pointermove", onPointerMove, { passive: true });
    container.addEventListener("pointerleave", onPointerLeave, { passive: true });
    window.addEventListener("flexbridge:theme-change", onThemeSync);
    window.addEventListener("resize", resize, { passive: true });
    document.addEventListener("visibilitychange", ensureLoop);
    reducedQuery?.addEventListener("change", ensureLoop);

    return () => {
      disposed = true;
      if (rafId) window.cancelAnimationFrame(rafId);
      io?.disconnect();
      mutObserver.disconnect();
      container.removeEventListener("pointermove", onPointerMove);
      container.removeEventListener("pointerleave", onPointerLeave);
      window.removeEventListener("flexbridge:theme-change", onThemeSync);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", ensureLoop);
      reducedQuery?.removeEventListener("change", ensureLoop);
      gl.deleteBuffer(vbo);
      gl.deleteVertexArray(vao);
      gl.deleteProgram(program);
      gl.deleteShader(vert);
      gl.deleteShader(frag);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden rounded-2xl border border-white/15 bg-black/30 ${className}`}
    >
      {webglReady ? (
        <canvas
          ref={canvasRef}
          data-testid="liquid-glass-3d"
          aria-hidden="true"
          className="block h-full w-full"
        />
      ) : (
        <div
          aria-hidden="true"
          className="flex h-full w-full items-center justify-center bg-[radial-gradient(circle_at_30%_30%,rgba(224,98,45,0.28),transparent_60%),radial-gradient(circle_at_75%_65%,rgba(16,185,129,0.24),transparent_60%)]"
        >
          <div className="h-9 w-36 rounded-full border border-white/35 bg-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.6),inset_0_-1px_1px_rgba(120,225,255,0.25),0_8px_20px_rgba(0,0,0,0.4)]" />
        </div>
      )}
      <span className="pointer-events-none absolute bottom-1.5 right-2.5 rounded-full border border-white/15 bg-black/45 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-white/80">
        {label}
      </span>
    </div>
  );
}
