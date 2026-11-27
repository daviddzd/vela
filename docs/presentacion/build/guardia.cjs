// Click guard for the screenshots of the colloquium deck (the same rules as docs/video/build/grabar.cjs):
//   - NEVER click "Llamar al 911", "800 911 2000" or any tel: link; click() stops everything if the target is (or is
//     inside) a tel: link or its text mentions 911. BLOCK_TEL (an init script) cancels any tel: navigation as a
//     second barrier.
//   - NEVER click "Mostrar contraseña" or "Usuarios de prueba": the password must never show in a screenshot.
//   - noPassword(page) fails if the demo password is visible as text or inside a visible input.
const PASSWORD = "Demo2026!";   // public on purpose, only for the synthetic demo users (CLAUDE.md rule 9)

const BLOCK_TEL = () => {
  document.addEventListener("click", (e) => {
    const a = e.target && e.target.closest && e.target.closest("a[href^='tel:']");
    if (a) { e.preventDefault(); e.stopImmediatePropagation(); console.error("BLOQUEADO: clic en " + a.href); }
  }, true);
};

async function click(locator) {
  const target = locator.first();
  await target.waitFor({ state: "visible", timeout: 20000 });
  const info = await target.evaluate((el) => {
    const a = el.closest("a");
    return { href: a ? a.getAttribute("href") || "" : "", text: (el.innerText || el.textContent || "").trim() };
  });
  if (/^tel:/i.test(info.href) || /911/.test(info.text)) {
    throw new Error(`GUARDIA: se intentó hacer clic en un enlace de llamada («${info.text}» ${info.href}). Capturas detenidas.`);
  }
  if (/Mostrar contraseña|Usuarios de prueba/i.test(info.text)) {
    throw new Error(`GUARDIA: se intentó hacer clic en «${info.text}». Capturas detenidas.`);
  }
  await target.click();
}

async function noPassword(page) {
  const leak = await page.evaluate((pw) => {
    if ((document.body.innerText || "").includes(pw)) return "texto";
    for (const i of document.querySelectorAll("input")) if (i.type !== "password" && i.value.includes(pw)) return "campo";
    return "";
  }, PASSWORD);
  if (leak) throw new Error(`GUARDIA: la contraseña se vería en la captura (${leak}). Capturas detenidas.`);
}

module.exports = { PASSWORD, BLOCK_TEL, click, noPassword };
