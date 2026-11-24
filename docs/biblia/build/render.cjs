// Print docs/biblia/out/biblia.html to docs/biblia/biblia_enlaza.pdf with Chromium.
//   1. copies the fonts (Atkinson Hyperlegible, Plus Jakarta Sans) next to the HTML
//   2. draws every Mermaid diagram (```mermaid blocks) as SVG
//   3. Paged.js splits the book into letter pages: page numbers, running header, index with page numbers
//   4. Chromium writes the PDF with bookmarks (outline) built from the headings
// Runs inside the vela-biblia image (see scripts/build_biblia.sh).
const fs = require("fs");
const path = require("path");
const http = require("http");
const { chromium } = require("playwright");

const BIBLIA = path.resolve(__dirname, "..");
const OUT = path.join(BIBLIA, "out");
const MODULES = process.env.NODE_PATH || "/opt/biblia/node_modules";

function copyFonts() {
  const dir = path.join(OUT, "assets", "fonts");
  fs.mkdirSync(dir, { recursive: true });
  const faces = [
    ["Atkinson Hyperlegible", "atkinson-hyperlegible", [[400, "normal"], [400, "italic"], [700, "normal"], [700, "italic"]]],
    ["Plus Jakarta Sans", "plus-jakarta-sans", [[400, "normal"], [600, "normal"], [700, "normal"], [800, "normal"]]],
  ];
  let css = "";
  for (const [family, pkg, variants] of faces) {
    for (const [weight, style] of variants) {
      for (const subset of ["latin", "latin-ext"]) {
        const file = `${pkg}-${subset}-${weight}-${style}.woff2`;
        const src = path.join(MODULES, "@fontsource", pkg, "files", file);
        if (!fs.existsSync(src)) continue;
        fs.copyFileSync(src, path.join(dir, file));
        css += `@font-face{font-family:"${family}";font-style:${style};font-weight:${weight};font-display:block;src:url(fonts/${file}) format("woff2");}\n`;
      }
    }
  }
  fs.writeFileSync(path.join(OUT, "assets", "fonts.css"), css);
}

