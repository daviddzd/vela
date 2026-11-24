// Browser checks for the fixes of the Chrome-on-Windows review (23 Nov 2026). Exits 1 if any check fails.
// Runs inside the official Playwright image on the Compose network, with a real window (xvfb), like capture.mjs:
//   docker run --rm --init --ipc=host --network vela_default -v "$PWD/frontend/scripts:/scripts:ro" \
//     -e BASE=http://proxy:8080 mcr.microsoft.com/playwright:<version> \
//     sh -c "cd /tmp && npm i -s playwright@<version> && xvfb-run -a node /scripts/ui_checks.mjs"
// It creates no data: every form it tries is one that must be stopped before sending.
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:8080";
const browser = await chromium.launch({ headless: false });
const results = [];
const check = (name, ok, detail = "") => { results.push({ name, ok }); console.log(`${ok ? "OK   " : "FALLA"} ${name}${detail ? ` — ${detail}` : ""}`); };

async function session(user, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, locale: "es-MX", timezoneId: "America/Mexico_City", ...opts });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(`${BASE}/entrar`);
  await page.fill('input[type="email"]', `${user}@ejemplo.test`);
  await page.fill('input[autocomplete="current-password"]', "Demo2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.endsWith("/"), { timeout: 15000 });
  await page.waitForSelector("header", { timeout: 15000 });
  return { ctx, page, errors };
}
const posts = (page, part) => { const seen = []; page.on("request", (r) => { if (r.method() === "POST" && r.url().includes(part)) seen.push(r.url()); }); return seen; };
const chartHeights = (page) => page.evaluate(() => [...document.querySelectorAll("[_echarts_instance_]")].map((e) => Math.round(e.getBoundingClientRect().height)));

// 2. Charts do not grow by themselves (Windows at 125 %: 1920 px screen = 1536 CSS px)
{
  const { ctx, page } = await session("owner", { viewport: { width: 1536, height: 730 }, deviceScaleFactor: 1.25 });
  for (const path of ["/panorama?vista=panorama", "/simulacion"]) {
    await page.goto(`${BASE}${path}`); await page.waitForTimeout(2000);
    const before = await chartHeights(page); await page.waitForTimeout(10000); const after = await chartHeights(page);
    const grew = after.map((h, i) => h - (before[i] ?? h)).filter((d) => Math.abs(d) > 2);
    check(`gráficas de ${path} no crecen en 10 s`, before.length > 0 && grew.length === 0, `${JSON.stringify(before)} → ${JSON.stringify(after)}`);
  }
  await ctx.close();
}

// 3 + 11 + 12. Date field, Spanish validation, past dates (family form: nothing must be sent)
{
  const { ctx, page } = await session("fam-0001");
  await page.goto(`${BASE}/familia`); await page.waitForTimeout(1500);
  const sent = posts(page, "/api/requests");
  const date = page.getByPlaceholder("dd/mm/aaaa").first();   // the request form's date (label "Fecha")
  await date.click(); await page.keyboard.type("25/12/2026");
  check("escribir sobre una fecha la reemplaza", (await date.inputValue()) === "25/12/2026", await date.inputValue());
  await date.fill("31/02/2026"); await page.getByRole("button", { name: "Solicitar servicio" }).click(); await page.waitForTimeout(800);
  const body = await page.locator("main").innerText();
  check("fecha inválida: no se envía y avisa en español", sent.length === 0 && body.includes("Escribe la fecha como dd/mm/aaaa."));
  check("sin avisos en inglés", !/Please|fill out|match the requested/i.test(body));
  await date.fill("01/01/2026"); await page.getByRole("button", { name: "Solicitar servicio" }).click(); await page.waitForTimeout(800);
  check("fecha pasada: se frena antes de enviar", sent.length === 0 && (await page.locator("main").innerText()).includes("ya pasaron"));
  await ctx.close();
}

// 11. Required field with our own Spanish message (coordination board form, empty patient id)
{
  const { ctx, page } = await session("coordinacion.a");
  await page.goto(`${BASE}/tablero`); await page.waitForTimeout(1500);
  const sent = posts(page, "/api/requests");
  await page.getByRole("button", { name: "Solicitar servicio" }).click(); await page.waitForTimeout(600);
  const txt = await page.locator("main").innerText();
  check("campo obligatorio: «Completa este campo.» y no se envía", sent.length === 0 && txt.includes("Completa este campo."));
  await ctx.close();
}

