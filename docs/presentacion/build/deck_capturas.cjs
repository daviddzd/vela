// Colloquium deck WITHOUT live demo -> docs/presentacion/enlaza_coloquio_capturas.pptx (editable text, speaker notes).
// Screenshots of the real app replace the demo: each one cropped to the important zone (recortes.py) with 2 to 4
// numbered callouts (a numbered circle on the image + the same number with a short text beside it).
//
//   node docs/presentacion/build/deck_capturas.cjs   (inside the vela-presentacion image; see scripts/build_presentacion_capturas.sh)
//
// Same brand, fonts, masters and rules as deck.cjs (the version with live demo, which this file does not touch):
// no number is typed here, T("key") takes it from docs/biblia/out/numeros.json and records it in
// out_capturas/numeros_usados.csv; speaker notes come from guion_capturas_fuente.md (out_capturas/notas.json).
// Every text is 24 pt or more, except the source lines and the slide number (14 pt).
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PRES = path.join(ROOT, "docs", "presentacion");
const OUT = path.join(PRES, "out_capturas");
const ASSETS = path.join(OUT, "assets");
const CROPS = path.join(OUT, "recortes");
fs.mkdirSync(ASSETS, { recursive: true });
const N = JSON.parse(fs.readFileSync(path.join(ROOT, "docs/biblia/out/numeros.json"), "utf8"));
const NOTES = JSON.parse(fs.readFileSync(path.join(OUT, "notas.json"), "utf8"));
const QR = path.join(ROOT, "docs", "privado", "qr_enlaza.png");
// Team names: only in the private version (NOMBRES="A|B|C|D"); the version in Git says "Persona 1–4".
const NAMES = (process.env.NOMBRES || "").split("|").map((n) => n.trim()).filter(Boolean);
const TEAM = NAMES.length ? NAMES : ["Persona 1", "Persona 2", "Persona 3", "Persona 4"];
const OUTFILE = process.env.OUTFILE ? path.resolve(ROOT, process.env.OUTFILE) : path.join(PRES, "enlaza_coloquio_capturas.pptx");
if (!fs.existsSync(QR)) throw new Error("Falta docs/privado/qr_enlaza.png: correr `uv run scripts/make_qr.py`");

const USED = new Map();
const T = (key) => {                       // the printed text of a number, with its source recorded
  if (!N[key]) throw new Error(`número desconocido: ${key}`);
  USED.set(key, N[key]);
  return N[key].text;
};
const V = (key) => { T(key); return Number(N[key].value); };
const DRAWN = new Set();
const CI = (key) => { DRAWN.add(key); return T(key).split("–").map(Number); };

// ---- brand (docs/brand.md), the same values as deck.cjs
const C = { deep: "1B3349", navy: "3A5B76", tealText: "137273", teal: "2AAEAE", tealSoft: "E3F5F5", sky: "EAF4F8",
  skySoft: "F4F9FB", ink: "1B2B38", muted: "4F5F6B", white: "FFFFFF", danger: "B42318", dangerSoft: "FDECEA",
  warn: "8A5A00", warnSoft: "FFF4DF", line: "D5E3EA", chart1: "0094A6", chart2: "3159B8" };
const HEAD = "Plus Jakarta Sans", BODY = "Atkinson Hyperlegible";
const W = 13.333, M = 0.6;

// ---- logo and icons as PNG (rsvg-convert)
const LUCIDE = "/opt/biblia/node_modules/lucide-static/icons";
function svgPng(svgText, name, width) {
  const svg = path.join(ASSETS, `${name}.svg`), png = path.join(ASSETS, `${name}.png`);
  fs.writeFileSync(svg, svgText);
  execFileSync("rsvg-convert", ["-w", String(width), "-o", png, svg]);
  return png;
}
const logo = (file, name, w) => svgPng(fs.readFileSync(path.join(ROOT, "frontend/public", file), "utf8"), name, w);
const LOGO_WHITE = logo("logo-white.svg", "logo-white", 1200);
const MARK = logo("logo-mark.svg", "logo-mark", 300);
const icon = (name, color) => svgPng(fs.readFileSync(path.join(LUCIDE, `${name}.svg`), "utf8")
  .replace(/currentColor/g, `#${color}`).replace(/stroke-width="2"/, 'stroke-width="2.2"'), `i-${name}-${color}`, 256);
const sizeOf = (png) => { const b = fs.readFileSync(png); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; };

// ---- deck
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                // 13.333 x 7.5 in
pres.title = "Enlaza · cuidado coordinado · Coloquio (con capturas)";
pres.author = "Equipo Enlaza";
pres.company = "Enlaza Cuidado Coordinado (proyecto escolar, UNRC)";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

