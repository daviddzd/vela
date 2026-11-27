// Proves the click guard of grabar.cjs: a click on any tel: link (or on text with 911) stops the recording, and the
// init script cancels a tel: navigation even if something clicks it directly. Run by scripts/build_video.sh before
// recording:  node docs/video/build/test_guardia.cjs
process.env.OUT = process.env.OUT || require("path").resolve(__dirname, "../../privado/video/clips/prueba");
const { chromium } = require("playwright");
const { click, BLOCK_TEL } = require("./grabar.cjs");

(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext()).newPage();
  await page.addInitScript(BLOCK_TEL);
  await page.goto("about:blank");
  await page.setContent(`
    <a id="a" href="tel:911">Llamar al 911</a>
    <a id="b" href="tel:8009112000">800 911 2000</a>
    <a id="c" href="tel:5555555555"><span id="c2">Llamar a la institución</span></a>
    <button id="ok" onclick="this.dataset.done=1">Solicitar servicio</button>`);
  let fails = 0;
  for (const id of ["a", "b", "c2"]) {
    try { await click(page.locator("#" + id)); console.log(`MAL: el guardia dejó hacer clic en #${id}`); fails++; }
    catch (e) { console.log(`bien: #${id} bloqueado (${e.message.slice(0, 60)}…)`); }
  }
  await click(page.locator("#ok"));
  if (await page.locator("#ok").getAttribute("data-done") !== "1") { console.log("MAL: no dejó hacer un clic normal"); fails++; }
  else console.log("bien: un clic normal sí funciona");
  // second barrier: a direct click (without the guard) on a tel: link does not navigate
  await page.locator("#a").click();
  if (page.url() !== "about:blank") { console.log("MAL: la página navegó a " + page.url()); fails++; }
  else console.log("bien: el clic directo en tel:911 no navegó");
  await browser.close();
  if (fails) { console.log(`${fails} falla(s)`); process.exit(1); }
  console.log("Guardia de llamadas: todo bien");
})();
