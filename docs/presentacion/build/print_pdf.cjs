// out/guion.html -> docs/presentacion/guion_coloquio.pdf (Chromium, letter size, page numbers in the footer).
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

const PRES = path.resolve(__dirname, "..");
// HTML_DIR / PDF_NAME / FOOTER: the version without live demo (build_presentacion_capturas.sh); defaults: live-demo version
const OUT = path.join(PRES, process.env.HTML_DIR || "out");
const PDF = path.join(PRES, process.env.PDF_NAME || "guion_coloquio.pdf");
const FOOTER = process.env.FOOTER || "Guion del coloquio · Enlaza";
fs.copyFileSync(path.join(PRES, "..", "..", "frontend", "public", "logo.svg"), path.join(OUT, "logo.svg"));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + path.join(OUT, "guion.html"));
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: PDF, format: "Letter", printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: "<span></span>",
    footerTemplate: '<div style="font-size:8pt;color:#4F5F6B;width:100%;text-align:center;font-family:Arial">' +
      FOOTER + ' · <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    margin: { top: "16mm", bottom: "18mm", left: "16mm", right: "16mm" }, tagged: true, outline: true,
  });
  await browser.close();
  console.log("Guion PDF: " + PDF);
})();
