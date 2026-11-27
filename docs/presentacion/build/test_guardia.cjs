// Proves the click guard (guardia.cjs) before any screenshot:  node docs/presentacion/build/test_guardia.cjs
const { chromium } = require("playwright");
const { click, BLOCK_TEL, noPassword, PASSWORD } = require("./guardia.cjs");

(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext()).newPage();
  await page.addInitScript(BLOCK_TEL);
  await page.goto("about:blank");
  await page.setContent(`
    <a id="a" href="tel:911">Llamar al 911</a>
    <a id="b" href="tel:8009112000">800 911 2000</a>
    <a id="c" href="tel:5555555555"><span id="c2">Llamar a la institución</span></a>
    <label id="d"><input type="checkbox"> Mostrar contraseña</label>
    <button id="e">Usuarios de prueba</button>
    <button id="ok" onclick="this.dataset.done=1">Solicitar servicio</button>
    <input id="pw" type="password">`);
  let fails = 0;
  for (const id of ["a", "b", "c2", "d", "e"]) {
    try { await click(page.locator("#" + id)); console.log(`MAL: el guardia dejó hacer clic en #${id}`); fails++; }
    catch (e) { console.log(`bien: #${id} bloqueado`); }
  }
  await click(page.locator("#ok"));
  if (await page.locator("#ok").getAttribute("data-done") !== "1") { console.log("MAL: no dejó hacer un clic normal"); fails++; }
  else console.log("bien: un clic normal sí funciona");
  await page.locator("#a").click();   // second barrier: a direct click on a tel: link does not navigate
  if (page.url() !== "about:blank") { console.log("MAL: la página navegó a " + page.url()); fails++; }
  else console.log("bien: el clic directo en tel:911 no navegó");
  await page.fill("#pw", PASSWORD);
  try { await noPassword(page); console.log("bien: contraseña en campo de puntos no cuenta"); } catch { console.log("MAL"); fails++; }
  await page.evaluate(() => { document.querySelector("#pw").type = "text"; });
  try { await noPassword(page); console.log("MAL: no detectó la contraseña visible"); fails++; } catch { console.log("bien: contraseña visible detectada"); }
  await browser.close();
  if (fails) { console.log(`${fails} falla(s)`); process.exit(1); }
  console.log("Guardia: todo bien");
})();
