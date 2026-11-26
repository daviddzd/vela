// Colloquium deck -> docs/presentacion/enlaza_coloquio.pptx (editable text, native charts, speaker notes).
//
//   node docs/presentacion/build/deck.cjs      (inside the vela-presentacion image; see scripts/build_presentacion.sh)
//
// No number is typed here: T("key") takes the text from docs/biblia/out/numeros.json (the same script as the book) and
// records it in out/numeros_usados.csv. Speaker notes come from guion_fuente.md (out/notas.json, render_guion.py).
// Brand: docs/brand.md (deep navy, teal-text, Plus Jakarta Sans for titles and figures, Atkinson Hyperlegible for text).
// Every text is 24 pt or more, except the source lines and the slide number (14 pt).
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const PRES = path.join(ROOT, "docs", "presentacion");
const OUT = path.join(PRES, "out");
const ASSETS = path.join(OUT, "assets");
fs.mkdirSync(ASSETS, { recursive: true });
const N = JSON.parse(fs.readFileSync(path.join(ROOT, "docs/biblia/out/numeros.json"), "utf8"));
const NOTES = JSON.parse(fs.readFileSync(path.join(OUT, "notas.json"), "utf8"));
const SHOTS = path.join(PRES, "capturas");
const QR = path.join(ROOT, "docs", "privado", "qr_enlaza.png");
if (!fs.existsSync(QR)) throw new Error("Falta docs/privado/qr_enlaza.png: correr `uv run scripts/make_qr.py`");

const USED = new Map();
const T = (key) => {                       // the printed text of a number, with its source recorded
  if (!N[key]) throw new Error(`número desconocido: ${key}`);
  USED.set(key, N[key]);
  return N[key].text;
};
const V = (key) => { T(key); return Number(N[key].value); };                 // numeric value (charts)
const DRAWN = new Set();                   // numbers only drawn (error bars): the check does not look for them as text
const CI = (key) => { DRAWN.add(key); return T(key).split("–").map(Number); };   // "17.7–22.4" -> [17.7, 22.4]
const LABEL = new Map();                   // numbers shown as a chart data label (without their unit): key -> label text
const PCT = (key) => { const v = Number(T(key).replace(/[^\d.]/g, "")); LABEL.set(key, v.toFixed(1)); return v; };  // "17.1 %" -> 17.1

// ---- brand (docs/brand.md)
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
const LOGO = logo("logo.svg", "logo", 1200), LOGO_WHITE = logo("logo-white.svg", "logo-white", 1200);
const MARK = logo("logo-mark.svg", "logo-mark", 300);
const icon = (name, color) => svgPng(fs.readFileSync(path.join(LUCIDE, `${name}.svg`), "utf8")
  .replace(/currentColor/g, `#${color}`).replace(/stroke-width="2"/, 'stroke-width="2.2"'), `i-${name}-${color}`, 256);
const sizeOf = (png) => { const b = fs.readFileSync(png); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; };

// ---- deck
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                // 13.333 x 7.5 in
pres.title = "Enlaza · cuidado coordinado · Coloquio";
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
// title with one word in teal-text (brand "Highlight"); parts: ["La simulación ", ["cambió"], " el producto"]
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
function image(s, file, x, y, w, alt) {          // keeps the aspect ratio; returns the height used
  const { w: pw, h: ph } = sizeOf(file);
  const h = (w * ph) / pw;
  s.addImage({ path: file, x, y, w, h, altText: alt });
  return h;
}

