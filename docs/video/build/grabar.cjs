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
  await target.hover().catch(() => {});        // the pointer moves there first: easier to follow on video
  await target.page().waitForTimeout(350);
  await target.click();
}

// ---- sessions -----------------------------------------------------------------------------------------------
async function login(page, user, { slow = false } = {}) {
  await page.goto(`${BASE}/entrar`);
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
    await form.locator("select").first().selectOption({ label: "11:00" });
    await fam.page.waitForTimeout(1200);
    await click(form.getByRole("button", { name: "Solicitar servicio" }));
    await fam.page.waitForTimeout(2500);
    await fam.page.getByText(/Asignada/i).first().scrollIntoViewIfNeeded().catch(() => {});
    await board.page.waitForTimeout(9000);   // the board updates by itself (WebSocket): no reload on camera
    await fam.close(); await board.close();
  },

  async "D.3"() {
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

module.exports = { click, BLOCK_TEL };   // for test_guardia.cjs

if (require.main === module) (async () => {
  browser = await chromium.launch({ headless: false });
  const scenes = { 2: VIDEO2 }[VIDEO];
  if (!scenes) throw new Error(`VIDEO=${VIDEO}: todavía no hay escenas para ese video`);
  for (const [id, run] of Object.entries(scenes)) if (want(id)) await run();
  await browser.close();
})().catch(async (e) => { console.error(e.message || e); await browser?.close(); process.exit(1); });