pres.defineSlideMaster({
  title: "CONTENIDO", background: { color: C.white },
  objects: [
    { image: { path: MARK, x: W - M - 0.42, y: 6.86, w: 0.42, h: 0.42 } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: W - 2 * M, h: 1.0, fontFace: HEAD,
      fontSize: 36, bold: true, color: C.deep, valign: "middle", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: W - M - 1.25, y: 6.9, w: 0.7, h: 0.35, fontFace: BODY, fontSize: 14, color: C.muted, align: "right" },
});
pres.defineSlideMaster({ title: "OSCURO", background: { color: C.deep },
  slideNumber: { x: W - M - 0.7, y: 6.9, w: 0.7, h: 0.35, fontFace: BODY, fontSize: 14, color: "C9D6E0", align: "right" } });

let slideNo = 0;
function slide(master, section) {
  if (section) pres.addSection({ title: section });
  const s = pres.addSlide({ masterName: master, sectionTitle: section ? section : undefined });
  slideNo += 1;
  if (NOTES[slideNo]) s.addNotes(NOTES[slideNo]);
  return s;
}
const runs = (parts, color = C.deep, hl = C.tealText) =>
  parts.map((p) => (Array.isArray(p) ? { text: p[0], options: { color: hl } } : { text: p, options: { color } }));
function title(s, parts) { s.addText(runs(parts), { placeholder: "title" }); }
function text(s, t, o) {
  s.addText(t, { isTextBox: true, fontFace: BODY, fontSize: 24, color: C.ink, margin: 0, valign: "top", ...o });
}
function source(s, t, dark = false) {
  text(s, `Fuente: ${t}`, { x: M, y: 6.82, w: W - 2 * M - 1.4, h: 0.5, fontSize: 14, color: dark ? "C9D6E0" : C.muted,
    valign: "middle", objectName: "Fuente" });
}
function card(s, x, y, w, h, fill = C.sky, name = "Tarjeta") {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.16, fill: { color: fill }, line: { color: fill },
    objectName: name });
}
function iconCircle(s, x, y, d, name, color = C.tealText, fill = C.tealSoft) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: `Ícono ${name}` });
  const k = d * 0.56;
  s.addImage({ path: icon(name, color), x: x + (d - k) / 2, y: y + (d - k) / 2, w: k, h: k, altText: name });
}
function image(s, file, x, y, w, alt) {
  const { w: pw, h: ph } = sizeOf(file);
  const h = (w * ph) / pw;
  s.addImage({ path: file, x, y, w, h, altText: alt });
  return h;
}

// ---- screenshots with numbered callouts -----------------------------------------------------------------------
// A crop from recortes.py, scaled to fit (w x h), framed. marks: [n, fx, fy] (fractions of the crop) or
// { n, fx, fy, box: [fx0, fy0, fx1, fy1], side } to also outline a zone (a row, a button) or put the number outside the
// image (side "left" or "right"). Returns where it was placed.
const DOT = 0.62;
function numberDot(s, n, x, y, name) {
  s.addShape(pres.shapes.OVAL, { x, y, w: DOT, h: DOT, fill: { color: C.deep }, line: { color: C.white, width: 2.5 },
    objectName: name });
  text(s, String(n), { x, y, w: DOT, h: DOT, fontFace: HEAD, bold: true, color: C.white, align: "center", valign: "middle",
    objectName: `${name} · número` });
}
function shot(s, crop, alt, x, y, maxW, maxH, marks = [], align = "left") {
  const file = path.join(CROPS, `${crop}.png`);
  if (!fs.existsSync(file)) throw new Error(`Falta el recorte ${file}: correr recortes.py`);
  const { w: pw, h: ph } = sizeOf(file);
  let w = maxW, h = (maxW * ph) / pw;
  if (h > maxH) { h = maxH; w = (maxH * pw) / ph; }
  if (align === "center") x += (maxW - w) / 2;
  s.addImage({ path: file, x, y, w, h, altText: alt });
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { type: "none" }, line: { color: C.line, width: 1.25 }, objectName: "Marco" });
  for (const m of marks) {
    const { n, fx, fy, box, side } = Array.isArray(m) ? { n: m[0], fx: m[1], fy: m[2] } : m;
    if (box) {
      const [a, b, c, d] = box;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + a * w, y: y + b * h, w: (c - a) * w, h: (d - b) * h, rectRadius: 0.08,
        fill: { type: "none" }, line: { color: C.warn, width: 4.5 }, objectName: `Marca ${n}` });
    }
    // side: "left" / "right" puts the number just outside the image, next to a row, so it covers no text
    const px = side === "left" ? x - DOT - 0.1 : side === "right" ? x + w + 0.1 : x + fx * w - DOT / 2;
    const py = side === "top" ? y - DOT - 0.06 : y + fy * h - DOT / 2;
    const cx = Math.min(Math.max(px, 0.05), W - DOT - 0.05);
    const cy = Math.min(Math.max(py, 0.05), 7.5 - DOT - 0.05);
    numberDot(s, n, cx, cy, `Llamada ${n}`);
  }
  return { x, y, w, h };
}
// the legend of the callouts: the same numbered circle and its short text
function legend(s, items, x, y, w, rowH = 1.0) {
  items.forEach(([n, t], i) => {
    const yy = y + i * rowH;
    numberDot(s, n, x, yy + 0.04, `Leyenda ${n}`);
    text(s, t, { x: x + DOT + 0.2, y: yy, w: w - DOT - 0.2, h: rowH - 0.08, objectName: `Texto de la llamada ${n}` });
  });
}
function stepTag(s, t) {        // "Paso 1 de 4" on the demo slides, top right (24 pt)
  text(s, t, { x: W - M - 2.7, y: 0.5, w: 2.7, h: 0.6, color: C.tealText, bold: true, align: "right", valign: "middle",
    objectName: "Paso" });
}

