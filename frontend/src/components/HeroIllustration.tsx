// Own illustration (no stock photos, no people): a few city blocks, the route from the staff base to three homes,
// and the card of the next visit. Decorative: the page text says everything it shows.
import { theme } from "../theme";
import { es } from "../i18n/es";

const c = theme.colors;

function House({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <circle r="30" fill="#fff" stroke={c.navy} strokeWidth="3" />
      <path d="M-14 2 L0 -12 L14 2 M-10 -1 V13 H10 V-1" fill="none" stroke={c.navy} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
    </g>
  );
}

export function HeroIllustration() {
  const t = es.landing;
  return (
    <svg viewBox="0 0 560 460" role="img" aria-label={t.heroArt} className="h-auto w-full">
      <rect x="0" y="0" width="560" height="460" rx="36" fill={c.sky} />
      {/* city blocks */}
      {[[40, 40, 150, 110], [220, 40, 140, 70], [390, 40, 130, 150], [40, 180, 110, 120], [180, 140, 180, 90],
        [180, 260, 120, 150], [330, 230, 190, 80], [40, 330, 110, 90], [330, 340, 190, 80]].map(([x, y, w, h], i) => (
        <rect key={i} x={x} y={y} width={w} height={h} rx="18" fill="#fff" opacity={0.9} />))}
      {/* route from the base to the homes */}
      <path d="M95 255 C 160 255, 165 120, 270 120 S 430 210, 455 215 M270 120 C 300 200, 250 300, 240 335"
        fill="none" stroke={c.teal} strokeWidth="7" strokeLinecap="round" strokeDasharray="2 16" />
      {/* staff base: the Enlaza symbol colours */}
      <g transform="translate(95 255)">
        <circle r="34" fill={c.navy} />
        <path d="M-12 -2 h24 M0 -14 v24" stroke="#fff" strokeWidth="7" strokeLinecap="round" />
      </g>
      <House x={270} y={120} />
      <House x={455} y={215} />
      <House x={240} y={335} />
      {/* next visit card */}
      <g transform="translate(330 330)">
        <rect width="200" height="98" rx="22" fill="#fff" stroke={c.navy} strokeOpacity="0.15" />
        <circle cx="34" cy="49" r="20" fill={c.teal} opacity="0.25" />
        <path d="M24 49 l7 7 l13 -14" fill="none" stroke={c.tealText} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <text x="66" y="38" fontFamily={theme.displayFamily} fontWeight="700" fontSize="15" fill={c.navy}>{t.artCardTitle}</text>
        <text x="66" y="60" fontFamily={theme.fontFamily} fontSize="14" fill={c.ink}>{t.artCardWhen}</text>
        <text x="66" y="80" fontFamily={theme.fontFamily} fontSize="13" fill={c.muted}>{t.artCardWho}</text>
      </g>
    </svg>
  );
}
