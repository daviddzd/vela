// Screenshots for the colloquium deck WITHOUT live demo (enlaza_coloquio_capturas.pptx). Real app, synthetic data.
// Run by scripts/build_presentacion_capturas.sh (reset_demo.py BEFORE and AFTER) inside the vela-presentacion image:
//   docker run ... --network vela_default vela-presentacion xvfb-run -a node docs/presentacion/build/capturas.cjs
//   ONLY=C09,C10 ...   only these captures
// Desktop 1920x1080, phone 390x844. Login through the API (POST /api/auth/login): the password is never typed on screen.
// Guard: guardia.cjs (never click 911 / tel: / "Mostrar contraseña" / "Usuarios de prueba"; the password never shows).
// Each capture writes <id>.png (what fits on screen), <id>_completa.png (whole page) and <id>.txt (visible text).
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");
const { BLOCK_TEL, PASSWORD, click, noPassword } = require("./guardia.cjs");

const BASE = process.env.BASE || "http://proxy:8080";
const OUT = path.resolve(process.env.CAPTURE_OUT || path.join(__dirname, "..", "capturas"));
const ONLY = (process.env.ONLY || "").split(",").filter(Boolean);
const DESK = { width: 1920, height: 1080 };
const PHONE = { width: 390, height: 844 };
const EMERGENCY = "Mi mamá no puede respirar y tiene los labios morados.";
const AMBER = "Hoy mi mamá comió bien y durmió su siesta.";   // routine text the classifier alone flags (amber)
fs.mkdirSync(OUT, { recursive: true });
const want = (id) => !ONLY.length || ONLY.includes(id);
let browser;

async function session(user, viewport = DESK) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: viewport.width < 500 ? 3 : 2, locale: "es-MX",
    timezoneId: "America/Mexico_City" });
  await ctx.addInitScript(BLOCK_TEL);
  if (user) {
    const r = await ctx.request.post(`${BASE}/api/auth/login`, { data: { email: `${user}@ejemplo.test`, password: PASSWORD } });
    if (!r.ok()) throw new Error(`login ${user}: ${r.status()}`);
  }
  return { ctx, page: await ctx.newPage() };
}

async function settle(page, ms = 2500) {
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(ms);
}

async function shot(page, name, { full = true, el = null } = {}) {
  await noPassword(page);
  const file = path.join(OUT, `${name}.png`);
  if (el) await el.screenshot({ path: file }); else await page.screenshot({ path: file, fullPage: false });
  if (full && !el) await page.screenshot({ path: path.join(OUT, `${name}_completa.png`), fullPage: true });
  fs.writeFileSync(file.replace(/\.png$/, ".txt"), await (el || page.locator("body")).innerText().catch(() => ""));
  console.log("captura", name);
}

// every card (main section) of a page as its own image: the deck crops and enlarges the important one
async function cards(page, prefix) {
  const list = page.locator("main section");
  const n = await list.count();
  let k = 0;
  for (let i = 0; i < n; i++) {
    const el = list.nth(i);
    if (((await el.boundingBox()) || { height: 0 }).height < 40) continue;
    await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(400);
    await shot(page, `${prefix}_tarjeta_${String(++k).padStart(2, "0")}`, { el });
  }
  await page.evaluate(() => window.scrollTo(0, 0));
}

async function writeNote(page, text) {
  await page.goto(`${BASE}/voz`); await settle(page, 1500);
  await click(page.getByRole("button", { name: "Escribir el mensaje" }));
  await page.getByLabel("Escribe lo que pasa").fill(text);
  await page.waitForTimeout(500);
}

async function api(user, route) {   // a GET through the API with that user's session (off camera)
  const { ctx } = await session(user);
  const r = await ctx.request.get(`${BASE}${route}`);
  const body = r.ok() ? await r.json() : null;
  await ctx.close();
  return body;
}