function namesBand(s) {
  const t = NAMES.length ? `${TEAM[0]} · ${TEAM[1]}\n${TEAM[2]} · ${TEAM[3]}` : TEAM.join(" · ");
  text(s, t, { x: M, y: 5.8, w: W - 2 * M - 0.9, h: 0.95, color: C.white, bold: true, valign: "middle", objectName: "Equipo" });
}
function qrCard(s, caption) {
  card(s, 8.75, 0.6, 4.0, 4.95, C.white, "Tarjeta QR");
  s.addImage({ path: QR, x: 9.15, y: 0.8, w: 3.2, h: 3.2, altText: "QR de https://enlaza.zenthinks.com" });
  text(s, "enlaza.zenthinks.com", { x: 8.85, y: 4.1, w: 3.8, h: 0.55, fontFace: HEAD, bold: true, color: C.deep, align: "center" });
  text(s, caption, { x: 8.85, y: 4.7, w: 3.8, h: 0.5, color: C.tealText, align: "center" });
}
// a big figure with its label (Plus Jakarta Sans, as in deck.cjs)
function figure(s, big, label, x, y, w, color = C.deep, size = 40) {
  text(s, big, { x, y, w, h: 0.72, fontFace: HEAD, fontSize: size, bold: true, color });
  text(s, label, { x, y: y + 0.72, w, h: 0.5 });
}
function limitCard(s, t, x, y, w, h) {    // the honest limitation of each subject
  card(s, x, y, w, h, C.warnSoft, "Limitación");
  iconCircle(s, x + 0.2, y + (h - 0.7) / 2, 0.7, "triangle-alert", C.warn, C.white);
  text(s, [{ text: "Limitación: ", options: { bold: true } }, { text: t }], { x: x + 1.05, y: y + 0.08, w: w - 1.25, h: h - 0.16,
    valign: "middle" });
}

// ======================================================================= 1. Portada
{
  const s = slide("OSCURO", "Exposición");
  image(s, LOGO_WHITE, M, 0.6, 4.4, "Enlaza · cuidado coordinado");
  text(s, "Coordinamos el cuidado de las personas mayores", { x: M, y: 2.15, w: 7.6, h: 1.4,
    fontFace: HEAD, fontSize: 36, bold: true, color: C.white });
  text(s, "Universidad Nacional “Rosario Castellanos”\nLicenciatura en Ciencia de Datos para Negocios\nEvidencia integradora · 2026-2",
    { x: M, y: 3.7, w: 7.9, h: 1.45, color: "D6E4EE" });
  qrCard(s, "Pruébala después");
  namesBand(s);
}

// ======================================================================= 2. El problema
{
  const s = slide("CONTENIDO");
  title(s, ["Muchas personas mayores, cuidado ", ["a mano"]]);
  const stats = [
    [T("seed.pop60_cdmx"), "personas de 60 años o más viven en la Ciudad de México", "INEGI, Censo 2020"],
    [T("ctx.mexico_60mas_2024"), "personas de 60 años o más en todo México", "INEGI, ENASEM 2024"],
    [T("cal.ref_multimorbidity"), "vive con dos o más enfermedades crónicas", "ENSANUT 2018-19 (Salinas-Rodríguez et al., 2020)"],
  ];
  const cw = (W - 2 * M - 2 * 0.3) / 3;
  stats.forEach(([big, label, src], i) => {
    const x = M + i * (cw + 0.3);
    card(s, x, 1.55, cw, 3.25, C.sky, `Cifra ${i + 1}`);
    // "17.7 millones": the figure big and the word smaller, in the same box (so the PDF has the whole text)
    const [fig, ...rest] = big.split(" ");
    const word = rest.length && !rest[0].startsWith("%") ? rest.join(" ") : "";
    text(s, word ? [{ text: fig }, { text: ` ${word}`, options: { fontSize: 28 } }] : big, { x: x + 0.3, y: 1.8, w: cw - 0.6, h: 0.85,
      fontFace: HEAD, fontSize: 44, bold: true, color: C.deep });
    text(s, (word ? "de " : "") + label, { x: x + 0.3, y: 2.75, w: cw - 0.6, h: 1.25 });
    text(s, src, { x: x + 0.3, y: 4.1, w: cw - 0.6, h: 0.5, fontSize: 14, color: C.muted, objectName: "Fuente de la cifra" });
  });
  const pains = [["phone", "Llamadas y WhatsApp"], ["sheet", "Hojas de cálculo"], ["clock", "Lo urgente compite con lo rutinario"]];
  pains.forEach(([ic, label], i) => {
    const x = M + i * (cw + 0.3);
    iconCircle(s, x, 5.25, 0.95, ic);
    text(s, label, { x: x + 1.15, y: 5.2, w: cw - 1.15, h: 1.05, valign: "middle" });
  });
  source(s, "INEGI (Censo 2020, ENASEM 2024) · ENSANUT 2018-19: 2 o más de 7 condiciones crónicas, 60 años y más");
}

