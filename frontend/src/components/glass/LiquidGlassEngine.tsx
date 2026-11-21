"use client";

import { useEffect, useSyncExternalStore } from "react";
import {
  generateAllGlassMaps,
  supportsOpticalBackdropFilter,
  type GlassFilterKind,
  type GlassMapUrls,
} from "@/lib/glassOptics";

interface OpticalFilterSpec {
  kind: GlassFilterKind;
  id: string;
  blur: number;
  scaleR: number;
  scaleG: number;
  scaleB: number;
  saturate: number;
}

const FILTER_SPECS: OpticalFilterSpec[] = [
  { kind: "pill", id: "fb-glass-pill", blur: 0.9, scaleR: 15, scaleG: 12.5, scaleB: 10, saturate: 1.24 },
  { kind: "rail", id: "fb-glass-rail", blur: 0.9, scaleR: 13.5, scaleG: 11.2, scaleB: 9, saturate: 1.24 },
  { kind: "card", id: "fb-glass-card", blur: 2.2, scaleR: 11.5, scaleG: 9.8, scaleB: 8.2, saturate: 1.18 },
  { kind: "modal", id: "fb-glass-modal", blur: 10.5, scaleR: 13.5, scaleG: 11.5, scaleB: 9.5, saturate: 1.16 },
  { kind: "orb", id: "fb-glass-orb", blur: 0.4, scaleR: 20, scaleG: 17, scaleB: 14, saturate: 1.3 },
];

function getServerMapsSnapshot(): Record<GlassFilterKind, GlassMapUrls> | null {
  return null;
}

function getClientMapsSnapshot(): Record<GlassFilterKind, GlassMapUrls> | null {
  return supportsOpticalBackdropFilter() ? generateAllGlassMaps() : null;
}

function subscribeMediaPreferences(onStoreChange: () => void): () => void {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return () => undefined;
  }
  const mReducedTransparency = window.matchMedia("(prefers-reduced-transparency: reduce)");
  const mReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const onChange = () => onStoreChange();

  mReducedTransparency.addEventListener("change", onChange);
  mReducedMotion.addEventListener("change", onChange);
  return () => {
    mReducedTransparency.removeEventListener("change", onChange);
    mReducedMotion.removeEventListener("change", onChange);
  };
}

/**
 * Mounts five optical SVG `<filter>` graphs (`#fb-glass-pill/rail/card/modal/orb`)
 * using Snell bezel refraction + RGB Cauchy chromatic dispersion + crisp Fresnel
 * rim highlights on Chromium, and switches `html[data-liquid-glass]` cleanly.
 */
export default function LiquidGlassEngine() {
  const maps = useSyncExternalStore(
    subscribeMediaPreferences,
    getClientMapsSnapshot,
    getServerMapsSnapshot
  );

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.dataset.liquidGlass = maps ? "optical" : "fresnel";
  }, [maps]);

  return (
    <svg
      aria-hidden="true"
      focusable="false"
      width="0"
      height="0"
      style={{ position: "fixed", width: 0, height: 0, pointerEvents: "none", overflow: "hidden" }}
    >
      <defs>
        {maps
          ? FILTER_SPECS.map((spec) => {
              const pair = maps[spec.kind];
              return (
                <filter
                  key={spec.id}
                  id={spec.id}
                  x="-6%"
                  y="-6%"
                  width="112%"
                  height="112%"
                  colorInterpolationFilters="sRGB"
                >
                  <feGaussianBlur in="SourceGraphic" stdDeviation={spec.blur} result="soft" />
                  <feImage
                    href={pair.displacement}
                    x="0%"
                    y="0%"
                    width="100%"
                    height="100%"
                    preserveAspectRatio="none"
                    result="dispMap"
                  />

                  <feDisplacementMap
                    in="soft"
                    in2="dispMap"
                    xChannelSelector="R"
                    yChannelSelector="G"
                    scale={spec.scaleR}
                    result="dispR"
                  />
                  <feDisplacementMap
                    in="soft"
                    in2="dispMap"
                    xChannelSelector="R"
                    yChannelSelector="G"
                    scale={spec.scaleG}
                    result="dispG"
                  />
                  <feDisplacementMap
                    in="soft"
                    in2="dispMap"
                    xChannelSelector="R"
                    yChannelSelector="G"
                    scale={spec.scaleB}
                    result="dispB"
                  />

                  <feColorMatrix
                    in="dispR"
                    type="matrix"
                    values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"
                    result="rCh"
                  />
                  <feColorMatrix
                    in="dispG"
                    type="matrix"
                    values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0"
                    result="gCh"
                  />
                  <feColorMatrix
                    in="dispB"
                    type="matrix"
                    values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0"
                    result="bCh"
                  />

                  <feComposite in="rCh" in2="gCh" operator="arithmetic" k1="0" k2="1" k3="1" k4="0" result="rg" />
                  <feComposite in="rg" in2="bCh" operator="arithmetic" k1="0" k2="1" k3="1" k4="0" result="rgb" />
                  <feColorMatrix in="rgb" type="saturate" values={String(spec.saturate)} result="refracted" />

                  <feImage
                    href={pair.specular}
                    x="0%"
                    y="0%"
                    width="100%"
                    height="100%"
                    preserveAspectRatio="none"
                    result="specRim"
                  />
                  <feBlend in="specRim" in2="refracted" mode="screen" />
                </filter>
              );
            })
          : null}
      </defs>
    </svg>
  );
}
