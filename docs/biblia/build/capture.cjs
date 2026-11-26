// Screenshots of every screen of Enlaza for "La biblia de Enlaza" (docs/biblia/capturas/, git-ignored).
// scripts/build_biblia.sh runs scripts/reset_demo.py BEFORE (clean operation, no rehearsal data) and AFTER this
// script (removes what the interactive captures created: a family request, an urgent request, voice notes).
// Runs inside the vela-biblia image on the Compose network, with a real window (xvfb) so the maps draw:
//   docker run ... --network vela_default vela-biblia xvfb-run -a node docs/biblia/build/capture.cjs
// ONLY=familia,voz node capture.cjs  -> only the steps whose name contains one of those words.
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE = process.env.BASE || "http://proxy:8080";
const OUT = path.resolve(__dirname, "..", "capturas");
const ONLY = (process.env.ONLY || "").split(",").filter(Boolean);
const PROJECTOR = { width: 1280, height: 800 };
const PHONE = { width: 390, height: 844 };
fs.mkdirSync(OUT, { recursive: true });

let browser;
const want = (name) => !ONLY.length || ONLY.some((w) => name.includes(w));

async function session(user, { viewport = PROJECTOR, simple = false } = {}) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: viewport.width < 500 ? 2 : 1.5, locale: "es-MX",
    timezoneId: "America/Mexico_City" });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/entrar`);
  if (simple) await page.getByLabel("Modo sencillo", { exact: false }).check();
  await page.fill('input[type="email"]', `${user}@ejemplo.test`);
  await page.fill('input[autocomplete="current-password"]', "Demo2026!");
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.endsWith("/entrar"), { timeout: 20000 });
  await page.waitForSelector("header", { timeout: 20000 });
  return { ctx, page };
}

async function settle(page, ms = 2500) {
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(ms);                      // charts animate, map tiles arrive
}

async function shot(page, name, { full = true } = {}) {
  const file = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: file, fullPage: full });
  // the visible text, for the final check that no screenshot shows test data (verify.py)
  fs.writeFileSync(file.replace(/\.png$/, ".txt"), await page.locator("body").innerText().catch(() => ""));
  console.log("captura", name);
}

async function screens(user, list, opts = {}) {
  const todo = list.filter(([name]) => want(name));
  if (!todo.length) return;
  const { ctx, page } = await session(user, opts);
  for (const [name, route, extra] of todo) {
    await page.goto(`${BASE}${route}`);
    await settle(page, extra?.wait ?? 2500);
    if (extra?.before) await extra.before(page);
    await shot(page, name, { full: false });                       // what fits on one screen (used in the book)
    if (extra?.full ?? true) await shot(page, `${name}_completa`); // the whole page, for reference
  }
  await ctx.close();
}

(async () => {
  browser = await chromium.launch({ headless: false });

  // ---- Public pages
  if (want("publico")) {
    const ctx = await browser.newContext({ viewport: PROJECTOR, deviceScaleFactor: 1.5, locale: "es-MX", timezoneId: "America/Mexico_City" });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/`); await settle(page);
    await shot(page, "publico_inicio", { full: false });
    await shot(page, "publico_inicio_completo");
    await page.goto(`${BASE}/entrar`); await settle(page, 800);
    await shot(page, "publico_entrar", { full: false });
    await ctx.close();
  }

  // ---- Static screens, one session per role (state right after reset_demo.py)
  await screens("owner", [
    ["direccion_panorama", "/panorama"],
    ["direccion_panorama_poblacion", "/panorama?vista=panorama"],
    ["direccion_simulacion", "/simulacion"],
    ["direccion_contingencia", "/contingencia", { wait: 5000 }],
    ["direccion_negocio", "/negocio"],
    ["direccion_privacidad", "/privacidad"],
    ["direccion_demo", "/demo"],
  ]);
  await screens("coordinacion.a", [
    ["coordinacion_tablero", "/tablero", { wait: 5000 }],
    ["coordinacion_aprobaciones_vacia", "/aprobaciones"],
    ["coordinacion_pacientes", "/pacientes"],
    ["coordinacion_ficha", "/pacientes/PAC-0001"],
    ["coordinacion_personal", "/personal", { wait: 5000 }],
    ["coordinacion_privacidad", "/privacidad"],
  ]);
  await screens("cui-001", [                          // physician (Laura Medina, INS-A)
    ["medico_reportes_vacio", "/reportes-voz"],
    ["medico_pacientes", "/pacientes"],
    ["medico_mis_visitas", "/mis-visitas"],
  ]);
  await screens("cui-003", [                          // caregiver (Alejandro González, INS-A)
    ["cuidador_mis_visitas", "/mis-visitas"],
    ["cuidador_voz", "/voz"],
  ]);
  await screens("fam-0001", [
    ["familia_inicio", "/familia"],
    ["familia_voz", "/voz"],
    ["familia_privacidad", "/privacidad"],
  ]);
  await screens("fam-0001", [["familia_celular", "/familia"]], { viewport: PHONE });
  await screens("fam-0001", [["familia_sencillo", "/familia"]], { simple: true });
  await screens("cui-003", [["cuidador_celular", "/mis-visitas"]], { viewport: PHONE });
  await screens("coordinacion.a", [["coordinacion_tablero_celular", "/tablero", { wait: 5000, full: false }]], { viewport: PHONE });

  // ---- Cards of the long pages, one image per card (main section), for Part II
  async function cards(user, route, prefix, opts = {}) {
    if (!want(prefix)) return;
    const { ctx, page } = await session(user, opts);
    await page.goto(`${BASE}${route}`); await settle(page, opts.wait ?? 3500);
    if (opts.before) await opts.before(page);
    const list = page.locator("main section");
    const n = await list.count();
    for (let i = 0; i < n; i++) {
      const el = list.nth(i);
      if ((await el.boundingBox())?.height < 40) continue;
      await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(400);
      const card = path.join(OUT, `${prefix}_${String(i + 1).padStart(2, "0")}.png`);
      await el.screenshot({ path: card });
      fs.writeFileSync(card.replace(/\.png$/, ".txt"), await el.innerText().catch(() => ""));
    }
    console.log("tarjetas", prefix, n);
    await ctx.close();
  }
  await cards("owner", "/simulacion", "tarjeta_simulacion");
  await cards("owner", "/negocio", "tarjeta_negocio");
  await cards("owner", "/panorama?vista=panorama", "tarjeta_poblacion");
  await cards("owner", "/panorama", "tarjeta_operacion");
  await cards("coordinacion.a", "/personal", "tarjeta_personal", { wait: 5000 });
  await cards("coordinacion.a", "/contingencia", "tarjeta_contingencia", { wait: 5000 });
  for (const [tab, name] of [["Consentimientos", "tarjeta_consentimientos"], ["Derechos ARCO", "tarjeta_arco"]]) {
    await cards("coordinacion.a", "/privacidad", name, { before: async (page) => {
      await page.getByRole("button", { name: tab }).first().click().catch(() => page.getByRole("tab", { name: tab }).click());
      await page.waitForTimeout(1500); } });
  }
  await cards("owner", "/privacidad", "tarjeta_bitacora", { before: async (page) => {
    await page.getByRole("button", { name: "Bitácora" }).first().click().catch(() => page.getByRole("tab", { name: "Bitácora" }).click());
    await page.waitForTimeout(2000); } });

  // ---- Interactive captures (reset_demo.py removes all of this afterwards)
  if (want("urgente")) {
    // Dirección creates an urgent high-priority request from the demo panel -> coordination must approve
    const own = await session("owner");
    await own.page.goto(`${BASE}/demo`); await settle(own.page, 1500);
    await own.page.getByRole("button", { name: "Crear solicitud urgente" }).click();
    await own.page.waitForTimeout(2500);
    const coord = await session("coordinacion.a");
    await coord.page.goto(`${BASE}/aprobaciones`); await settle(coord.page, 2000);
    await shot(coord.page, "urgente_aprobaciones");
    await coord.page.goto(`${BASE}/tablero`); await settle(coord.page, 4000);
    await shot(coord.page, "urgente_tablero");
    await own.ctx.close(); await coord.ctx.close();
  }

  if (want("voz")) {
    const fam = await session("fam-0001");
    const say = async (text) => {
      await fam.page.goto(`${BASE}/voz`); await settle(fam.page, 1200);
      await fam.page.getByRole("button", { name: "Escribir el mensaje" }).click();
      await fam.page.getByLabel("Escribe lo que pasa").fill(text);
      await fam.page.getByRole("button", { name: "Enviar mensaje" }).click();
      await fam.page.waitForTimeout(5000);
    };
    // a routine message (typed: the classroom microphone is not needed)
    await say("Mi papá amaneció de buen humor, desayunó completo y ya se tomó sus pastillas.");
    await shot(fam.page, "voz_rutina_familia", { full: false });
    // a routine message that the classifier v1 alone marks as emergency (a real false alarm): amber notice
    await say("Hoy mi mamá comió bien y durmió su siesta.");
    await shot(fam.page, "voz_ambar_falsa_alarma", { full: false });
    // an emergency (a rule fires) -> full-screen red notice, before the LLM
    await say("Mi mamá no puede respirar, tiene los labios morados y casi no responde.");
    await shot(fam.page, "voz_emergencia_911", { full: false });
    await fam.ctx.close();
    // the physician's inbox once the local LLM has written the report (can take a minute)
    const doc = await session("cui-001");
    for (let i = 0; i < 60; i++) {
      await doc.page.goto(`${BASE}/reportes-voz`); await settle(doc.page, 1500);
      const txt = await doc.page.locator("main").innerText();
      if (!txt.includes("No hay reportes") && !/preparando|generando|pendiente/i.test(txt)) break;
      await doc.page.waitForTimeout(5000);
    }
    await shot(doc.page, "voz_reportes_medico");
    await doc.ctx.close();
    // coordination sees the critical review alert of the amber notice on its live board
    const coord = await session("coordinacion.a");
    await coord.page.goto(`${BASE}/tablero`); await settle(coord.page, 4000);
    await shot(coord.page, "voz_revision_tablero", { full: false });
    await coord.ctx.close();
  }

  if (want("contingencia")) {
    // Dirección starts the demo contingency; the worker detects it and proposes; coordination approves; back to normal
    const own = await session("owner");
    await own.page.goto(`${BASE}/demo`); await settle(own.page, 1500);
    await own.page.getByRole("button", { name: "Contingencia en el oriente" }).click();
    const coord = await session("coordinacion.a");
    let found = false;
    for (let i = 0; i < 30 && !found; i++) {                 // detection takes under a minute (worker tick)
      await coord.page.waitForTimeout(5000);
      await coord.page.goto(`${BASE}/contingencia`); await settle(coord.page, 2500);
      found = (await coord.page.getByRole("button", { name: "Aprobar todo" }).count()) > 0;
    }
    await shot(coord.page, "contingencia_propuesta", { full: false });
    await shot(coord.page, "contingencia_propuesta_completa");
    await coord.page.goto(`${BASE}/tablero`); await settle(coord.page, 4000);
    await shot(coord.page, "contingencia_tablero", { full: false });
    await coord.page.goto(`${BASE}/contingencia`); await settle(coord.page, 2500);
    if (found) {
      await coord.page.getByRole("button", { name: "Aprobar todo" }).first().click();
      await coord.page.waitForTimeout(3000);
      await shot(coord.page, "contingencia_aprobada", { full: false });
    }
    await own.page.goto(`${BASE}/contingencia`); await settle(own.page, 3000);
    await shot(own.page, "contingencia_direccion", { full: false });
    await own.page.goto(`${BASE}/demo`); await settle(own.page, 1500);
    await own.page.getByRole("button", { name: "Volver a normal" }).click();
    await own.page.waitForTimeout(3000);
    await own.ctx.close(); await coord.ctx.close();
  }

  if (want("solicitud")) {
    // The family asks for a service. The family does not choose the priority: the patient's base priority is used.
    //   fam-0002 (PAC-0002, medium) -> assigned at once (approval = auto)
    //   fam-0001 (PAC-0001, high)   -> waits for coordination in Aprobaciones
    for (const [user, name] of [["fam-0002", "solicitud_familia_enviada"], ["fam-0001", "solicitud_familia_alta"]]) {
      const fam = await session(user);
      await fam.page.goto(`${BASE}/familia`); await settle(fam.page, 1500);
      const d = new Date(Date.now() + 2 * 24 * 3600 * 1000);
      const dd = String(d.getDate()).padStart(2, "0"), mm = String(d.getMonth() + 1).padStart(2, "0");
      await fam.page.getByPlaceholder("dd/mm/aaaa").first().fill(`${dd}/${mm}/${d.getFullYear()}`);
      const hour = fam.page.locator("main select").first();
      if (await hour.count()) await hour.selectOption({ label: "11:00" }).catch(() => {});
      await fam.page.getByRole("button", { name: "Solicitar servicio" }).click();
      await fam.page.waitForTimeout(3000);
      await shot(fam.page, name);
      await fam.ctx.close();
    }
  }

  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