// "para hoy, en un par de horas": today's date and the first time on the list at least 2 h from now
function todayInTwoHours(options) {
  const now = new Date();
  const fmt = (d, o) => d.toLocaleString("es-MX", { timeZone: "America/Mexico_City", ...o });
  const date = fmt(now, { day: "2-digit", month: "2-digit", year: "numeric" });
  const later = fmt(new Date(now.getTime() + 2 * 3600 * 1000), { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  const sameDay = fmt(new Date(now.getTime() + 2 * 3600 * 1000), { day: "2-digit" }) === fmt(now, { day: "2-digit" });
  const time = sameDay && options.map((o) => o.trim()).filter((o) => /^\d\d:\d\d$/.test(o)).sort().find((o) => o >= later);
  if (!time) throw new Error("ALTO: ya no hay una hora de hoy dos horas después de ahora.");
  return { date, time };
}

async function centerOn(locator) {
  await locator.first().evaluate((el) => (el.closest("li") || el).scrollIntoView({ block: "center" }));
  await locator.first().page().waitForTimeout(800);
}

const CAPTURES = {
  // ---- DAY captures (personal on shift in INS-A, 08:00 to 18:00) --------------------------------------------
  async C12() {   // staff: workday alerts (12 h night shifts are flagged, not corrected)
    const { ctx, page } = await session("coordinacion.a");
    await page.goto(`${BASE}/personal`); await settle(page, 5000);
    await shot(page, "C12_personal");
    await cards(page, "C12_personal");
    await ctx.close();
    // the 12 h night shifts are in INS-B and INS-D: coordination of INS-B sees the alert (flagged, not corrected)
    const b = await session("coordinacion.b");
    await b.page.goto(`${BASE}/personal`); await settle(b.page, 5000);
    const flagged = b.page.locator("li, button").filter({ hasText: "Excede la jornada legal" });
    await flagged.first().evaluate((e) => e.scrollIntoView({ block: "center" }));
    await click(flagged.first().getByText(/Cortés|Reyes/).first());
    await settle(b.page, 2500);
    await b.page.evaluate(() => window.scrollTo(0, 0)); await b.page.waitForTimeout(500);
    await shot(b.page, "C12_personal_jornada");
    await cards(b.page, "C12_personal_jornada");
    await b.ctx.close();
  },
  async C01() {   // C01 form, C02 confirmation, C03 board row «Nueva», C04 the assigned person's agenda
    const fam = await session("fam-0002", PHONE);
    await fam.page.goto(`${BASE}/familia`); await settle(fam.page, 1500);
    const form = fam.page.locator("form").filter({ has: fam.page.getByRole("button", { name: "Solicitar servicio" }) });
    await click(form.locator("label").filter({ hasText: /Enfermería/i }));
    const { date, time } = todayInTwoHours(await form.locator("select").first().locator("option").allTextContents());
    await form.getByPlaceholder("dd/mm/aaaa").first().fill(date);
    await form.locator("select").first().selectOption({ label: time });
    await fam.page.waitForTimeout(800);
    await form.evaluate((f) => f.scrollIntoView({ block: "center" })); await fam.page.waitForTimeout(500);
    await form.getByRole("button", { name: "Solicitar servicio" }).evaluate((e) => e.scrollIntoView({ block: "end" }));
    await fam.page.evaluate(() => window.scrollBy(0, 40)); await fam.page.waitForTimeout(500);
    await shot(fam.page, "C01_familia_solicitud", { full: false });   // service chosen, today's date, the hour, the button
    if (process.env.FORM_ONLY) { await fam.ctx.close(); console.log("C01: solo el formulario, no se envió"); return; }
    await click(form.getByRole("button", { name: "Solicitar servicio" }));
    await fam.page.waitForTimeout(3500);
    await fam.page.getByText(/Asignada/i).first().evaluate((e) => e.scrollIntoView({ block: "center" })).catch(() => {});
    await fam.page.waitForTimeout(800);
    await shot(fam.page, "C02_familia_asignada", { full: false });
    const who = (await fam.page.locator("h1").first().innerText()).replace(/^.*?:\s*/, "").trim();
    await fam.ctx.close();
    console.log(`solicitud: ${who}, hoy ${date} ${time}`);

    const board = await api("coordinacion.a", "/api/board");
    const up = (board && board.upcoming) || [];
    console.log("tablero (API, primeras 3):", JSON.stringify(up.slice(0, 3).map((v) => ({ p: v.patient_name, n: v.is_new, at: v.scheduled_for, cg: v.caregiver_name }))));
    // the worker also creates care-plan visits as their time comes near: they can be «Nueva» too. Ours must be among them.
    const mine = up.find((v) => v.patient_name === who && v.is_new);
    if (!mine || up.slice(0, up.findIndex((v) => !v.is_new) >>> 0).indexOf(mine) < 0) throw new Error(`ALTO: la visita de ${who} no está entre las «Nueva» del tablero.`);
    console.log("tablero (API):", JSON.stringify({ p: mine.patient_name, at: mine.scheduled_for, cg: mine.caregiver_name }));
    const coord = await session("coordinacion.a");
    await coord.page.goto(`${BASE}/tablero`); await settle(coord.page, 4000);
    const row = coord.page.locator("li").filter({ hasText: who }).filter({ hasText: "Nueva" });
    await row.first().waitFor({ timeout: 15000 });
    await centerOn(row);
    await shot(coord.page, "C03_tablero_nueva", { full: false });
    await shot(coord.page, "C03_tablero_nueva_fila", { el: row.first() });
    await coord.ctx.close();

    // C04: the agenda of whoever got the visit (cui-003 or cui-004 have accounts in INS-A)
    for (const u of ["cui-003", "cui-004"]) {
      const c = await session(u, PHONE);
      await c.page.goto(`${BASE}/mis-visitas`); await settle(c.page, 2500);
      if ((await c.page.locator("main").innerText()).includes(who)) {
        await centerOn(c.page.getByText(who));
        await shot(c.page, `C04_mis_visitas_${u}`, { full: false });
        console.log(`C04: la visita está en la agenda de ${u}`);
        await c.ctx.close(); return;
      }
      await c.ctx.close();
    }
    console.log(`C04 PENDIENTE: la visita no quedó con cui-003 ni cui-004 (asignada a ${up[0].caregiver_name || "?"})`);
  },
  async C05() {   // C05 urgent in Aprobaciones, C06 approved on the board
    const st = await api("owner", "/api/demo/state");
    const inst = ((st && st.institutions) || []).find((i) => i.institution_id === "INS-A");
    if (!inst || inst.on_shift < 1) throw new Error("ALTO: INS-A no tiene personal en turno ahora.");
    const own = await session("owner");
    await own.page.goto(`${BASE}/demo`); await settle(own.page, 1500);
    await click(own.page.locator('input[name="institution"][value="INS-A"]').locator("xpath=ancestor::label[1]"));
    await click(own.page.getByRole("button", { name: "Crear solicitud urgente" }));
    await own.page.waitForTimeout(3000);
    await own.ctx.close();
    // the urgent one is the request created by the demo panel (there can be other high-priority ones waiting)
    const pending = (await api("coordinacion.a", "/api/approvals")) || [];
    const urgent = pending.find((r) => r.origin === "demo_scenario");
    if (!urgent) throw new Error("ALTO: no aparece la solicitud urgente del panel en Aprobaciones.");
    console.log(`urgente: ${urgent.request_id} ${urgent.scheduled_for} (${pending.length} en Aprobaciones)`);
    const coord = await session("coordinacion.a");
    await coord.page.goto(`${BASE}/aprobaciones`); await settle(coord.page, 2500);
    const card = coord.page.locator("main section").filter({ hasText: urgent.request_id });
    await card.first().evaluate((e) => e.scrollIntoView({ block: "center" })); await coord.page.waitForTimeout(500);
    await shot(coord.page, "C05_aprobaciones_urgente");
    await shot(coord.page, "C05_aprobaciones_urgente_tarjeta", { el: card.first() });
    await click(card.first().getByRole("button", { name: /^Aprobar/ }));   // the proposed person, well within the 3 min
    await coord.page.waitForTimeout(2500);
    await coord.page.goto(`${BASE}/tablero`); await settle(coord.page, 4000);
    const left = ((await api("coordinacion.a", "/api/approvals")) || []).some((r) => r.request_id === urgent.request_id);
    if (left) throw new Error("ALTO: la urgente sigue en Aprobaciones después de aprobarla.");
    await shot(coord.page, "C06_tablero_urgente_aprobada", { full: true });
    await coord.ctx.close();
  },
  async C07() {   // C07 stations, C08 the proposal per institution; then "Volver a normal"
    const own = await session("owner");
    await own.page.goto(`${BASE}/demo`); await settle(own.page, 1500);
    await click(own.page.getByRole("button", { name: "Contingencia en el oriente" }));
    await own.page.waitForTimeout(2000);
    try {
      let ok = false;
      for (let i = 0; i < 36 && !ok; i++) {
        const c = await api("coordinacion.a", "/api/contingency/current");
        ok = ((c && c.events) || []).some((e) => !e.ended_at && (e.proposals || []).length);
        if (!ok) await new Promise((r) => setTimeout(r, 5000));
      }
      if (!ok) throw new Error("ALTO: no llegó la propuesta de contingencia en 3 min.");
      const coord = await session("coordinacion.a");
      await coord.page.goto(`${BASE}/contingencia`); await settle(coord.page, 4000);
      await shot(coord.page, "C07_contingencia");
      await cards(coord.page, "C07_contingencia");
      const txt = await coord.page.locator("main").innerText();
      if (/oxigenoterapia: no hay visitas|no hay visitas de oxigenoterapia/i.test(txt)) console.log("AVISO C08: la propuesta dice «no hay visitas de oxigenoterapia»");
      else console.log("C08: la propuesta no dice «no hay visitas de oxigenoterapia»");
      await coord.ctx.close();
    } finally {
      await own.page.goto(`${BASE}/demo`); await settle(own.page, 1500);
      await click(own.page.getByRole("button", { name: "Volver a normal" }));
      await own.page.waitForTimeout(3000);
      console.log("demo: Volver a normal");
      await own.ctx.close();
    }
  },
  // C17 first: the amber notice (classifier only). Then C09/C10: the emergency, the newest report for the physician.
  async C17() {
    const { ctx, page } = await session("fam-0001", PHONE);
    await writeNote(page, AMBER);
    await click(page.getByRole("button", { name: "Enviar mensaje" }));
    await page.getByText("Tu mensaje podría indicar algo urgente").first().waitFor({ timeout: 30000 });
    await page.waitForTimeout(1500);
    // the notice is a scrollable overlay: top (title and danger signs), then bottom (coordination will call)
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await page.getByText("Tu mensaje podría indicar algo urgente").first()
      .evaluate((e) => e.scrollIntoView({ block: "start" }));
    await page.waitForTimeout(500);
    await shot(page, "C17_voz_ambar", { full: false });
    await page.getByText(/Coordinación te contactará/).first().evaluate((e) => e.scrollIntoView({ block: "end" }));
    await page.waitForTimeout(500);
    await shot(page, "C17_voz_ambar_abajo", { full: false });
    // on a 390x844 phone the title is cut (centered overlay taller than the screen): a taller window shows it whole
    await page.setViewportSize({ width: 390, height: 1240 });
    await page.waitForTimeout(800);
    await shot(page, "C17_voz_ambar_completo", { full: false });
    await ctx.close();
  },
  async C09() {
    const { ctx, page } = await session("fam-0001", PHONE);
    await writeNote(page, EMERGENCY);
    await shot(page, "C09_voz_escrita");
    if (want("C10")) {
      await click(page.getByRole("button", { name: "Enviar mensaje" }));
      await page.getByText("Llama al 911 ahora").first().waitFor({ timeout: 30000 });
      await page.waitForTimeout(1500);
      await shot(page, "C10_voz_roja");   // nobody touches "Llamar al 911"
    }
    await ctx.close();
  },
  async C11() {   // the physician (cui-001, INS-A) once the local LLM wrote the report
    const { ctx, page } = await session("cui-001");
    let txt = "";
    for (let i = 0; i < 60; i++) {
      await page.goto(`${BASE}/reportes-voz`); await settle(page, 2000);
      txt = await page.locator("main").innerText();
      if (txt.includes("labios morados") && !/preparando|generando|pendiente|escribiendo/i.test(txt)) break;
      await page.waitForTimeout(5000);
    }
    await shot(page, "C11_reportes_voz");
    await cards(page, "C11_reportes_voz");
    await ctx.close();
  },
  async C13() {
    const { ctx, page } = await session("owner");
    await page.goto(`${BASE}/simulacion`); await settle(page, 3000);
    await click(page.getByRole("button", { name: "Modo presentación" }));
    await settle(page, 3000);
    await shot(page, "C13_simulacion_presentacion");
    await cards(page, "C13_simulacion_presentacion");
    await ctx.close();
  },
  async C14() {
    const { ctx, page } = await session("owner");
    await page.goto(`${BASE}/panorama`); await settle(page, 5000);
    await shot(page, "C14_panorama");
    await cards(page, "C14_panorama");
    await ctx.close();
  },
  async C15() {
    const { ctx, page } = await session("owner");
    await page.goto(`${BASE}/negocio`); await settle(page, 4000);
    await shot(page, "C15_negocio");
    await cards(page, "C15_negocio");
    await ctx.close();
  },
  async C16() {   // the audit trail filtered to "Intento a otra institución" (INS-B asking for an INS-A patient: 403)
    // a fresh attempt through the API, so it is the first row: coordination of INS-B asks for PAC-0001 (INS-A)
    const b = await session("coordinacion.b");
    const r = await b.ctx.request.get(`${BASE}/api/patients/PAC-0001`);
    if (r.status() !== 403) throw new Error(`se esperaba 403 y respondió ${r.status()}`);
    console.log("intento ajeno: coordinacion.b -> PAC-0001 respondió 403");
    await b.ctx.close();
    const { ctx, page } = await session("owner");
    await page.goto(`${BASE}/privacidad`); await settle(page, 3000);
    const action = page.locator("main select").first();
    await action.selectOption("blocked_cross_tenant");
    await click(page.getByRole("button", { name: "Aplicar" }));
    await settle(page, 2500);
    await shot(page, "C16_privacidad_bitacora");
    await cards(page, "C16_privacidad_bitacora");
    await page.getByText(/\d+ registros/).first().evaluate((e) => e.scrollIntoView({ block: "start" }));
    await page.evaluate(() => window.scrollBy(0, -40));
    await page.waitForTimeout(800);
    await shot(page, "C16_privacidad_tabla", { full: false });
    await ctx.close();
  },
};

(async () => {
  browser = await chromium.launch({ headless: false });
  // DAY=1: the daytime batch (C02/C03/C04 inside C01, C06 inside C05, C08 inside C07)
  const order = process.env.DAY ? ["C12", "C01", "C05", "C07", "C14", "C17"] : ["C17", "C09", "C11", "C13", "C14", "C15", "C16"];
  for (const id of order) if (want(id) || (id === "C09" && want("C10"))) await CAPTURES[id]();
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
