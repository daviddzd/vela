// "Modo sencillo": larger text (24 px). Remembered in this browser.
const KEY = "vela.simpleMode";

export function getSimpleMode(): boolean {
  return localStorage.getItem(KEY) === "1";
}

export function setSimpleMode(on: boolean): void {
  localStorage.setItem(KEY, on ? "1" : "0");
  document.documentElement.classList.toggle("simple", on);
}
