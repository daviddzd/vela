// docs/video/out/diapositivas/<id>.html (diapositivas.py) -> docs/privado/video/diapositivas/<id>.png, 1920x1080.
// Run inside the vela-video image:  node docs/video/build/diapositivas.cjs
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const SRC = path.resolve(__dirname, "..", "out", "diapositivas");
const OUT = path.resolve(__dirname, "..", "..", "privado", "video", "diapositivas");

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
  for (const f of fs.readdirSync(SRC).filter((f) => f.endsWith(".html")).sort()) {
    await page.goto("file://" + path.join(SRC, f));
    await page.evaluate(() => document.fonts.ready);
    // nothing may overflow the slide: a long text would be cut on video
    const over = await page.evaluate(() => document.body.scrollHeight > 1080 || document.body.scrollWidth > 1920);
    if (over) throw new Error(`La diapositiva ${f} no cabe en 1920x1080: acortar el texto`);
    // the footer sits above the subtitles (bottom 160 px): no content may reach it
    const hit = await page.evaluate(() => {
      const foot = document.querySelector(".foot").getBoundingClientRect();
      return [...document.body.children].filter((e) => !e.classList.contains("foot") && !e.classList.contains("logo"))
        .some((e) => e.getBoundingClientRect().bottom > foot.top - 8);
    });
    if (hit) throw new Error(`La diapositiva ${f}: el contenido toca el pie de página; acortar el texto`);
    await page.screenshot({ path: path.join(OUT, f.replace(/\.html$/, ".png")) });
  }
  await browser.close();
  console.log("PNG en", OUT);
})().catch((e) => { console.error(e.message); process.exit(1); });