// Paged.js reads the stylesheets with XHR, which Chromium blocks on file:// pages: serve docs/biblia over http.
function serve() {
  const types = { ".html": "text/html", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png",
    ".jpg": "image/jpeg", ".woff2": "font/woff2", ".js": "text/javascript" };
  const server = http.createServer((req, res) => {
    const file = path.join(BIBLIA, decodeURIComponent(new URL(req.url, "http://x").pathname));
    if (!file.startsWith(BIBLIA) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { "Content-Type": types[path.extname(file)] || "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((ok) => server.listen(0, "127.0.0.1", () => ok(server)));
}

// One full layout: load the HTML, apply the figure adjustments of earlier passes, draw Mermaid, paginate.
async function layout(page, url, mods) {
  await page.goto(url, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  // adjustments decided by earlier passes: shrink a figure, or let the next block go before it
  await page.evaluate((mods) => {
    for (const [id, m] of Object.entries(mods)) {
      const fig = document.querySelector(`figure[data-fig="${id}"]`);
      if (!fig) continue;
      if (m.maxHeight) fig.style.setProperty("--fit-height", `${Math.floor(m.maxHeight)}px`), fig.classList.add("fit");
      for (let k = 0; k < (m.defer || 0); k++) {
        const next = fig.nextElementSibling;
        if (next && !/^H[1-4]$/.test(next.tagName)) next.after(fig);
      }
    }
  }, mods);

  // Mermaid diagrams, in the Enlaza palette (docs/brand.md)
  await page.addScriptTag({ path: path.join(MODULES, "mermaid", "dist", "mermaid.min.js") });
  const failed = await page.evaluate(async () => {
    window.mermaid.initialize({
      startOnLoad: false, theme: "base", securityLevel: "loose",
      flowchart: { htmlLabels: true, curve: "basis", padding: 12, useMaxWidth: true },
      sequence: { useMaxWidth: true, mirrorActors: false },
      themeVariables: {
        fontFamily: "Atkinson Hyperlegible, sans-serif", fontSize: "17px",
        primaryColor: "#E3F5F5", primaryBorderColor: "#137273", primaryTextColor: "#1B2B38",
        secondaryColor: "#EAF4F8", tertiaryColor: "#F4F9FB", lineColor: "#3A5B76",
        clusterBkg: "#F4F9FB", clusterBorder: "#3A5B76", noteBkgColor: "#FFF6E0", noteBorderColor: "#8A5A00",
        actorBkg: "#E3F5F5", actorBorder: "#137273", signalColor: "#1B2B38", signalTextColor: "#1B2B38",
      },
    });
    const bad = [];
    const nodes = [...document.querySelectorAll("pre.mermaid")];
    for (let i = 0; i < nodes.length; i++) {
      try { await window.mermaid.run({ nodes: [nodes[i]] }); }
      catch (e) { bad.push(`${nodes[i].closest("section")?.id}: ${String(e).slice(0, 200)}`); }
    }
    return bad;
  });
  if (failed.length) { console.error("Diagramas con error:\n" + failed.join("\n")); process.exit(1); }

  // Paged.js: pages, numbers, index page numbers, cross references
  await page.addScriptTag({ content: "window.PagedConfig = { auto: false };" });
  await page.addScriptTag({ path: path.join(MODULES, "pagedjs", "dist", "paged.polyfill.js") });
  const total = await page.evaluate(async () => (await window.PagedPolyfill.preview()).total);

  // Find figures that start a page and left a big gap at the end of the previous page (same chapter).
  const gaps = await page.evaluate(() => {
    const pages = [...document.querySelectorAll(".pagedjs_page")];
    const area = (pg) => pg.querySelector(".pagedjs_page_content");
    const chapterOf = (el) => el?.closest("section")?.getAttribute("data-ref");
    const lastBottom = (pg) => {
      let b = area(pg).getBoundingClientRect().top, last = null;
      for (const e of area(pg).querySelectorAll("p,li,figure,table,pre,h1,h2,h3,h4,.admonition,dt,dd")) {
        const r = e.getBoundingClientRect();
        if (r.height > 0 && r.bottom > b) { b = r.bottom; last = e; }
      }
      return { b, last };
    };
    const out = [];
    for (let i = 1; i < pages.length; i++) {
      const a = area(pages[i]);
      const fig = a.querySelector("figure[data-fig]");
      if (!fig) continue;
      const ar = a.getBoundingClientRect(), fr = fig.getBoundingClientRect();
      if (fr.top - ar.top > 30) continue;                        // the figure is not what starts the page
      const prev = area(pages[i - 1]), pr = prev.getBoundingClientRect();
      const { b, last } = lastBottom(pages[i - 1]);
      if (!last || chapterOf(last) !== chapterOf(fig)) continue;  // end of a chapter: the gap is expected
      const free = pr.bottom - b;
      if (free < 0.22 * pr.height) continue;                     // small gaps are fine
      const media = fig.querySelector("img, svg");
      const h = media ? media.getBoundingClientRect().height : 0;
      const need = fr.height - free + 14;                         // what must disappear for it to fit
      out.push({ id: fig.dataset.fig, h, newHeight: h - need, free, page: i + 1 });
    }
    return out;
  });
  return { total, gaps };
}

(async () => {
  copyFonts();
  const server = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") console.log("[navegador]", m.text()); });
  page.on("pageerror", (e) => console.log("[navegador]", String(e)));
  const url = `http://127.0.0.1:${server.address().port}/out/biblia.html`;

  // Avoid half-empty pages: up to 6 passes. A figure that would leave a big gap is shrunk to fit with its text
  // (down to 55 % of its height); if that is not enough, the next paragraph goes before it and fills the gap.
  const mods = {};
  let result;
  for (let pass = 1; pass <= 6; pass++) {
    result = await layout(page, url, mods);
    const todo = result.gaps.filter((g) => !(mods[g.id]?.done));
    console.log(`pasada ${pass}: ${result.total} páginas, ${todo.length} huecos por ajustar`);
    if (!todo.length) break;
    for (const g of todo) {
      const m = (mods[g.id] ||= {});
      if (g.h > 0 && g.newHeight >= 0.55 * g.h && !m.maxHeight) m.maxHeight = g.newHeight;
      else if ((m.defer || 0) < 3) m.defer = (m.defer || 0) + 1;
      else m.done = true;                                         // give up on this one
    }
  }
  const pdf = path.join(BIBLIA, process.env.PDF_NAME || "biblia_enlaza.pdf");
  await page.pdf({ path: pdf, preferCSSPageSize: true, printBackground: true, outline: true, tagged: true });
  await browser.close();
  server.close();
  console.log(`PDF listo: ${pdf} (${result.total} páginas)`);
})();
