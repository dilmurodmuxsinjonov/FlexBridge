/**
 * SVG "liquid glass" filter used by `.fb-goo` (Issues #271, #273, upgraded in LOG-210).
 *
 * 1. Metaball: blur the shapes' alpha and apply a steep alpha curve, so the
 *    pill and nearby drops melt together with smooth necks and drops that move
 *    apart become round beads.
 * 2. Optical Glass + Chromatic Rim: clearer body (18%), sharper convex specular
 *    highlights on the height map, inner depth shade, plus subtle warm-amber &
 *    cool-cyan prismatic edge dispersion masked inside the liquid silhouette.
 * 3. A soft drop shadow taken from the final liquid shape.
 * Colours stay natural over both themes; SVG is mounted with zero box instead of
 * `display: none` so every Chromium renderer applies it cleanly.
 */
export default function GooFilter() {
  return (
    <svg aria-hidden="true" focusable="false" width="0" height="0" style={{ position: "absolute", width: 0, height: 0, overflow: "hidden" }}>
      <defs>
        <filter id="fb-goo" x="-5%" y="-60%" width="110%" height="220%" colorInterpolationFilters="sRGB">
          {/* 1. metaball mask (white, thresholded alpha) */}
          <feGaussianBlur in="SourceAlpha" stdDeviation="5" result="blur" />
          <feColorMatrix in="blur" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 22 -9" result="goo" />

          {/* 2a. height map -> sharp convex specular highlights along every edge */}
          <feGaussianBlur in="goo" stdDeviation="3" result="height" />
          <feSpecularLighting in="height" surfaceScale="5.2" specularConstant="1.05" specularExponent="42" lightingColor="#ffffff" result="spec">
            <feDistantLight azimuth="225" elevation="44" />
          </feSpecularLighting>
          <feComposite in="spec" in2="goo" operator="in" result="gloss" />

          {/* 2b. inner shade on the side away from the light (optical depth) */}
          <feOffset in="height" dx="-2" dy="-2.5" result="shifted" />
          <feComposite in="goo" in2="shifted" operator="out" result="shadeEdge" />
          <feColorMatrix in="shadeEdge" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.22 0" result="shade" />

          {/* 2c. thin bright Fresnel glass rim + prismatic warm/cool edge split */}
          <feMorphology in="goo" operator="erode" radius="1.4" result="inner" />
          <feComposite in="goo" in2="inner" operator="out" result="rimEdge" />
          <feColorMatrix in="rimEdge" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.42 0" result="rim" />

          <feOffset in="rimEdge" dx="1.1" dy="0.8" result="warmShift" />
          <feComposite in="warmShift" in2="goo" operator="in" result="warmClip" />
          <feColorMatrix in="warmClip" type="matrix" values="0 0 0 0 1  0 0 0 0 0.65  0 0 0 0 0.43  0 0 0 0.34 0" result="rimWarm" />

          <feOffset in="rimEdge" dx="-1.1" dy="-0.8" result="coolShift" />
          <feComposite in="coolShift" in2="goo" operator="in" result="coolClip" />
          <feColorMatrix in="coolClip" type="matrix" values="0 0 0 0 0.47  0 0 0 0 0.88  0 0 0 0 1  0 0 0 0.3 0" result="rimCool" />

          {/* 2d. clearer optical glass body */}
          <feColorMatrix in="goo" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.18 0" result="body" />

          <feMerge result="liquid">
            <feMergeNode in="body" />
            <feMergeNode in="shade" />
            <feMergeNode in="rimWarm" />
            <feMergeNode in="rimCool" />
            <feMergeNode in="gloss" />
            <feMergeNode in="rim" />
          </feMerge>

          {/* 3. shadow from the liquid shape */}
          <feDropShadow in="liquid" dx="0" dy="3" stdDeviation="3" floodColor="#000000" floodOpacity="0.38" />
        </filter>
      </defs>
    </svg>
  );
}
