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

(async () => {
  copyFonts();
  const server = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") console.log("[navegador]", m.text()); });
  page.on("pageerror", (e) => console.log("[navegador]", String(e)));
  await page.goto(`http://127.0.0.1:${server.address().port}/out/biblia.html`, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);

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
  const pages = await page.evaluate(async () => {
    const flow = await window.PagedPolyfill.preview();
    return flow.total;
  });
  const pdf = path.join(BIBLIA, process.env.PDF_NAME || "biblia_enlaza.pdf");
  await page.pdf({ path: pdf, preferCSSPageSize: true, printBackground: true, outline: true, tagged: true });
  await browser.close();
  server.close();
  console.log(`PDF listo: ${pdf} (${pages} páginas)`);
})();