// ======================================================================= 3. La solución y cómo funciona
{
  const s = slide("CONTENIDO");
  title(s, ["Una sola plataforma, ", ["por dentro"]]);
  // the six modules in one compact row (short names; each subject has its own slide, 8 to 13)
  const mods = [["clipboard-list", "SIE"], ["chart-spline", "Simulación"], ["mic", "Voz"], ["chart-column", "Tableros"],
    ["briefcase", "Negocio"], ["shield-check", "Ética"]];
  const gap = 0.12, cw = (W - 2 * M - 5 * gap) / 6;
  mods.forEach(([ic, label], i) => {
    const x = M + i * (cw + gap);
    card(s, x, 1.45, cw, 1.45, C.skySoft, `Módulo ${label}`);
    iconCircle(s, x + (cw - 0.7) / 2, 1.53, 0.7, ic);
    text(s, label, { x: x + 0.05, y: 2.28, w: cw - 0.1, h: 0.5, bold: true, align: "center", valign: "middle" });
  });
  // two lanes (visits, voice) of four boxes joined by arrows, and the database underneath
  const lane = (y, label, boxes, fills) => {
    text(s, label, { x: M, y, w: 1.55, h: 1.3, bold: true, color: C.tealText, valign: "middle", objectName: `Carril ${label}` });
    const x0 = M + 1.6, g = 0.4, bw = (W - M - x0 - g * (boxes.length - 1)) / boxes.length;
    boxes.forEach((t, i) => {
      const x = x0 + i * (bw + g);
      card(s, x, y, bw, 1.3, fills[i], `Paso ${label} ${i + 1}`);
      text(s, t, { x: x + 0.1, y: y + 0.05, w: bw - 0.2, h: 1.2, align: "center", valign: "middle" });
      if (i < boxes.length - 1) {
        s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + 0.06, y: y + 0.47, w: g - 0.12, h: 0.36, fill: { color: C.navy },
          line: { color: C.navy }, objectName: "Flecha" });
      }
    });
  };
  lane(3.1, "Visitas", ["Llega una solicitud", "Se elige quién va", "Lo delicado lo aprueba una persona", "Tablero en vivo"],
    [C.sky, C.sky, C.warnSoft, C.tealSoft]);
  lane(4.55, "Voz", ["Nota de voz o escrita", "Primero, reglas", "Luego, el clasificador", "Resumen sin diagnóstico"],
    [C.sky, C.dangerSoft, C.warnSoft, C.tealSoft]);
  card(s, M, 6.0, W - 2 * M, 0.75, C.skySoft, "Datos");
  iconCircle(s, M + 0.15, 6.05, 0.65, "database");
  text(s, [{ text: "Una sola base de datos: ", options: { bold: true } }, { text: "cada institución ve solo lo suyo." }],
    { x: M + 1.0, y: 6.0, w: W - 2 * M - 1.2, h: 0.75, valign: "middle" });
}

// ======================================================================= 4. Paso 1 · La familia pide y se asigna sola
{
  const s = slide("CONTENIDO", "La app en capturas");
  title(s, ["La familia pide ", ["y se asigna sola"]]);
  stepTag(s, "Paso 1 de 4");
  shot(s, "c02_asignada", "Celular de la familia: visita de enfermería para hoy, asignada, y quién va", M, 1.45, 5.0, 2.5,
    [[1, 0.53, 0.66], [2, 0.93, 0.9]]);
  legend(s, [[1, "Pidió para hoy: ya dice «Asignada»"], [2, "Y quién va"],
    [3, "En el tablero: Víctor Chávez, marcada «Nueva»"]], 6.0, 1.5, W - M - 6.0, 0.85);
  shot(s, "c03_nuevas", "Tablero de coordinación: la visita de Víctor Chávez aparece sola, marcada Nueva, ya asignada",
    M + 0.75, 4.2, W - 2 * M - 0.75, 2.5, [{ n: 3, side: "left", fy: 0.75, box: [0.0, 0.5, 1.0, 1.0] }]);
  source(s, "capturas de la app en vivo: celular de la familia y tablero de coordinación · datos sintéticos");
}

// ======================================================================= 5. Paso 2 · Lo urgente lo decide una persona
{
  const s = slide("CONTENIDO");
  title(s, ["Lo urgente lo decide ", ["una persona"]]);
  stepTag(s, "Paso 2 de 4");
  shot(s, "c05_urgente", "Aprobaciones: solicitud urgente de prioridad alta con la persona propuesta y dos alternativas con su tiempo de viaje",
    M, 1.45, W - 2 * M, 2.55, [[1, 0.89, 0.08], [2, 0.3, 0.44], [3, 0.6, 0.44]], "center");
  legend(s, [[1, `Prioridad alta, visita en menos de ${T("cfg.urgent_within")}`], [2, "Enlaza propone a quien llega antes"],
    [3, "Alternativas, con su tiempo de viaje"]], M, 4.15, 6.1, 0.86);
  const x = 6.95, w = W - M - x;
  card(s, x, 4.15, w, 2.6, C.warnSoft, "Regla de lo urgente");
  text(s, [{ text: "Solo para lo urgente: ", options: { bold: true } },
    { text: `sin respuesta en ${T("cfg.auto_apply_after")}, se aplica con aviso.` }],
  { x: x + 0.25, y: 4.22, w: w - 0.5, h: 1.2 });
  text(s, "Lo de prioridad alta que no es urgente siempre espera a una persona.", { x: x + 0.25, y: 5.45, w: w - 0.5, h: 1.25,
    bold: true, color: C.warn });
  source(s, "captura de la app en vivo (/aprobaciones), solicitud urgente del panel de demostración · config/simulation.yaml");
}

