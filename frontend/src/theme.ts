// Brand tokens from docs/brand.md. Keep in sync with the @theme block in index.css
// (CSS uses them for Tailwind classes; this file is for code, e.g. ECharts and MapLibre later).
export const theme = {
  colors: {
    teal: "#0F5C6E",   // primary: headers, buttons
    coral: "#E8704A",  // accent, logo flame (not for text: low contrast on cream)
    cream: "#FAF7F2",  // background
    ink: "#1F2A30",    // text
    muted: "#5B6870",  // secondary text
    ok: "#2E7D4F",     // always with text
    warn: "#B7791F",
    danger: "#C0392B",
  },
  fontFamily: '"Atkinson Hyperlegible", Arial, sans-serif',
  baseFontPx: 18,
  simpleModeFontPx: 24,
  radiusPx: 12,
} as const;
