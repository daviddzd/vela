// Screen recordings of the real app for the explainer videos (Playwright, 1920x1080, one WebM per scene).
// Run by scripts/build_video.sh inside the vela-video image on the Compose network, with a real window (xvfb):
//   docker run ... --network vela_default vela-video xvfb-run -a node docs/video/build/grabar.cjs
// build_video.sh runs scripts/reset_demo.py BEFORE and AFTER (the scenes create requests, approvals and a voice note).
//
//   VIDEO=2           which video (2 = the colloquium demo, plan B)
//   ONLY=D.1,D.6      only these scenes (the others are skipped)
//   OUT=...           must be inside docs/privado/video/ (git-ignored); the script refuses anything else
//
// Safety rules (team decision, 26 Nov 2026):
//   - NEVER click "Llamar al 911", "800 911 2000" or any tel: link. click() checks the target first and stops the
//     whole recording if it is (or is inside) a tel: link or its text mentions 911; an init script also cancels any
//     tel: navigation in every page, as a second barrier.
//   - The password is typed only into an input of type "password" (shown as dots) and never appears in the narration.
//   - The voice is typed ("Escribir el mensaje"); the microphone is never used.
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE = process.env.BASE || "http://proxy:8080";
const VIDEO = process.env.VIDEO || "2";
const ONLY = (process.env.ONLY || "").split(",").filter(Boolean);
const PRIVATE = path.resolve(__dirname, "..", "..", "privado", "video");
const OUT = path.resolve(process.env.OUT || path.join(PRIVATE, "clips", `video${VIDEO}`));
if (!OUT.startsWith(PRIVATE + path.sep)) throw new Error(`OUT debe estar dentro de ${PRIVATE} (Git lo ignora): ${OUT}`);
fs.mkdirSync(OUT, { recursive: true });

const FULL = { width: 1920, height: 1080 };
const HALF = { width: 960, height: 1080 };
const PASSWORD = "Demo2026!";   // public on purpose, only for the synthetic demo users (CLAUDE.md rule 9)
const tomorrow = () => { const d = new Date(Date.now() + 24 * 3600 * 1000);
  return d.toLocaleDateString("es-MX", { timeZone: "America/Mexico_City" }); };

let browser;
const want = (id) => !ONLY.length || ONLY.includes(id);
const states = {};   // user -> storageState (logged in once, off camera)

// ---- safety -------------------------------------------------------------------------------------------------
const BLOCK_TEL = () => {
  document.addEventListener("click", (e) => {
    const a = e.target && e.target.closest && e.target.closest("a[href^='tel:']");
    if (a) { e.preventDefault(); e.stopImmediatePropagation(); console.error("BLOQUEADO: clic en " + a.href); }
  }, true);
};

async function click(locator) {
  // Refuse a click on a tel: link (911, 800 911 2000, the institution's line) or on anything that says 911.
  const target = locator.first();
  await target.waitFor({ state: "visible", timeout: 20000 });
  const info = await target.evaluate((el) => {
    const a = el.closest("a");
    return { href: a ? a.getAttribute("href") || "" : "", text: (el.innerText || el.textContent || "").trim() };
  });
  if (/^tel:/i.test(info.href) || /911/.test(info.text)) {
    throw new Error(`GUARDIA: se intentó hacer clic en un enlace de llamada («${info.text}» ${info.href}). Grabación detenida.`);
  }
  if (/Mostrar contraseña|Usuarios de prueba/i.test(info.text)) {   // the password never shows on video
    throw new Error(`GUARDIA: se intentó hacer clic en «${info.text}». Grabación detenida.`);
  }
  await target.hover().catch(() => {});        // the pointer moves there first: easier to follow on video
  await target.page().waitForTimeout(350);
  await target.click();
}

// ---- sessions -----------------------------------------------------------------------------------------------
async function login(page, user, { slow = false, here = false } = {}) {
  if (!here) await page.goto(`${BASE}/entrar`);
  const pwd = page.locator('input[autocomplete="current-password"]');
  if ((await pwd.getAttribute("type")) !== "password") throw new Error("GUARDIA: la contraseña no se mostraría como puntos");
  const email = page.locator('input[type="email"]');
  if (slow) { await email.pressSequentially(`${user}@ejemplo.test`, { delay: 60 }); await pwd.pressSequentially(PASSWORD, { delay: 60 }); }
  else { await email.fill(`${user}@ejemplo.test`); await pwd.fill(PASSWORD); }
  await click(page.locator('button[type="submit"]'));
  await page.waitForURL((u) => !u.pathname.endsWith("/entrar"), { timeout: 20000 });
  await page.waitForSelector("header", { timeout: 20000 });
}