// ======================================================================= 1. Portada
{
  const s = slide("OSCURO", "Exposición");
  image(s, LOGO_WHITE, M, 0.6, 4.4, "Enlaza · cuidado coordinado");
  text(s, "Coordinamos el cuidado de las personas mayores", { x: M, y: 2.35, w: 7.6, h: 1.4,
    fontFace: HEAD, fontSize: 36, bold: true, color: C.white });
  text(s, "Universidad Nacional “Rosario Castellanos”\nLicenciatura en Ciencia de Datos para Negocios\nEvidencia integradora · 2026-2",
    { x: M, y: 3.95, w: 7.9, h: 1.45, color: "D6E4EE" });
  text(s, "Persona 1 · Persona 2 · Persona 3 · Persona 4", { x: M, y: 5.75, w: 7.6, h: 0.5, color: C.white, bold: true });
  card(s, 8.75, 0.9, 4.0, 5.55, C.white, "Tarjeta QR");
  s.addImage({ path: QR, x: 9.05, y: 1.1, w: 3.4, h: 3.4, altText: "QR de https://enlaza.zenthinks.com" });
  text(s, "enlaza.zenthinks.com", { x: 8.85, y: 4.6, w: 3.8, h: 0.55, fontFace: HEAD, bold: true, color: C.deep, align: "center" });
  text(s, "Entra desde tu celular", { x: 8.85, y: 5.25, w: 3.8, h: 0.5, color: C.tealText, align: "center" });
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
    // "17.7 millones": the figure big, the word joins the label
    const [fig, ...rest] = big.split(" ");
    const lead = rest.length && !rest[0].startsWith("%") ? rest.join(" ") + " de " : "";
    text(s, rest.length && rest[0].startsWith("%") ? big : fig, { x: x + 0.3, y: 1.8, w: cw - 0.6, h: 0.85, fontFace: HEAD,
      fontSize: 44, bold: true, color: C.deep });
    text(s, lead + label, { x: x + 0.3, y: 2.75, w: cw - 0.6, h: 1.25 });
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

// ======================================================================= 3. La solución
{
  const s = slide("CONTENIDO");
  title(s, ["Enlaza: ", ["una sola plataforma"], " para todo el cuidado"]);
  text(s, "Asigna sola cada visita, deja lo delicado a una persona y avisa a tiempo de una emergencia.",
    { x: M, y: 1.4, w: W - 2 * M, h: 0.9, fontSize: 28, color: C.ink });
  const mods = [["clipboard-list", "Operación y tablero en vivo", "SIE"], ["chart-spline", "SIRAG-D · simulación", "Modelado y Simulación"],
    ["mic", "Enlaza Voz", "Cómputo Cognitivo"], ["chart-column", "Panorama-AM · tableros", "Visualización"],
    ["briefcase", "Modelo de negocio", "Emprendimiento"], ["shield-check", "Consentimientos y ética", "Práctica Profesional"]];
  const cw = (W - 2 * M - 0.3) / 2, ch = 1.22;
  mods.forEach(([ic, mod, subject], i) => {
    const x = M + (i % 2) * (cw + 0.3), y = 2.6 + Math.floor(i / 2) * (ch + 0.2);
    card(s, x, y, cw, ch, C.skySoft, `Módulo ${mod}`);
    iconCircle(s, x + 0.25, y + (ch - 0.85) / 2, 0.85, ic);
    s.addText([{ text: mod, options: { bold: true, color: C.ink, breakLine: true } }, { text: subject, options: { color: C.tealText } }],
      { isTextBox: true, x: x + 1.35, y: y + 0.12, w: cw - 1.5, h: ch - 0.24, fontFace: BODY, fontSize: 24, margin: 0, valign: "middle" });
  });
}

// ======================================================================= 4. Demostración en vivo (pausa)
{
  const s = slide("OSCURO", "Demostración");
  text(s, [{ text: "Demostración ", options: { color: C.white } }, { text: "en vivo", options: { color: "7FD3D3" } }],
    { x: M, y: 0.55, w: 7.8, h: 1.0, fontFace: HEAD, fontSize: 44, bold: true });
  const steps = ["La familia pide una visita y se asigna sola", "Coordinación aprueba lo urgente y el tablero cambia en vivo",
    "Contingencia en el oriente: propuesta y aprobación", "Voz de emergencia: la pantalla roja del 911"];
  steps.forEach((t, i) => {
    const y = 1.85 + i * 1.12;
    s.addShape(pres.shapes.OVAL, { x: M, y: y + 0.05, w: 0.75, h: 0.75, fill: { color: C.tealText }, line: { color: C.tealText },
      objectName: `Paso ${i + 1}` });
    text(s, String(i + 1), { x: M, y: y + 0.05, w: 0.75, h: 0.75, fontFace: HEAD, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, t, { x: M + 1.0, y, w: 6.9, h: 0.9, color: C.white, valign: "middle" });
  });
  card(s, 8.75, 0.9, 4.0, 5.55, C.white, "Tarjeta QR");
  s.addImage({ path: QR, x: 9.05, y: 1.1, w: 3.4, h: 3.4, altText: "QR de https://enlaza.zenthinks.com" });
  text(s, "enlaza.zenthinks.com", { x: 8.85, y: 4.6, w: 3.8, h: 0.55, fontFace: HEAD, bold: true, color: C.deep, align: "center" });
  text(s, "Síguelo en tu celular", { x: 8.85, y: 5.25, w: 3.8, h: 0.5, color: C.tealText, align: "center" });
}

// ======================================================================= 5. Simulación
const ERRBARS = [];
{
  const s = slide("CONTENIDO", "Resultados");
  title(s, ["La simulación ", ["cambió"], " el producto"]);
  const pol = [["human_dispatcher", "Despacho humano"], ["nearest", "Más cercano"], ["risk_priority", "Prioridad por riesgo"],
    ["risk_plus_live_traffic", "Riesgo + tráfico"], ["vela_timeout", "Enlaza hoy"]];
  const key = (p) => `sim.normal.${p}.high_wait_p90_min`;
  const vals = pol.map(([p]) => V(key(p)));
  const ci = pol.map(([p]) => CI(`${key(p)}.ci`));
  text(s, "Espera p90 de lo urgente (minutos)", { x: M, y: 1.4, w: 7.7, h: 0.5, bold: true, color: C.ink });
  const series = "Espera p90 de prioridad alta (min)";
  s.addChart(pres.charts.BAR, [{ name: series, labels: pol.map(([, l]) => l), values: vals }], {
    x: M, y: 1.95, w: 7.7, h: 4.35, barDir: "bar", catAxisOrientation: "maxMin", barGapWidthPct: 45,
    chartColors: [C.navy, C.navy, C.navy, C.navy, C.tealText],
    catAxisLabelFontFace: BODY, catAxisLabelFontSize: 24, catAxisLabelColor: C.ink, catAxisLineShow: false,
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 28, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "inBase", dataLabelColor: C.white, dataLabelFontFace: HEAD, dataLabelFontSize: 24,
    dataLabelFontBold: true, dataLabelFormatCode: "0.0", showLegend: false, showTitle: false,
  });
  ERRBARS.push({ series, plus: vals.map((v, i) => +(ci[i][1] - v).toFixed(2)), minus: vals.map((v, i) => +(v - ci[i][0]).toFixed(2)) });
  text(s, `Barra: promedio de ${T("cfg.replications")} réplicas · línea: intervalo de confianza del ${T("cfg.confidence")}`,
    { x: M, y: 6.33, w: 7.7, h: 0.4, fontSize: 14, color: C.muted, objectName: "Nota de la gráfica" });
  const x = 8.65, w = W - M - x;
  card(s, x, 1.4, w, 5.3, C.sky, "Hallazgo");
  text(s, "El hallazgo", { x: x + 0.3, y: 1.6, w: w - 0.6, h: 0.45, bold: true, color: C.tealText });
  text(s, "Con coordinación lenta, lo urgente esperaba más que con una persona.", { x: x + 0.3, y: 2.05, w: w - 0.6, h: 1.65 });
  text(s, "El cambio", { x: x + 0.3, y: 3.75, w: w - 0.6, h: 0.45, bold: true, color: C.tealText });
  text(s, `Límite de ${T("cfg.auto_apply_after")} y reserva del candidato.`, { x: x + 0.3, y: 4.2, w: w - 0.6, h: 0.85 });
  text(s, [{ text: T("sim.normal.vela_timeout.high_wait_p90_min"), options: { color: C.tealText } },
    { text: " vs. ", options: { color: C.ink, fontSize: 24, bold: false } },
    { text: T("sim.normal.human_dispatcher.high_wait_p90_min"), options: { color: C.deep } }],
  { x: x + 0.3, y: 5.1, w: w - 0.6, h: 0.7, fontFace: HEAD, fontSize: 36, bold: true });
  text(s, `minutos · ${T("test.normal.high_wait_p90_min.vela_timeout.p")}`, { x: x + 0.3, y: 5.85, w: w - 0.6, h: 0.5, color: C.muted });
  source(s, `SIRAG-D, simulation/results/summary.csv · ${T("sim.runs_main")} corridas · Friedman y Wilcoxon con corrección de Holm`);
}

// ======================================================================= 6. Enlaza Voz
{
  const s = slide("CONTENIDO");
  title(s, ["Enlaza Voz: ", ["dos niveles"], " de aviso"]);
  const levels = [
    ["octagon-alert", C.danger, C.dangerSoft, "Pantalla roja: se activó una regla",
      `${T("vozb.holdout.red")} avisos, ${T("vozb.holdout.red_false")} falsos`],
    ["triangle-alert", C.warn, C.warnSoft, "Aviso ámbar: solo el clasificador",
      `${T("vozb.holdout.amber")} avisos, ${T("vozb.holdout.amber_false")} falsos · los revisa coordinación`],
  ];
  levels.forEach(([ic, color, soft, head, body], i) => {
    const y = 1.5 + i * 2.6;
    card(s, M, y, 6.9, 2.35, soft, head);
    iconCircle(s, M + 0.3, y + 0.35, 1.0, ic, color, C.white);
    text(s, head, { x: M + 1.55, y: y + 0.3, w: 5.15, h: 0.95, bold: true, color: C.ink });
    text(s, body, { x: M + 1.55, y: y + 1.25, w: 5.15, h: 0.95, color: C.ink });
  });
  const x = 8.0, w = W - M - x;
  text(s, T("voz.holdout.sens"), { x, y: 1.4, w, h: 0.95, fontFace: HEAD, fontSize: 54, bold: true, color: C.tealText });
  text(s, "de las emergencias detectadas", { x, y: 2.35, w, h: 0.5 });
  text(s, `solo con reglas: ${T("voz.holdout.sens_rules")}`, { x, y: 2.9, w, h: 0.5, color: C.muted });
  text(s, T("voz.holdout.fa100"), { x, y: 3.95, w, h: 0.95, fontFace: HEAD, fontSize: 54, bold: true, color: C.danger });
  text(s, "falsas alarmas por cada 100 notas", { x, y: 4.9, w, h: 0.9 });
  text(s, "El sistema nunca diagnostica.", { x, y: 5.9, w, h: 0.5, bold: true, color: C.deep });
  source(s, `evaluación a ciegas (holdout) con ${T("voz.holdout.n")} frases que el modelo no vio · voice/eval/results/`);
}

// ======================================================================= 7. Seguridad, privacidad y ética
{
  const s = slide("CONTENIDO");
  title(s, ["Seguridad y ética desde la ", ["base de datos"]]);
  card(s, M, 1.45, 5.4, 5.2, C.sky, "Seguridad por fila");
  iconCircle(s, M + 0.3, 1.7, 0.85, "database");
  text(s, "Pacientes que ve la API", { x: M + 1.35, y: 1.7, w: 3.9, h: 0.85, bold: true, valign: "middle" });
  [["db.rls_patients_none", "sin institución"], ["db.rls_patients_insa", "Clínica Oriente"], ["db.rls_patients_all", "Dirección"]]
    .forEach(([k, label], i) => {
      const y = 2.85 + i * 1.2;
      text(s, T(k), { x: M + 0.3, y, w: 1.8, h: 0.9, fontFace: HEAD, fontSize: 48, bold: true, color: i === 0 ? C.tealText : C.deep,
        valign: "middle" });
      text(s, label, { x: M + 2.2, y, w: 3.0, h: 0.9, valign: "middle" });
    });
  const rows = [["file-check", "Consentimiento por tipo de uso y asentimiento de la persona"],
    ["scale", "LFPDPPP: aviso de privacidad, derechos ARCO y bitácora"],
    ["calendar-clock", "Ley Federal del Trabajo: descanso, jornada y relevos"],
    ["user-check", "La IA avisa, no diagnostica; una persona decide lo delicado"]];
  rows.forEach(([ic, t], i) => {
    const y = 1.45 + i * 1.32;
    iconCircle(s, 6.4, y + 0.1, 0.9, ic);
    text(s, t, { x: 7.5, y, w: W - M - 7.5, h: 1.1, valign: "middle" });
  });
  source(s, `consulta en vivo a PostgreSQL como vela_api (seguridad por fila) · ${T("repo.tests_summary")} del backend`);
}

// ======================================================================= 8. Negocio y mercado
{
  const s = slide("CONTENIDO", "Negocio");
  title(s, ["Un mercado real, contado en el ", ["DENUE"]]);
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
  text(s, T("bm.arpa1"), { x, y: 1.45, w, h: 0.85, fontFace: HEAD, fontSize: 44, bold: true, color: C.deep });
  text(s, "al mes por institución (promedio del año 1)", { x, y: 2.3, w, h: 0.9 });
  text(s, T("bm.ltv_cac"), { x, y: 3.35, w, h: 0.85, fontFace: HEAD, fontSize: 44, bold: true, color: C.tealText });
  text(s, "lo que vale un cliente contra lo que cuesta conseguirlo", { x, y: 4.2, w, h: 0.9 });
  text(s, "Suscripción por tamaño; los públicos compran por licitación (plan aparte).", { x, y: 5.3, w, h: 1.3, color: C.muted });
  source(s, "INEGI, DENUE, sector 62 (mayo 2026) · data/business/assumptions.csv (lo mismo que /negocio)");
}

// ======================================================================= 9. Pitch
{
  const s = slide("CONTENIDO");
  title(s, ["Por qué invertir ", ["ahora"]]);
  const tiles = [[T("bm.sc.recommended.investment"), "inversión necesaria"],
    [T("bm.sc.recommended.npv25"), `VPN al ${T("bm.rate_25")}, 5 años`],
    [T("bm.sc.recommended.tir"), "TIR anual"],
    [`mes ${T("bm.sc.recommended.breakeven")}`, "deja de perder dinero"]];
  const tw = (W - 2 * M - 3 * 0.25) / 4;
  tiles.forEach(([big, label], i) => {
    const x = M + i * (tw + 0.25);
    card(s, x, 1.45, tw, 1.95, i === 0 ? C.deep : C.sky, `Cifra ${label}`);
    text(s, big, { x: x + 0.2, y: 1.6, w: tw - 0.4, h: 0.8, fontFace: HEAD, fontSize: 32, bold: true,
      color: i === 0 ? C.white : C.deep });
    text(s, label, { x: x + 0.2, y: 2.45, w: tw - 0.4, h: 0.85, color: i === 0 ? C.white : C.ink });
  });
  text(s, "% de la CDMX con 60 años o más", { x: M, y: 3.7, w: 6.6, h: 0.5, bold: true });
  s.addChart(pres.charts.BAR, [{ name: "60 años o más (%)", labels: ["2022", "2030"],
    values: [PCT("ctx.cdmx_prop_60mas_2022"), PCT("ctx.cdmx_prop_60mas_2030")] }], {
    x: M, y: 4.25, w: 6.6, h: 2.5, barDir: "bar", catAxisOrientation: "maxMin", barGapWidthPct: 35,
    chartColors: [C.navy, C.tealText], catAxisLabelFontFace: HEAD, catAxisLabelFontSize: 24, catAxisLabelColor: C.ink,
    catAxisLineShow: false, valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 30, valGridLine: { style: "none" },
    catGridLine: { style: "none" }, showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.ink, dataLabelFontFace: HEAD,
    dataLabelFontSize: 24, dataLabelFontBold: true, dataLabelFormatCode: "0.0", showLegend: false, showTitle: false,
  });
  const x = 7.6, w = W - M - x;
  card(s, x, 3.7, w, 3.0, C.skySoft, "Honestidad");
  text(s, `Plan base: VPN ${T("bm.sc.base.npv25")}.`, { x: x + 0.3, y: 3.9, w: w - 0.6, h: 0.5, bold: true });
  text(s, `Por eso recomendamos un tope de ${T("neg.recommended_private_cap")} % por entidad y crecer por regiones.`,
    { x: x + 0.3, y: 4.4, w: w - 0.6, h: 1.3 });
  text(s, `${T("ctx.mexico_60mas_2024")} de personas mayores en México.`, { x: x + 0.3, y: 5.75, w: w - 0.6, h: 0.85, color: C.tealText, bold: true });
  source(s, "escenario recomendado del modelo de negocio (/negocio) · CONAPO, ficha CDMX (2022) · INEGI, ENASEM 2024");
}

// ======================================================================= 10. Cierre
{
  const s = slide("OSCURO", "Cierre");
  text(s, "Lo que logramos y lo que sigue", { x: M, y: 0.5, w: W - 2 * M, h: 0.9, fontFace: HEAD, fontSize: 36, bold: true, color: C.white });
  const cols = [["circle-check", "Logramos", ["Seis materias en una app en vivo", "La simulación mejoró el producto", T("repo.tests_summary")]],
    ["triangle-alert", "Límites honestos", ["Datos sintéticos", `${T("voz.holdout.fa100")} falsas alarmas por 100 notas de voz`, "Falta una institución real"]],
    ["arrow-right", "Siguientes pasos", ["Piloto con una residencia", "Voz con hablantes reales", "Diagnóstico de campo"]]];
  const cw = (W - 2 * M - 2 * 0.3) / 3;
  cols.forEach(([ic, head, items], i) => {
    const x = M + i * (cw + 0.3);
    card(s, x, 1.55, cw, 4.45, C.navy, head);
    iconCircle(s, x + 0.3, 1.85, 0.8, ic, C.deep, "BFE7E7");
    text(s, head, { x: x + 1.25, y: 1.85, w: cw - 1.45, h: 0.8, bold: true, color: C.white, valign: "middle" });
    s.addText(items.map((t, j) => ({ text: t, options: { bullet: { indent: 18 }, breakLine: j < items.length - 1 } })),
      { isTextBox: true, x: x + 0.3, y: 2.8, w: cw - 0.5, h: 3.05, fontFace: BODY, fontSize: 24, color: C.white, margin: 0,
        valign: "top", paraSpaceAfter: 8 });
  });
  text(s, "Gracias · enlaza.zenthinks.com", { x: M, y: 6.25, w: 10, h: 0.7, fontFace: HEAD, fontSize: 28, bold: true, color: C.white,
    valign: "middle" });
}

// ======================================================================= 11. Respaldo (no se presenta)
{
  const s = slide("CONTENIDO", "Respaldo (no se presenta)");
  title(s, ["Respaldo: la demostración en ", ["capturas"]]);
  const shots = [["solicitud_familia_enviada", "1 · Se asigna sola"], ["urgente_aprobaciones", "2 · Aprobación humana"],
    ["contingencia_propuesta", "3 · Contingencia"], ["voz_emergencia_911", "4 · Pantalla roja"]];
  const iw = 4.75, ih = (iw * 810) / 1440, gx = 0.35, gy = 0.25, x0 = (W - 2 * iw - gx) / 2;
  shots.forEach(([file, cap], i) => {
    const x = x0 + (i % 2) * (iw + gx), y = 1.45 + Math.floor(i / 2) * (ih + gy);
    const f = path.join(SHOTS, `${file}.png`);
    if (!fs.existsSync(f)) throw new Error(`Falta la captura ${f}: correr scripts/build_presentacion.sh --capturas`);
    s.addImage({ path: f, x, y, w: iw, h: ih, sizing: { type: "cover", w: iw, h: ih }, altText: cap });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: iw, h: ih, fill: { type: "none" }, line: { color: C.line, width: 1 }, objectName: "Marco" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.12, y: y + ih - 0.62, w: 3.75, h: 0.5, rectRadius: 0.1,
      fill: { color: C.deep, transparency: 8 }, line: { color: C.deep }, objectName: "Pie" });
    text(s, cap, { x: x + 0.25, y: y + ih - 0.62, w: 3.55, h: 0.5, color: C.white, valign: "middle", fontSize: 24 });
  });
}

// ---- write
(async () => {
  const file = path.join(PRES, "enlaza_coloquio.pptx");
  await pres.writeFile({ fileName: file });
  fs.writeFileSync(path.join(OUT, "errbars.json"), JSON.stringify(ERRBARS));
  const rows = [["clave", "texto", "fuente", "uso"], ...[...USED].map(([k, d]) => [k, LABEL.get(k) ?? d.text, d.source, DRAWN.has(k) ? "gráfica" : LABEL.has(k) ? "etiqueta de gráfica" : "texto"])];
  fs.writeFileSync(path.join(OUT, "numeros_usados.csv"), rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n"));
  console.log(`Presentación: ${file} (${slideNo} diapositivas, ${USED.size} números)`);
})();
