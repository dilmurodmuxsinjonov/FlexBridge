/**
 * SVG metaball ("goo") filter used by `.fb-goo`: blur, then a steep alpha curve
 * melts nearby shapes into one liquid with smooth necks, while drops that move
 * apart become round beads. The original pixels are kept on top (atop), and the
 * shadow is drawn from the final liquid shape. Not display:none — filters inside
 * hidden SVGs do not apply in every browser.
 */
export default function GooFilter() {
  return (
    <svg aria-hidden="true" focusable="false" width="0" height="0" style={{ position: "absolute", width: 0, height: 0, overflow: "hidden" }}>
      <defs>
        <filter id="fb-goo" x="-5%" y="-60%" width="110%" height="220%" colorInterpolationFilters="sRGB">
          <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
          <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -9" result="goo" />
          <feComposite in="SourceGraphic" in2="goo" operator="atop" result="liquid" />
          <feDropShadow in="liquid" dx="0" dy="3" stdDeviation="3.5" floodColor="#000000" floodOpacity="0.45" />
        </filter>
      </defs>
    </svg>
  );
}