// ======================================================================= 6. Paso 3 · Contingencia en el oriente
{
  const s = slide("CONTENIDO");
  title(s, ["Contingencia en el ", ["oriente"]]);
  stepTag(s, "Paso 3 de 4");
  const m = shot(s, "c07_mapa", "Mapa de estaciones: Iztapalapa en Fase I por PM2.5, alcaldías vecinas en vigilancia", M, 1.45, 4.4, 3.5,
    [[1, 0.5, 0.33]]);
  text(s, "Nada cambia hasta que coordinación aprueba.", { x: M, y: m.y + m.h + 0.2, w: m.w, h: 0.9, bold: true, color: C.deep });
  const q = shot(s, "c08_propuesta", "Propuesta de Enlaza: subir la prioridad de dos pacientes sensibles, adelantar una oxigenoterapia y avisar a 16 familias",
    m.x + m.w + 0.85, 1.45, 3.6, 5.25, [{ n: 2, side: "left", fy: 0.19 }, { n: 3, side: "left", fy: 0.64 }]);
  legend(s, [[1, "Fase I por estación, no promediada"], [2, "Subir la prioridad de los sensibles"],
    [3, "Adelantar la oxigenoterapia próxima"]], q.x + q.w + 0.2, 1.5, W - M - (q.x + q.w + 0.2), 1.4);
  source(s, "captura de la app en vivo (/contingencia), escenario de demostración «Contingencia en el oriente» · datos sintéticos");
}

// ======================================================================= 7. Paso 4 · Nota de emergencia y lo que recibe la médica
{
  const s = slide("CONTENIDO");
  title(s, ["Emergencia: ", ["rojo y reporte"]]);
  stepTag(s, "Paso 4 de 4");
  const a = shot(s, "c10_roja", "Pantalla roja a pantalla completa: Esto puede ser una emergencia. Llama al 911 ahora", M, 1.45, 3.1, 3.95,
    [{ n: 1, side: "right", fy: 0.3 }]);
  shot(s, "c11_medica", "Reporte de voz para la médica: transcripción, regla que se activó, resumen y la limitación: no es diagnóstico",
    a.x + a.w + 0.85, 1.45, W - M - (a.x + a.w + 0.85), 3.95, [[2, 0.9, 0.415], [3, 0.9, 0.975]]);
  const cols = [[1, "«Llama al 911», antes que la IA"], [2, "La médica ve la regla que se activó"], [3, "«No es diagnóstico»"]];
  cols.forEach(([n, t], i) => legend(s, [[n, t]], M + i * 4.1, 5.6, 3.95, 1.1));
  source(s, "capturas de la app en vivo: celular de la familia y /reportes-voz de la médica · datos sintéticos");
}

// ======================================================================= 8. SIE
{
  const s = slide("CONTENIDO", "Las seis materias");
  title(s, ["SIE: la operación ", ["en un solo lugar"]]);
  const a = shot(s, "c12_fila", "Personal y turnos: Diana Cortés, jornada nocturna de 20:00 a 08:00, Excede la jornada legal", M + 0.75, 1.45, 6.9, 1.35,
    [{ n: 1, side: "left", fy: 0.45 }]);
  shot(s, "c12_detalle", "Agenda de Diana Cortés: excede la jornada legal; lo decide la institución, Enlaza no cambia la plantilla",
    M + 0.75, 3.0, 6.9, 1.5, [{ n: 2, side: "left", fy: 0.45 }]);
  legend(s, [[1, "Turno nocturno de 12 h: se marca"], [2, "No se corrige: lo decide la institución"]], M, 4.6, 7.7, 0.6);
  const x = 8.75, w = W - M - x;
  text(s, T("seed.assign_auto"), { x, y: 1.4, w, h: 0.72, fontFace: HEAD, fontSize: 40, bold: true, color: C.tealText });
  text(s, "asignadas solas", { x, y: 2.12, w, h: 0.5 });
  text(s, T("seed.assign_coordinator"), { x, y: 2.75, w, h: 0.72, fontFace: HEAD, fontSize: 40, bold: true, color: C.deep });
  text(s, "aprobadas por coordinación", { x, y: 3.47, w, h: 0.9 });
  text(s, `de ${T("seed.service_requests")} solicitudes del historial`, { x, y: 4.5, w, h: 0.9, color: C.muted });
  limitCard(s, "ERP acotado (personal, turnos y agenda); sin prueba con una institución real.", M, 5.95, W - 2 * M, 0.8);
  source(s, `captura de la app en vivo (/personal, INS-B) · historial sintético de ${T("seed.history_days")} días (database/seed/)`);
}

// ======================================================================= 9. Modelado y Simulación
{
  const s = slide("CONTENIDO");
  title(s, ["La simulación nos dijo ", ["cómo asignar"]]);
  const a = shot(s, "c13_grafica", "Gráfica de SIRAG-D: espera p90 de prioridad alta por política, con intervalos de confianza, escenario normal",
    M, 1.45, 8.3, 3.3, [[1, 0.9, 0.51], [2, 0.97, 0.83]]);
  legend(s, [[1, "Prioridad por riesgo"], [2, "Despacho humano (como hoy)"]], M, a.y + a.h + 0.2, 8.3, 0.62);
  const x = 9.15, w = W - M - x;
  card(s, x, 1.45, w, 2.15, C.sky, "Priorizar por riesgo");
  text(s, [{ text: T("sim.normal.human_dispatcher.high_wait_p90_min"), options: { color: C.deep } },
    { text: " a ", options: { color: C.ink, fontSize: 24, bold: false } },
    { text: T("sim.normal.risk_priority.high_wait_p90_min"), options: { color: C.tealText } }],
  { x: x + 0.2, y: 1.52, w: w - 0.4, h: 0.7, fontFace: HEAD, fontSize: 36, bold: true });
  text(s, `minutos de espera de lo urgente (${T("test.normal.high_wait_p90_min.risk_priority.p")})`, { x: x + 0.2, y: 2.22, w: w - 0.4, h: 1.3 });
  card(s, x, 3.72, w, 1.95, C.skySoft, "Aprobación lenta");
  text(s, `Aprobar en ${T("sens.approval_delay.5-15.label")}:`, { x: x + 0.2, y: 3.78, w: w - 0.4, h: 0.45 });
  text(s, [{ text: T("sens.approval_delay.5-15.vela_timeout.high_wait_p90_min"), options: { bold: true, color: C.tealText } },
    { text: " con límite y reserva", options: { breakLine: true } },
    { text: T("sens.approval_delay.5-15.risk_plus_live_traffic.high_wait_p90_min"), options: { bold: true, color: C.deep } },
    { text: " sin ellos" }], { x: x + 0.2, y: 4.27, w: w - 0.4, h: 1.3 });
  limitCard(s, "datos sintéticos; con turnos largos difiere del historial.", M, 5.85, W - 2 * M, 0.85);
  source(s, `SIRAG-D · ${T("sim.runs_main")} corridas, ${T("cfg.replications")} réplicas · Friedman y Wilcoxon con Holm · captura de /simulacion`);
}

