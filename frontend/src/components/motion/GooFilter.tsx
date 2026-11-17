/**
 * SVG "liquid glass" filter used by `.fb-goo` (Issues #271, #273).
 *
 * 1. Metaball: blur the shapes' alpha and apply a steep alpha curve, so the
 *    pill and nearby drops melt together with smooth necks and drops that move
 *    apart become round beads.
 * 2. Glass: the liquid body is mostly transparent (the dark capsule shows
 *    through), lit by a distant light on a blurred height map so every edge
 *    bulges with a specular highlight, plus a thin bright rim and an inner
 *    shade on the far side — it reads as a raised drop of water.
 * 3. A soft drop shadow taken from the final liquid shape.
 * Colours come from light only (white highlights over whatever is below), so
 * the palette is untouched. Not display:none — filters inside hidden SVGs do
 * not apply in every browser.
 */
export default function GooFilter() {
  return (
    <svg aria-hidden="true" focusable="false" width="0" height="0" style={{ position: "absolute", width: 0, height: 0, overflow: "hidden" }}>
      <defs>
        <filter id="fb-goo" x="-5%" y="-60%" width="110%" height="220%" colorInterpolationFilters="sRGB">
          {/* 1. metaball mask (white, thresholded alpha) */}
          <feGaussianBlur in="SourceAlpha" stdDeviation="5" result="blur" />
          <feColorMatrix in="blur" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 22 -9" result="goo" />

          {/* 2a. height map -> convex specular highlights along every edge */}
          <feGaussianBlur in="goo" stdDeviation="3" result="height" />
          <feSpecularLighting in="height" surfaceScale="7" specularConstant="1.25" specularExponent="22" lightingColor="#ffffff" result="spec">
            <feDistantLight azimuth="235" elevation="40" />
          </feSpecularLighting>
          <feComposite in="spec" in2="goo" operator="in" result="gloss" />

          {/* 2b. inner shade on the side away from the light (depth) */}
          <feOffset in="height" dx="-2" dy="-2.5" result="shifted" />
          <feComposite in="goo" in2="shifted" operator="out" result="shadeEdge" />
          <feColorMatrix in="shadeEdge" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.32 0" result="shade" />

          {/* 2c. thin bright glass rim */}
          <feMorphology in="goo" operator="erode" radius="1.4" result="inner" />
          <feComposite in="goo" in2="inner" operator="out" result="rimEdge" />
          <feColorMatrix in="rimEdge" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.55 0" result="rim" />

          {/* 2d. transparent body: a faint milky tint so the drop is visible but see-through */}
          <feColorMatrix in="goo" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.16 0" result="body" />

          <feMerge result="liquid">
            <feMergeNode in="body" />
            <feMergeNode in="shade" />
            <feMergeNode in="gloss" />
            <feMergeNode in="rim" />
          </feMerge>

          {/* 3. shadow from the liquid shape */}
          <feDropShadow in="liquid" dx="0" dy="4" stdDeviation="4" floodColor="#000000" floodOpacity="0.45" />
        </filter>
      </defs>
    </svg>
  );
}