// 6. Header never overflows (1280 and 1536 px, longest institution names)
for (const user of ["coordinacion.b", "coordinacion.c", "coordinacion.d", "coordinacion.e"]) {
  for (const width of [1280, 1536]) {
    const { ctx, page } = await session(user, { viewport: { width, height: 720 } });
    const r = await page.evaluate(() => {
      const out = [...document.querySelectorAll("header button")].find((b) => b.textContent.includes("Cerrar sesión"));
      return { doc: document.documentElement.scrollWidth, inner: innerWidth, right: out ? out.getBoundingClientRect().right : 0 };
    });
    check(`encabezado de ${user} en ${width} px sin desbordar`, r.right > 0 && r.doc <= r.inner && r.right <= r.inner, JSON.stringify(r));
    await ctx.close();
  }
}

// 8. Panorama: "Desde" after "Hasta" → notice, not applied
{
  const { ctx, page } = await session("coordinacion.a");
  await page.goto(`${BASE}/panorama`); await page.waitForTimeout(1500);
  const calls = []; page.on("request", (r) => { if (r.url().includes("/api/panorama/operation")) calls.push(r.url()); });
  await page.getByLabel("Desde").fill("20/11/2026"); await page.getByLabel("Hasta").fill("10/11/2026"); await page.waitForTimeout(1200);
  const txt = await page.locator("main").innerText();
  check("Panorama: fechas al revés avisan y no se aplican", txt.includes("«Desde» es posterior a «Hasta»") && !calls.some((u) => u.includes("from=2026-11-20") && u.includes("to=2026-11-10")));
  check("Panorama: dice a qué gráficas afectan las fechas", txt.includes("Las fechas (Desde / Hasta) cambian"));
  await ctx.close();
}

// 9. Business: the plan mix must add up to 100 %
{
  const { ctx, page } = await session("owner");
  await page.goto(`${BASE}/negocio`); await page.waitForTimeout(2000);
  const sent = posts(page, "/api/business/model");
  await page.getByLabel("Básico (%)").fill("50"); await page.waitForTimeout(1200);
  const txt = await page.locator("main").innerText();
  check("Negocio: mezcla ≠ 100 % avisa y no recalcula", sent.length === 0 && txt.includes("deben sumar 100 %"));
  await ctx.close();
}

// 7. Staff map: a click on a base selects that person
{
  const { ctx, page } = await session("coordinacion.a");
  await page.goto(`${BASE}/personal`); await page.waitForTimeout(6000);          // the street map needs its tiles
  const before = await page.locator("#agenda h2").first().innerText();
  const markers = page.locator(".maplibregl-marker");
  let changed = false;
  for (let i = 0; i < Math.min(await markers.count(), 6) && !changed; i++) {
    await markers.nth(i).click({ force: true }); await page.waitForTimeout(800);
    changed = (await page.locator("#agenda h2").first().innerText()) !== before;
  }
  check("Personal: clic en una base muestra la agenda de esa persona", changed);
  await ctx.close();
}

// 13. Texts: no jargon, no a.m./p.m., dates dd/mm/aaaa, map controls in Spanish (all screens of each role)
for (const user of ["owner", "coordinacion.a", "cui-001", "cui-003", "fam-0001"]) {
  const { ctx, page, errors } = await session(user);
  const me = await page.evaluate(() => fetch("/api/auth/me").then((r) => r.json()));
  const bad = [];
  for (const path of me.screens) {
    await page.goto(`${BASE}${path}`); await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {}); await page.waitForTimeout(1500);
    const txt = await page.locator("body").innerText();
    for (const [what, re] of [["jerga", /config\/simulation\.yaml|\bsemilla\b|\bworker\b|assumptions\.csv/i], ["a.m./p.m.", /\b[ap]\.\s?m\./i],
      ["fecha no dd/mm/aaaa", /\b\d{1,2} (de )?(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\b|\d{4}-\d{2}-\d{2}/i],
      ["controles del mapa en inglés", /Data from|Zoom in|Zoom out|Toggle attribution/]]) {
      const m = txt.match(re); if (m) bad.push(`${path}: ${what} («${m[0]}»)`);
    }
    const labels = await page.evaluate(() => [...document.querySelectorAll(".maplibregl-map [aria-label], .maplibregl-map [title]")]
      .map((e) => e.getAttribute("aria-label") ?? e.getAttribute("title")).filter((t) => /^(Zoom|Toggle|Map$|Reset|Drag)/.test(t ?? "")));
    if (labels.length) bad.push(`${path}: controles del mapa en inglés (${labels.join(", ")})`);
  }
  check(`textos de ${user} (${me.screens.length} pantallas)`, bad.length === 0, bad.slice(0, 4).join(" | "));
  check(`sin errores de página para ${user}`, errors.length === 0, errors.slice(0, 2).join(" | "));
  await ctx.close();
}

await browser.close();
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed} de ${results.length} verificaciones correctas`);
process.exit(failed ? 1 : 0);