async function stateOf(user) {
  if (!states[user]) {
    const ctx = await browser.newContext({ viewport: FULL, locale: "es-MX", timezoneId: "America/Mexico_City" });
    const page = await ctx.newPage();
    await login(page, user);
    states[user] = await ctx.storageState();
    await ctx.close();
  }
  return states[user];
}

// A recorded browser window. mark() notes "the scene starts here" (seconds since the recording began), so the
// montage can cut the blank loading at the beginning.
async function recorded(id, user, { viewport = FULL, part = "" } = {}) {
  const dir = path.join(OUT, `${id}${part}`);
  fs.rmSync(dir, { recursive: true, force: true });
  const ctx = await browser.newContext({ viewport, locale: "es-MX", timezoneId: "America/Mexico_City",
    storageState: user ? await stateOf(user) : undefined, recordVideo: { dir, size: viewport } });
  await ctx.addInitScript(BLOCK_TEL);
  const page = await ctx.newPage();
  const t0 = Date.now();
  const marks = {};
  return {
    page,
    mark: (name = "start") => { marks[name] = (Date.now() - t0) / 1000; },
    async close() {
      const video = page.video();
      await ctx.close();
      fs.renameSync(await video.path(), path.join(OUT, `${id}${part}.webm`));
      fs.rmSync(dir, { recursive: true, force: true });
      fs.writeFileSync(path.join(OUT, `${id}${part}.json`), JSON.stringify(marks));
      console.log("grabada", `${id}${part}`, JSON.stringify(marks));
    },
  };
}

async function settle(page, ms = 1500) {
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(ms);
}

async function scroll(page, px, steps = 6, pause = 450) {   // a slow scroll, readable on video
  for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, px / steps); await page.waitForTimeout(pause); }
}

// ---- off-camera helpers (API, logged in as the right user) --------------------------------------------------
async function api(user, route, body) {
  const ctx = await browser.newContext({ storageState: await stateOf(user) });
  const r = body === undefined ? await ctx.request.get(`${BASE}${route}`) : await ctx.request.post(`${BASE}${route}`, { data: body });
  const out = r.ok() ? await r.json().catch(() => ({})) : { error: r.status() };
  await ctx.close();
  return out;
}

