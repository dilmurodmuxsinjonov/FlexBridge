"use client";

import { useEffect, useRef } from "react";

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
uniform float u_dark;
uniform vec2 u_pointer;

out vec4 fragColor;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
    mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
    u.y
  );
}

float fbm(vec2 p) {
  float value = 0.0;
  float amp = 0.5;
  mat2 rot = mat2(0.80, -0.60, 0.60, 0.80);
  for (int i = 0; i < 4; i++) {
    value += amp * noise(p);
    p = rot * p * 1.95;
    amp *= 0.5;
  }
  return value;
}

vec3 computeSilk(vec2 uv, float t, float darkMode) {
  vec2 p = uv * 2.1 + u_pointer * 0.14;

  float qx = fbm(p + vec2(0.0, 0.0) + 0.12 * t);
  float qy = fbm(p + vec2(5.2, 1.3) - 0.10 * t);
  vec2 q = vec2(qx, qy);

  float rx = fbm(p + 2.4 * q + vec2(1.7, 9.2) + 0.09 * t);
  float ry = fbm(p + 2.4 * q + vec2(8.3, 2.8) - 0.08 * t);
  float fold = clamp(fbm(p + 2.0 * vec2(rx, ry)), 0.0, 1.0);

  float ribbon = pow(smoothstep(0.18, 0.92, fold), 1.45);
  float ridge = smoothstep(0.46, 0.86, sin((uv.x * 2.4 - uv.y * 1.7 + fold * 2.8) * 2.2) * 0.5 + 0.5);

  // Dark palette: deep obsidian + luminous emerald silk + molten terracotta caustic + ocean teal
  vec3 darkBase = vec3(0.024, 0.035, 0.047);
  vec3 darkTeal = vec3(0.059, 0.263, 0.353);
  vec3 darkEmerald = vec3(0.043, 0.478, 0.333);
  vec3 darkTerracotta = vec3(0.851, 0.361, 0.149);

  vec3 darkCol = mix(darkBase, darkTeal, smoothstep(0.12, 0.68, fold));
  darkCol = mix(darkCol, darkEmerald, ribbon * 0.82);
  darkCol += darkTerracotta * pow(ridge * q.x, 1.6) * 0.52;

  // Light palette: pearl alabaster + champagne terracotta + fresh jade + glacier sky
  vec3 lightBase = vec3(0.925, 0.941, 0.965);
  vec3 lightGlacier = vec3(0.573, 0.784, 0.973);
  vec3 lightJade = vec3(0.525, 0.878, 0.761);
  vec3 lightChampagne = vec3(0.953, 0.663, 0.494);

  vec3 lightCol = mix(lightBase, lightGlacier, smoothstep(0.22, 0.85, fold) * 0.55);
  lightCol = mix(lightCol, lightJade, ribbon * 0.42);
  lightCol = mix(lightCol, lightChampagne, pow(ridge * q.y, 1.5) * 0.48);

  return mix(lightCol, darkCol, darkMode);
}

