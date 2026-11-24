// Enlaza brand tokens from docs/brand.md. Keep in sync with the @theme block in index.css
// (CSS uses them for Tailwind classes; this file is for code: ECharts, MapLibre, inline SVG illustrations).
export const theme = {
  colors: {
    navy: "#3A5B76",      // logo navy: titles, primary buttons
    teal: "#2AAEAE",      // logo teal: decoration only (2.7:1 on white, never text)
    tealText: "#137273",  // teal for text and meaningful icons
    deep: "#1B3349",      // deep blue sections
    sky: "#EAF4F8",       // light blue gradients
    ink: "#1B2B38",       // text
    muted: "#4F5F6B",     // secondary text
    ok: "#1D7447",        // always with text and icon
    warn: "#8A5A00",
    danger: "#B42318",
  },
  fontFamily: '"Enlaza Digits", "Atkinson Hyperlegible", Arial, sans-serif',
  displayFamily: '"Plus Jakarta Sans", "Atkinson Hyperlegible", Arial, sans-serif',
  baseFontPx: 18,
  simpleModeFontPx: 24,
  radiusPx: 22,
} as const;