// ======================================================================= 10. Visualización
{
  const s = slide("CONTENIDO");
  title(s, ["Panorama-AM: ", ["ver para decidir"]]);
  const a = shot(s, "c14_contadores", "Panorama-AM: contadores en vivo de solicitudes en cola, en camino, en visita y terminadas", M + 0.75, 1.45, 7.25, 1.0,
    [{ n: 1, side: "left", fy: 0.5 }]);
  shot(s, "c14_cumplimos", "Panorama-AM: puntualidad y sin atender, antes de Enlaza y con Enlaza; con Enlaza dice datos insuficientes",
    M + 0.75, a.y + a.h + 0.2, 7.25, 3.3, [[2, 0.9, 0.12], { n: 3, side: "right", fy: 0.68 }]);
  legend(s, [[1, "Contadores en vivo"], [2, "Antes de Enlaza y con Enlaza"], [3, "Si faltan datos, lo dice"]], 9.55, 1.5, W - M - 9.55, 1.05);
  figure(s, T("seed.persons"), "personas sintéticas", 9.55, 4.55, W - M - 9.55, C.tealText, 32);
  limitCard(s, "la línea base es sintética; con Enlaza aún hay pocos datos.", M, 5.85, W - 2 * M, 0.85);
  source(s, "captura de la app en vivo (/panorama, Dirección) · personas calibradas con Censo 2020, ENSANUT y ENASEM");
}

// ======================================================================= 11. Cómputo Cognitivo
{
  const s = slide("CONTENIDO");
  title(s, ["Enlaza Voz: ", ["dos niveles"], " de aviso"]);
  const a = shot(s, "c10_roja", "Pantalla roja: se activó una regla de emergencia", M, 2.15, 3.0, 4.55, [{ n: 1, side: "top", fx: 0.5 }]);
  shot(s, "c17_ambar", "Aviso ámbar: solo el clasificador sospecha; coordinación llama a la familia", a.x + a.w + 0.3, 2.15, 3.0, 4.55,
    [{ n: 2, side: "top", fx: 0.5 }]);
  const x = 7.3, w = W - M - x;
  legend(s, [[1, "Regla de emergencia: rojo"], [2, "Solo el clasificador sospecha: ámbar; coordinación llama"]], x, 1.45, w, 1.0);
  text(s, T("voz.holdout.sens"), { x, y: 3.55, w, h: 0.65, fontFace: HEAD, fontSize: 36, bold: true, color: C.tealText });
  text(s, "de las emergencias detectadas", { x, y: 4.2, w, h: 0.5 });
  text(s, T("voz.holdout.fa100"), { x, y: 4.75, w: 1.9, h: 0.65, fontFace: HEAD, fontSize: 36, bold: true, color: C.danger });
  text(s, "falsas alarmas por 100 notas", { x: x + 1.95, y: 4.7, w: w - 1.95, h: 0.9, valign: "middle" });
  limitCard(s, "solo frases sintéticas.", x, 5.75, w, 0.9);
  source(s, `evaluación a ciegas (holdout) con ${T("voz.holdout.n")} frases que el modelo no vio · capturas de la app en celular`);
}

// ======================================================================= 12. Emprendimiento
{
  const s = slide("CONTENIDO");
  title(s, ["Un negocio viable, ", ["con su condición"]]);
  shot(s, "c15_escenarios", "Modelo de negocio: base, conservador y recomendado lado a lado", M, 1.45, W - 2 * M, 1.55, [], "center");
  // what is pointed at: the big tiles (recommended and base) and the condition, not the table
  const tiles = [[T("bm.sc.recommended.investment"), "inversión · recomendado", C.sky, C.deep, 0],
    [T("bm.sc.recommended.npv25"), `VPN al ${T("bm.rate_25")} · recomendado`, C.tealSoft, C.tealText, 1],
    [T("bm.sc.recommended.tir"), "TIR anual · recomendado", C.sky, C.deep, 0],
    [T("bm.sc.base.npv25"), `VPN al ${T("bm.rate_25")} · escenario base`, C.dangerSoft, C.danger, 2]];
  const gap = 0.25, tw = (W - 2 * M - 3 * gap) / 4, ty = 3.78;
  tiles.forEach(([big, label, fill, color, n], i) => {
    const x = M + i * (tw + gap);
    card(s, x, ty, tw, 1.55, fill, `Cifra ${label}`);
    text(s, big, { x: x + 0.2, y: ty + 0.1, w: tw - 0.4, h: 0.6, fontFace: HEAD, fontSize: 28, bold: true, color, valign: "middle" });
    text(s, label, { x: x + 0.2, y: ty + 0.72, w: tw - 0.4, h: 0.78 });
    if (n) numberDot(s, n, x + tw - DOT - 0.08, ty - DOT - 0.04, `Llamada ${n}`);
  });
  card(s, M, 5.48, W - 2 * M, 1.25, C.warnSoft, "Condición del escenario");
  iconCircle(s, M + 0.2, 5.7, 0.8, "triangle-alert", C.warn, C.white);
  text(s, [{ text: "Condición: ", options: { bold: true } },
    { text: `supone plan Gobierno y fundadores al ${T("neg.founder_salary_year1_recommended")} % el año 1; sin ambos, VPN ${T("bm.rec_wo_both")}.` }],
  { x: M + 1.2, y: 5.5, w: W - 2 * M - 2.1, h: 1.2, valign: "middle" });
  numberDot(s, 3, W - M - DOT - 0.15, 5.48 + (1.25 - DOT) / 2, "Llamada 3");
  source(s, "captura de la app en vivo (/negocio) · data/business/assumptions.csv");
}