void main() {
  vec2 uv = gl_FragCoord.xy / max(u_resolution, vec2(1.0));
  vec2 centered = (gl_FragCoord.xy - 0.5 * u_resolution) / max(u_resolution.y, 1.0);
  vec3 color = computeSilk(centered + vec2(0.5), u_time, u_dark);

  // Subtle depth vignette so outer chrome floats naturally
  float vignette = 1.0 - smoothstep(0.45, 1.25, length(uv - 0.5));
  color *= mix(0.94, 1.02, vignette);

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
 * Full-viewport fixed WebGL2 backdrop rendering smooth optical silk waves
 * that physically refract inside Chromium `backdrop-filter: url(#fb-glass-*)`
 * surfaces, with static single-frame fallback under reduced motion.
 */
export default function LiquidBackdropCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let gl: WebGL2RenderingContext | null = null;
    try {
      gl = canvas.getContext("webgl2", {
        alpha: false,
        antialias: false,
        depth: false,
        stencil: false,
        powerPreference: "low-power",
      });
    } catch {
      gl = null;
    }

    if (!gl) {
      canvas.style.display = "none";
      return;
    }

    const vert = compileShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
    const frag = compileShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
    if (!vert || !frag) {
      if (vert) gl.deleteShader(vert);
      if (frag) gl.deleteShader(frag);
      canvas.style.display = "none";
      return;
    }

    const program = gl.createProgram();
    if (!program) {
      gl.deleteShader(vert);
      gl.deleteShader(frag);
      canvas.style.display = "none";
      return;
    }
    gl.attachShader(program, vert);
    gl.attachShader(program, frag);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      gl.deleteProgram(program);
      gl.deleteShader(vert);
      gl.deleteShader(frag);
      canvas.style.display = "none";
      return;
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
    const uDark = gl.getUniformLocation(program, "u_dark");
    const uPointer = gl.getUniformLocation(program, "u_pointer");

    let targetDark = document.documentElement.classList.contains("dark") ? 1 : 0;
    let currentDark = targetDark;
    let px = 0;
    let py = 0;
    let targetPx = 0;
    let targetPy = 0;
    let rafId = 0;
    let lastTs = 0;
    let elapsed = 0;
    let disposed = false;

    const hasMatchMedia = typeof window.matchMedia === "function";
    const reducedMotionQuery = hasMatchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
    const reducedTransQuery = hasMatchMedia ? window.matchMedia("(prefers-reduced-transparency: reduce)") : null;

    const isStaticMode = () =>
      Boolean(reducedMotionQuery?.matches || reducedTransQuery?.matches);

    const resize = () => {
      const scale = Math.min(window.devicePixelRatio || 1, 1.25) * 0.65;
      const w = Math.max(1, Math.round(window.innerWidth * scale));
      const h = Math.max(1, Math.round(window.innerHeight * scale));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
    };

    const drawFrame = (dt: number) => {
      if (disposed) return;
      if (!isStaticMode()) {
        elapsed += dt;
      }
      const themeAlpha = Math.min(1, dt / 0.35);
      currentDark += (targetDark - currentDark) * (dt > 0 ? themeAlpha : 1);
      px += (targetPx - px) * 0.08;
      py += (targetPy - py) * 0.08;

      gl.useProgram(program);
      gl.bindVertexArray(vao);
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uTime, elapsed);
      gl.uniform1f(uDark, currentDark);
      gl.uniform2f(uPointer, px, py);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };

    const tick = (ts: number) => {
      if (disposed || document.hidden || isStaticMode()) {
        rafId = 0;
        return;
      }
      const dt = Math.min(0.05, lastTs ? (ts - lastTs) / 1000 : 0.016);
      lastTs = ts;
      drawFrame(dt);
      rafId = window.requestAnimationFrame(tick);
    };

    const startOrDraw = () => {
      if (disposed) return;
      if (isStaticMode()) {
        if (rafId) {
          window.cancelAnimationFrame(rafId);
          rafId = 0;
        }
        drawFrame(0);
        return;
      }
      if (!document.hidden && !rafId) {
        lastTs = 0;
        rafId = window.requestAnimationFrame(tick);
      }
    };

    const onThemeSync = () => {
      targetDark = document.documentElement.classList.contains("dark") ? 1 : 0;
      if (isStaticMode()) drawFrame(0);
    };

    const onPointerMove = (ev: PointerEvent) => {
      if (isStaticMode()) return;
      targetPx = (ev.clientX / Math.max(1, window.innerWidth) - 0.5) * 0.6;
      targetPy = -(ev.clientY / Math.max(1, window.innerHeight) - 0.5) * 0.6;
    };

    const onVisibility = () => {
      if (document.hidden && rafId) {
        window.cancelAnimationFrame(rafId);
        rafId = 0;
      } else {
        startOrDraw();
      }
    };

    const onResize = () => {
      resize();
      if (isStaticMode()) drawFrame(0);
    };

    resize();
    drawFrame(0);
    startOrDraw();

    const observer = new MutationObserver(onThemeSync);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    window.addEventListener("flexbridge:theme-change", onThemeSync);
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("resize", onResize, { passive: true });
    document.addEventListener("visibilitychange", onVisibility);
    reducedMotionQuery?.addEventListener("change", startOrDraw);
    reducedTransQuery?.addEventListener("change", startOrDraw);

    return () => {
      disposed = true;
      if (rafId) window.cancelAnimationFrame(rafId);
      observer.disconnect();
      window.removeEventListener("flexbridge:theme-change", onThemeSync);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
      reducedMotionQuery?.removeEventListener("change", startOrDraw);
      reducedTransQuery?.removeEventListener("change", startOrDraw);
      gl.deleteBuffer(vbo);
      gl.deleteVertexArray(vao);
      gl.deleteProgram(program);
      gl.deleteShader(vert);
      gl.deleteShader(frag);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      data-testid="liquid-backdrop"
      aria-hidden="true"
      className="fb-liquid-backdrop"
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
        zIndex: -1,
        pointerEvents: "none",
      }}
    />
  );
}
