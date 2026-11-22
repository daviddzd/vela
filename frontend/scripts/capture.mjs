// Screenshots of Panorama-AM for design review (docs/dev/capturas/).
// Runs inside the official Playwright image on the Compose network (no browser install on the laptop):
//   docker run --rm --network vela_default -v "$PWD/frontend/scripts:/scripts:ro" \
//     -v "$PWD/docs/dev/capturas:/out" -e BASE=http://proxy:8080 mcr.microsoft.com/playwright:<version> \
//     sh -c "cd /tmp && npm i -s playwright@<version> && node /scripts/capture.mjs"
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:8080";
const OUT = process.env.OUT ?? "/out";
const USERS = Object.fromEntries(Object.entries({ coordinacion: "coordinacion.a@ejemplo.test", direccion: "owner@ejemplo.test" })
  .filter(([k]) => !process.env.ONLY || process.env.ONLY.split(",").includes(k)));
const SIZES = { proyector: { width: 1280, height: 720 }, celular: { width: 390, height: 844 } };
const VIEWS = { operacion: "operacion", panorama: "panorama" };

const browser = await chromium.launch();
for (const [who, email] of Object.entries(USERS)) {
  for (const [sizeName, viewport] of Object.entries(SIZES)) {
    const ctx = await browser.newContext({ viewport, deviceScaleFactor: sizeName === "celular" ? 2 : 1, locale: "es-MX",
      timezoneId: "America/Mexico_City" });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/`);
    await page.fill('input[type="email"]', email);
    await page.fill('input[autocomplete="current-password"]', "Demo2026!");
    await page.click('button[type="submit"]');
    await page.waitForURL((u) => !u.pathname.endsWith("/"), { timeout: 15000 });
    for (const view of Object.keys(VIEWS)) {
      await page.goto(`${BASE}/panorama${view === "panorama" ? "?vista=panorama" : ""}`);
      await page.waitForSelector("canvas", { timeout: 20000 });
      await page.waitForTimeout(2500);                     // let charts animate and the map tiles settle
      const file = `${OUT}/${view}_${who}_${sizeName}.png`;
      await page.screenshot({ path: file, fullPage: true });
      console.log("saved", file);
      if (view === "panorama") {                                // broad multimorbidity vs ENSANUT
        await page.getByLabel("Multimorbilidad amplia", { exact: false }).check();
        await page.waitForTimeout(1200);
        const card = `${OUT}/tarjetas/multimorbilidad_amplia_${sizeName}.png`;
        await page.locator("main section").first().screenshot({ path: card });
        console.log("saved", card);
      }
      if (sizeName === "celular" && view === "operacion") {     // the mobile menu, opened
        await page.getByRole("button", { name: "Menú" }).click();
        await page.screenshot({ path: `${OUT}/menu_${who}_celular.png` });
        console.log("saved", `${OUT}/menu_${who}_celular.png`);
        await page.getByRole("button", { name: "Cerrar", exact: true }).click();
      }
      if (sizeName === "celular" && who === "coordinacion") {   // one image per card, readable on review
        const cards = page.locator("main section");
        for (let i = 0; i < (await cards.count()); i++) {
          const card = `${OUT}/tarjetas/${view}_celular_${String(i + 1).padStart(2, "0")}.png`;
          await cards.nth(i).screenshot({ path: card });
          console.log("saved", card);
        }
      }
    }
    await ctx.close();
  }
}
await browser.close();