// ======================================================================= 13. Práctica Profesional
{
  const s = slide("CONTENIDO");
  title(s, ["Privacidad y ética ", ["desde la base de datos"]]);
  const a = shot(s, "c16_bitacora", "Bitácora de Dirección: intento de una coordinación de INS-B a un paciente de INS-A, bloqueado",
    M + 0.75, 1.45, W - 2 * M - 1.5, 2.6, [{ n: 1, side: "left", fy: 0.62, box: [0.0, 0.27, 1.0, 0.99] }, { n: 2, side: "right", fy: 0.62 }]);
  legend(s, [[1, "Otra institución pidió un paciente de INS-A"]], M, a.y + a.h + 0.2, 6.6, 0.6);
  legend(s, [[2, "Bloqueado y registrado"]], 7.4, a.y + a.h + 0.2, W - M - 7.4, 0.6);
  // the security card right under the legend (no gap), a bit taller and with bigger figures
  const y0 = a.y + a.h + 1.2;
  card(s, M, y0, 6.3, 2.35, C.sky, "Seguridad por fila");
  text(s, "Pacientes que ve la API", { x: M + 0.25, y: y0 + 0.1, w: 5.8, h: 0.5, bold: true });
  [["db.rls_patients_none", "sin institución"], ["db.rls_patients_insa", "una clínica"], ["db.rls_patients_all", "Dirección"]]
    .forEach(([k, label], i) => {
      const x = M + 0.25 + [0, 2.2, 4.1][i];
      text(s, T(k), { x, y: y0 + 0.65, w: 1.85, h: 0.9, fontFace: HEAD, fontSize: 48, bold: true, color: i === 0 ? C.tealText : C.deep });
      text(s, label, { x, y: y0 + 1.6, w: [2.15, 1.85, 1.9][i], h: 0.55 });
    });
  const x = 7.15, w = W - M - x;
  [["file-check", "Sin consentimiento, la API bloquea"], ["calendar-clock", "Descanso respetado; jornada excedida, marcada"]].forEach(([ic, t], i) => {
    iconCircle(s, x, y0 + 0.2 + i * 1.15, 0.8, ic);
    text(s, t, { x: x + 1.0, y: y0 + 0.12 + i * 1.15, w: w - 1.0, h: 0.96, valign: "middle" });
  });
  source(s, `captura de la app en vivo (/privacidad, Dirección) · PostgreSQL como vela_api · ${T("repo.tests_summary")}`);
}

// ======================================================================= 14. Gracias (stays on screen during the questions)
{
  const s = slide("OSCURO", "Preguntas");
  image(s, LOGO_WHITE, M, 0.6, 3.8, "Enlaza · cuidado coordinado");
  text(s, "Gracias", { x: M, y: 1.85, w: 7.8, h: 1.4, fontFace: HEAD, fontSize: 80, bold: true, color: C.white });
  text(s, "¿Preguntas?", { x: M, y: 3.25, w: 7.8, h: 0.85, fontFace: HEAD, fontSize: 40, bold: true, color: "7FD3D3" });
  text(s, "Siguiente paso: piloto con una residencia real", { x: M, y: 4.3, w: 7.9, h: 0.9, color: C.white });
  qrCard(s, "La app sigue en vivo");
  namesBand(s);
}