// Today's date (dd/mm/aaaa, Mexico City) and the first time in the form's list that is at least 2 h from now.
function todayInTwoHours(options) {
  const now = new Date();
  const fmt = (d, o) => d.toLocaleString("es-MX", { timeZone: "America/Mexico_City", ...o });
  const date = fmt(now, { day: "2-digit", month: "2-digit", year: "numeric" });
  const later = fmt(new Date(now.getTime() + 2 * 3600 * 1000), { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  const sameDay = fmt(new Date(now.getTime() + 2 * 3600 * 1000), { day: "2-digit" }) === fmt(now, { day: "2-digit" });
  const time = sameDay && options.map((o) => o.trim()).filter((o) => /^\d\d:\d\d$/.test(o)).sort().find((o) => o >= later);
  if (!time) throw new Error("ALTO: ya no hay una hora de hoy dos horas después de ahora; grabar más temprano.");
  return { date, time };
}

// ---- Video 2 · the colloquium demo (plan B) -----------------------------------------------------------------
const VIDEO2 = {
  async "D.1"() {
    const w = await recorded("D.1", null);
    await w.page.goto(`${BASE}/`); await settle(w.page, 800); w.mark();
    await w.page.waitForTimeout(4000); await scroll(w.page, 900, 8, 600); await w.page.waitForTimeout(3000);
    await w.close();
  },

  async "D.2"() {
    // side by side: the family's phone-sized window (left) and coordination's live board (right), recorded together
    const fam = await recorded("D.2", "fam-0002", { viewport: HALF, part: "_izq" });
    const board = await recorded("D.2", "coordinacion.a", { viewport: HALF, part: "_der" });
    await board.page.goto(`${BASE}/tablero`); await fam.page.goto(`${BASE}/familia`);
    await settle(board.page, 2500); await settle(fam.page, 1000);
    fam.mark(); board.mark();
    await fam.page.waitForTimeout(2500);
    const form = fam.page.locator("form").filter({ has: fam.page.getByRole("button", { name: "Solicitar servicio" }) });
    await form.scrollIntoViewIfNeeded(); await fam.page.waitForTimeout(1200);
    await click(form.locator("label").filter({ hasText: /Enfermería/i }));
    await fam.page.waitForTimeout(800);
    // "para hoy, en un par de horas": today's date and the first time on the list at least 2 h from now
    const { date, time } = todayInTwoHours(await form.locator("select").first().locator("option").allTextContents());
    await form.getByPlaceholder("dd/mm/aaaa").first().fill(date);
    await form.locator("select").first().selectOption({ label: time });
    await fam.page.waitForTimeout(1200);
    await click(form.getByRole("button", { name: "Solicitar servicio" }));
    await fam.page.waitForTimeout(2500);
    await fam.page.getByText(/Asignada/i).first().scrollIntoViewIfNeeded().catch(() => {});
    // check with the API that the visit IS first on coordination's board and marked new; otherwise stop
    const who = (await fam.page.locator("h1").first().innerText()).replace(/^.*?:\s*/, "").trim();
    const up = (await api("coordinacion.a", "/api/board")).upcoming || [];
    if (!up.length || !up[0].is_new || up[0].patient_name !== who) {
      throw new Error(`ALTO: la visita de ${who} no aparece primero ni marcada «Nueva» en el tablero (API). No se sigue grabando.`);
    }
    console.log(`API: ${who} ${up[0].scheduled_for} está primero en el tablero, marcada «Nueva»`);
    // the board updates by itself (WebSocket, no reload on camera): the new row is first, marked «Nueva»
    await board.page.getByText("Nueva", { exact: true }).first().waitFor({ timeout: 15000 });
    await board.page.getByText("Nueva", { exact: true }).first()
      .evaluate((el) => el.closest("li").scrollIntoView({ behavior: "smooth", block: "center" }));
    await board.page.waitForTimeout(8000);
    await fam.close(); await board.close();
  },

  async "D.3"() {
    // the urgent visit (in 30 min) needs someone of the Clínica Oriente on shift now; otherwise stop
    const inst = ((await api("owner", "/api/demo/state")).institutions || []).find((i) => i.institution_id === "INS-A");
    if (!inst || inst.on_shift < 1) throw new Error("ALTO: la Clínica Oriente (INS-A) no tiene personal en turno ahora.");
    const own = await recorded("D.3", "owner", { part: "_a" });
    await own.page.goto(`${BASE}/demo`); await settle(own.page); own.mark();
    await own.page.waitForTimeout(2000);
    await click(own.page.getByRole("button", { name: "Contingencia en el oriente" }));
    await own.page.waitForTimeout(2500);
    await click(own.page.locator('input[name="institution"][value="INS-A"]').locator("xpath=ancestor::label[1]"));
    await own.page.waitForTimeout(1200);
    await click(own.page.getByRole("button", { name: "Crear solicitud urgente" }));
    await own.page.waitForTimeout(3500);
    await own.close();

    const coord = await recorded("D.3", "coordinacion.a", { part: "_b" });
    await coord.page.goto(`${BASE}/aprobaciones`); await settle(coord.page, 2000); coord.mark();
    await coord.page.waitForTimeout(4000);
    await click(coord.page.getByRole("button", { name: /^Aprobar/ }));
    await coord.page.waitForTimeout(2500);
    await coord.page.goto(`${BASE}/tablero`); await settle(coord.page, 2000);
    await coord.page.waitForTimeout(6000);
    await coord.close();
  },

  async "D.4"() {
    // off camera: wait until the worker has detected the contingency and proposed (it runs once a minute)
    for (let i = 0; i < 36; i++) {
      const c = await api("coordinacion.a", "/api/contingency/current");
      if ((c.events || []).some((e) => !e.ended_at && (e.proposals || []).length)) break;
      await new Promise((r) => setTimeout(r, 5000));
    }
    const coord = await recorded("D.4", "coordinacion.a", { part: "_a" });
    await coord.page.goto(`${BASE}/contingencia`); await settle(coord.page, 2500); coord.mark();
    await coord.page.waitForTimeout(3000); await scroll(coord.page, 700, 6, 700); await coord.page.waitForTimeout(1500);
    await click(coord.page.getByRole("button", { name: "Aprobar todo" }));
    await coord.page.waitForTimeout(3000);
    await coord.page.goto(`${BASE}/tablero`); await settle(coord.page, 2000);
    await coord.page.waitForTimeout(6000);
    await coord.close();

    const own = await recorded("D.4", "owner", { part: "_b" });
    await own.page.goto(`${BASE}/demo`); await settle(own.page); own.mark();
    await own.page.waitForTimeout(1500);
    await click(own.page.getByRole("button", { name: "Volver a normal" }));
    await own.page.waitForTimeout(3000);
    await own.close();
  },

  async "D.5"() {
    const fam = await recorded("D.5", "fam-0001");
    await fam.page.goto(`${BASE}/voz`); await settle(fam.page, 1200); fam.mark();
    await fam.page.waitForTimeout(2000);
    await click(fam.page.getByRole("button", { name: "Escribir el mensaje" }));
    await fam.page.getByLabel("Escribe lo que pasa").pressSequentially(
      "Mi mamá no puede respirar y tiene los labios morados.", { delay: 45 });
    await fam.page.waitForTimeout(1000);
    await click(fam.page.getByRole("button", { name: "Enviar mensaje" }));
    await fam.page.waitForTimeout(12000);    // the red screen stays: nobody touches "Llamar al 911"
    await fam.close();
  },

  async "D.6"() {
    const own = await recorded("D.6", "owner");
    await own.page.goto(`${BASE}/simulacion`); await settle(own.page, 3000); own.mark();
    await own.page.waitForTimeout(3000); await scroll(own.page, 800, 6, 700); await own.page.waitForTimeout(2000);
    await own.page.goto(`${BASE}/negocio`); await settle(own.page, 3000);
    await own.page.waitForTimeout(3000); await scroll(own.page, 800, 6, 700); await own.page.waitForTimeout(3000);
    await own.close();
  },
};

// The family asks for nursing "para hoy, en un par de horas" on its own page (video 1 and video 2 do the same).
async function familyAsksToday(page) {
  const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Solicitar servicio" }) });
  await form.scrollIntoViewIfNeeded(); await page.waitForTimeout(1500);
  await click(form.locator("label").filter({ hasText: /Enfermería/i }));
  await page.waitForTimeout(800);
  const { date, time } = todayInTwoHours(await form.locator("select").first().locator("option").allTextContents());
  await form.getByPlaceholder("dd/mm/aaaa").first().fill(date);
  await form.locator("select").first().selectOption({ label: time });
  await page.waitForTimeout(1500);
  await click(form.getByRole("button", { name: "Solicitar servicio" }));
  await page.waitForTimeout(3500);
}

// ---- Video 1 · Enlaza explained (the recorded scenes; the others are slides) --------------------------------
const VIDEO1 = {
  async "2.1"() {   // public page, then a family signs in on camera (the password shows as dots)
    const w = await recorded("2.1", null);
    await w.page.goto(`${BASE}/`); await settle(w.page, 800); w.mark();
    await w.page.waitForTimeout(3000); await scroll(w.page, 1200, 8, 600); await w.page.waitForTimeout(1500);
    await click(w.page.getByRole("link", { name: "Entrar" }).first());
    await settle(w.page, 1200);
    await w.page.getByLabel("Modo sencillo", { exact: false }).hover().catch(() => {});
    await w.page.waitForTimeout(1500);
    await login(w.page, "fam-0002", { slow: true, here: true });
    await settle(w.page, 2500);
    await w.close();
  },
  async "2.2"() {
    const w = await recorded("2.2", "fam-0002");
    await w.page.goto(`${BASE}/familia`); await settle(w.page); w.mark();
    await w.page.waitForTimeout(4000); await scroll(w.page, 500, 5, 600);
    await familyAsksToday(w.page);
    await w.page.getByText(/Asignada/i).last().scrollIntoViewIfNeeded().catch(() => {});
    await w.page.waitForTimeout(6000);
    await w.close();
  },
  async "2.3"() {
    const w = await recorded("2.3", "fam-0001");
    await w.page.goto(`${BASE}/familia`); await settle(w.page); w.mark();
    await familyAsksToday(w.page);
    await w.page.getByText(/En espera/i).last().scrollIntoViewIfNeeded().catch(() => {});
    await w.page.waitForTimeout(6000);
    await w.close();
  },
  async "2.4"() {
    const w = await recorded("2.4", "coordinacion.a");
    await w.page.goto(`${BASE}/tablero`); await settle(w.page, 3000); w.mark();
    await w.page.waitForTimeout(6000); await scroll(w.page, 700, 7, 900); await w.page.waitForTimeout(4000);
    await scroll(w.page, 700, 7, 900); await w.page.waitForTimeout(5000);
    await scroll(w.page, -1400, 4, 300); await w.page.waitForTimeout(3000);
    await w.close();
  },
  async "2.5"() {
    const w = await recorded("2.5", "coordinacion.a");
    await w.page.goto(`${BASE}/aprobaciones`); await settle(w.page, 2000); w.mark();
    await w.page.waitForTimeout(7000);
    await click(w.page.getByRole("button", { name: /^Aprobar/ }));
    await w.page.waitForTimeout(3000);
    await w.page.goto(`${BASE}/tablero`); await settle(w.page, 2000); await w.page.waitForTimeout(6000);
    await w.close();
  },
  async "2.6"() {
    const w = await recorded("2.6", "coordinacion.a");
    await w.page.goto(`${BASE}/pacientes`); await settle(w.page, 2000); w.mark();
    await w.page.waitForTimeout(4000); await scroll(w.page, 600, 5, 700);
    await w.page.goto(`${BASE}/pacientes/PAC-0001`); await settle(w.page, 2000);
    await w.page.waitForTimeout(3000); await scroll(w.page, 900, 7, 700);
    await w.page.goto(`${BASE}/personal`); await settle(w.page, 3000);
    await w.page.waitForTimeout(4000); await scroll(w.page, 800, 6, 800); await w.page.waitForTimeout(3000);
    await w.close();
  },
  async "2.7"() {   // the caregiver needs a visit whose "Llegué" is open now (it opens 60 min before); otherwise stop
    const mine = await api("cui-003", "/api/visits/mine");
    const list = Array.isArray(mine) ? mine : (mine.visits || []);
    const open = list.find((v) => v.step === "arrive" && (!v.arrive_from || new Date(v.arrive_from) <= new Date()));
    if (!open) throw new Error("ALTO: cui-003 no tiene ahora una visita con «Llegué» activo (se abre 60 min antes).");
    const w = await recorded("2.7", "cui-003", { viewport: { width: 430, height: 932 } });
    await w.page.goto(`${BASE}/mis-visitas`); await settle(w.page, 1500); w.mark();
    await w.page.waitForTimeout(5000);
    const card = w.page.locator("main li, main article, main section").filter({ hasText: open.patient_name }).first();
    await card.scrollIntoViewIfNeeded().catch(() => {});
    await w.page.waitForTimeout(2000);
    await click(card.getByRole("button", { name: "Llegué" }));
    await w.page.waitForTimeout(4000);
    await click(card.getByRole("button", { name: "Terminé" }));
    await w.page.waitForTimeout(1500);
    const sure = w.page.getByRole("button", { name: "Sí, ya terminé" });
    if (await sure.count()) { await w.page.waitForTimeout(2000); await click(sure); }
    await w.page.waitForTimeout(5000);
    await w.close();
  },
  async "2.8"() {
    const w = await recorded("2.8", "fam-0001");
    await w.page.goto(`${BASE}/voz`); await settle(w.page, 1200); w.mark();
    await w.page.waitForTimeout(3000);
    await click(w.page.getByRole("button", { name: "Escribir el mensaje" }));
    await w.page.getByLabel("Escribe lo que pasa").pressSequentially(
      "Mi mamá no puede respirar y tiene los labios morados.", { delay: 45 });
    await w.page.waitForTimeout(1000);
    await click(w.page.getByRole("button", { name: "Enviar mensaje" }));
    await w.page.waitForTimeout(12000);    // the red screen stays: nobody touches "Llamar al 911"
    await w.close();
  },
  async "2.9"() {   // off camera: wait until the local LLM has written the report (it takes some seconds)
    for (let i = 0; i < 36; i++) {
      const txt = JSON.stringify(await api("cui-001", "/api/voice/reports"));
      if (/morados/.test(txt) && !/"(pending|processing)"/.test(txt)) break;
      await new Promise((r) => setTimeout(r, 5000));
    }
    const w = await recorded("2.9", "cui-001");
    await w.page.goto(`${BASE}/reportes-voz`); await settle(w.page, 2000); w.mark();
    await w.page.waitForTimeout(5000); await scroll(w.page, 700, 6, 900); await w.page.waitForTimeout(5000);
    await w.close();
  },
  async "2.10"() {
    const w = await recorded("2.10", "owner");
    await w.page.goto(`${BASE}/panorama`); await settle(w.page, 3500); w.mark();
    await w.page.waitForTimeout(4000); await scroll(w.page, 900, 7, 800);
    await w.page.goto(`${BASE}/panorama?vista=panorama`); await settle(w.page, 3500);
    await w.page.waitForTimeout(4000); await scroll(w.page, 900, 7, 800); await w.page.waitForTimeout(3000);
    await w.close();
  },
  async "2.11"() {
    const w = await recorded("2.11", "owner");
    await w.page.goto(`${BASE}/simulacion`); await settle(w.page, 3000); w.mark();
    await w.page.waitForTimeout(4000); await scroll(w.page, 900, 7, 800); await w.page.waitForTimeout(3000);
    await w.close();
  },
  async "2.12"() {
    const own = await recorded("2.12", "owner", { part: "_a" });
    await own.page.goto(`${BASE}/demo`); await settle(own.page); own.mark();
    await own.page.waitForTimeout(3000);
    await click(own.page.getByRole("button", { name: "Contingencia en el oriente" }));
    await own.page.waitForTimeout(3000);
    await own.close();
    for (let i = 0; i < 36; i++) {          // off camera: the worker detects it within a minute and proposes
      const c = await api("coordinacion.a", "/api/contingency/current");
      if ((c.events || []).some((e) => !e.ended_at && (e.proposals || []).length)) break;
      await new Promise((r) => setTimeout(r, 5000));
    }
    const coord = await recorded("2.12", "coordinacion.a", { part: "_b" });
    await coord.page.goto(`${BASE}/contingencia`); await settle(coord.page, 2500); coord.mark();
    await coord.page.waitForTimeout(3000); await scroll(coord.page, 700, 6, 700); await coord.page.waitForTimeout(1500);
    await click(coord.page.getByRole("button", { name: "Aprobar todo" }));
    await coord.page.waitForTimeout(3000);
    await coord.close();
    const back = await recorded("2.12", "owner", { part: "_c" });
    await back.page.goto(`${BASE}/demo`); await settle(back.page); back.mark();
    await back.page.waitForTimeout(1500);
    await click(back.page.getByRole("button", { name: "Volver a normal" }));
    await back.page.waitForTimeout(3000);
    await back.close();
  },
  async "2.13"() {
    const w = await recorded("2.13", "owner");
    await w.page.goto(`${BASE}/negocio`); await settle(w.page, 3000); w.mark();
    await w.page.waitForTimeout(4000); await scroll(w.page, 900, 7, 800);
    await w.page.goto(`${BASE}/privacidad`); await settle(w.page, 2000);
    await w.page.waitForTimeout(3000);
    await click(w.page.getByRole("button", { name: "Bitácora" }).first()
      .or(w.page.getByRole("tab", { name: "Bitácora" }).first()));
    await w.page.waitForTimeout(6000);
    await w.close();
  },
};

module.exports = { click, BLOCK_TEL };   // for test_guardia.cjs

if (require.main === module) (async () => {
  browser = await chromium.launch({ headless: false });
  const scenes = { 1: VIDEO1, 2: VIDEO2 }[VIDEO];
  if (!scenes) throw new Error(`VIDEO=${VIDEO}: todavía no hay escenas para ese video`);
  for (const [id, run] of Object.entries(scenes)) if (want(id)) await run();
  await browser.close();
})().catch(async (e) => { console.error(e.message || e); await browser?.close(); process.exit(1); });