// ======================================================================= 15. Respaldo · Mercado (DENUE)
{
  const s = slide("CONTENIDO", "Respaldo (no se presenta)");
  title(s, ["Respaldo: un mercado contado en el ", ["DENUE"]]);
  const states = [["cdmx", "CDMX"], ["edomex", "Edomex"], ["jalisco", "Jalisco"], ["nuevoleon", "Nuevo León"]];
  text(s, "Establecimientos privados por entidad", { x: M, y: 1.4, w: 7.3, h: 0.5, bold: true });
  s.addChart(pres.charts.BAR, [
    { name: "Residencias", labels: states.map(([, l]) => l), values: states.map(([k]) => V(`neg.denue_residences_private_${k}`)) },
    { name: "Centros de día", labels: states.map(([, l]) => l), values: states.map(([k]) => V(`neg.denue_day_centers_private_${k}`)) },
  ], {
    x: M, y: 1.9, w: 7.3, h: 4.8, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60, chartColors: [C.chart1, C.chart2],
    catAxisLabelFontFace: BODY, catAxisLabelFontSize: 24, catAxisLabelColor: C.ink, valAxisHidden: true, valAxisMinVal: 0,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showValue: true, dataLabelPosition: "outEnd",
    dataLabelColor: C.ink, dataLabelFontFace: HEAD, dataLabelFontSize: 24, dataLabelFontBold: true,
    showLegend: true, legendPos: "t", legendFontFace: BODY, legendFontSize: 24, legendColor: C.ink, showTitle: false,
  });
  const x = 8.4, w = W - M - x;
  figure(s, T("bm.arpa1"), "al mes por institución, año 1", x, 1.45, w, C.deep, 44);
  figure(s, T("bm.ltv_cac"), "valor de un cliente contra su costo", x, 3.0, w, C.tealText, 44);
  text(s, "Los públicos compran por licitación: plan aparte.", { x, y: 4.7, w, h: 1.3, color: C.muted });
  source(s, "INEGI, DENUE, sector 62 (mayo 2026) · data/business/assumptions.csv (lo mismo que /negocio)");
}

// ======================================================================= 16. Respaldo · Escenarios
{
  const s = slide("CONTENIDO");
  title(s, ["Respaldo: los tres ", ["escenarios"]]);
  shot(s, "c15_completo", "Modelo de negocio: base, conservador y recomendado, con inversión, equilibrio, VPN e instituciones",
    M, 1.45, W - 2 * M, 5.25, [], "center");
  source(s, "captura de la app en vivo (/negocio) · data/business/assumptions.csv");
}

// ======================================================================= 17. Respaldo · Las cinco políticas (20.1 y 20.2)
const ERRBARS = [];
{
  const s = slide("CONTENIDO");
  title(s, ["Respaldo: las cinco ", ["políticas"]]);
  const pol = [["human_dispatcher", "Despacho humano"], ["nearest", "Más cercano"], ["risk_priority", "Prioridad por riesgo"],
    ["risk_plus_live_traffic", "Riesgo + tráfico"], ["vela_timeout", "Enlaza con límite"]];
  const key = (p) => `sim.normal.${p}.high_wait_p90_min`;
  const vals = pol.map(([p]) => V(key(p)));
  const ci = pol.map(([p]) => CI(`${key(p)}.ci`));
  const cw = 7.4;
  text(s, "Espera p90 de lo urgente (minutos)", { x: M, y: 1.4, w: cw, h: 0.5, bold: true });
  const series = "Espera p90 de prioridad alta (min)";
  s.addChart(pres.charts.BAR, [{ name: series, labels: pol.map(([, l]) => l), values: vals }], {
    x: M, y: 1.95, w: cw, h: 4.35, barDir: "bar", catAxisOrientation: "maxMin", barGapWidthPct: 45,
    chartColors: [C.navy, C.navy, C.tealText, C.tealText, C.tealText],
    catAxisLabelFontFace: BODY, catAxisLabelFontSize: 24, catAxisLabelColor: C.ink, catAxisLineShow: false,
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 28, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "inBase", dataLabelColor: C.white, dataLabelFontFace: HEAD, dataLabelFontSize: 24,
    dataLabelFontBold: true, dataLabelFormatCode: "0.0", showLegend: false, showTitle: false,
  });
  ERRBARS.push({ series, plus: vals.map((v, i) => +(ci[i][1] - v).toFixed(2)), minus: vals.map((v, i) => +(v - ci[i][0]).toFixed(2)) });
  text(s, `Barra: promedio de ${T("cfg.replications")} réplicas · línea: intervalo de confianza del ${T("cfg.confidence")}`,
    { x: M, y: 6.33, w: cw, h: 0.4, fontSize: 14, color: C.muted, objectName: "Nota de la gráfica" });
  const x = M + cw + 0.4, w = W - M - x;
  card(s, x, 1.45, w, 4.9, C.sky, "Por qué la app dice 20.1");
  text(s, "¿Por qué la app dice otra cifra?", { x: x + 0.3, y: 1.6, w: w - 0.6, h: 0.9, bold: true, color: C.tealText });
  text(s, [{ text: T("sim.normal.risk_priority.high_wait_p90_min"), options: { bold: true } },
    { text: ": priorizar por riesgo", options: { breakLine: true } },
    { text: T("sim.normal.vela_timeout.high_wait_p90_min"), options: { bold: true } },
    { text: ": Enlaza con el límite de tiempo", options: { breakLine: true } },
    { text: "Las dos contra " }, { text: T("sim.normal.human_dispatcher.high_wait_p90_min"), options: { bold: true } },
    { text: " de la asignación humana." }], { x: x + 0.3, y: 2.6, w: w - 0.6, h: 3.6 });
  source(s, `SIRAG-D, corrida vigente con plantilla legal · ${T("sim.runs_main")} corridas · Friedman y Wilcoxon con Holm`);
}

// ---- write
(async () => {
  const file = OUTFILE;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  await pres.writeFile({ fileName: file });
  fs.writeFileSync(path.join(OUT, "errbars.json"), JSON.stringify(ERRBARS));
  const rows = [["clave", "texto", "fuente", "uso"], ...[...USED].map(([k, d]) => [k, d.text, d.source, DRAWN.has(k) ? "gráfica" : "texto"])];
  fs.writeFileSync(path.join(OUT, "numeros_usados.csv"), rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n"));
  console.log(`Presentación: ${file} (${slideNo} diapositivas, ${USED.size} números)`);
})();
