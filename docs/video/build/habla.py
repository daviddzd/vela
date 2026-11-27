"""Subtitle text (with figures) -> the text Piper reads (only words).

The subtitles keep the figures exactly as numeros.json prints them; the voice gets them spelled out in Spanish. After
converting, `check()` stops the build if any digit, symbol or URL is left (Piper would read them badly or skip them):
the forbidden characters are 0-9 $ % : / + − – and the text "https".

    python3 docs/video/build/habla.py "La API ve 0 pacientes; Whisper pesa 486 MB."   (try one sentence)
"""
from __future__ import annotations

import re
import sys

from num2words import num2words

FORBIDDEN = re.compile(r"[0-9$%:/+−–]|https")

# Names and acronyms, in the order they are applied (longest first where one contains another).
TERMS: list[tuple[str, str]] = [
    (r"https://enlaza\.zenthinks\.com", "enlaza punto zenthinks punto com"),
    (r"enlaza\.zenthinks\.com", "enlaza punto zenthinks punto com"),
    (r"qwen3:8b", "Qwen tres, de ocho B"),
    (r"SIRAG-D", "Sirag de"),
    (r"ENSANUT", "Ensanut"),
    (r"ENASEM", "Enasem"),
    (r"DENUE", "Denue"),
    (r"ARCO", "arco"),
    (r"TPS", "te pe ese"),
    (r"CRM", "ce erre eme"),
    (r"ERP", "e erre pe"),
    (r"MIS", "eme i ese"),
    (r"DSS", "de ese ese"),
    (r"API", "a pe i"),
    (r"IA", "i a"),
    (r"HTTP", "hache te te pe"),
    (r"PostgreSQL", "Postgres"),
    (r"WebSocket", "web sóket"),
    (r"PowerShell", "páuer shel"),
    (r"cloudflared", "cloudflare de"),
    (r"WhatsApp", "uatsap"),
    (r"hotspot", "jótspot"),
]

UNITS = {  # unit -> (singular, plural)
    "MB": ("megabyte", "megabytes"), "GB": ("gigabyte", "gigabytes"), "ms": ("milisegundo", "milisegundos"),
    "s": ("segundo", "segundos"), "min": ("minuto", "minutos"), "h": ("hora", "horas"),
}
NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"


def words(num: str, noun_follows: bool = False) -> str:
    """'1,491,619' -> words; '20.2' -> 'veinte punto dos'; '98.0' -> 'noventa y ocho'."""
    num = num.replace(",", "")
    whole, _, dec = num.partition(".")
    if dec and set(dec) == {"0"}:
        dec = ""
    out = num2words(int(whole), lang="es")
    out = re.sub(r"veintiuno (mil|millones)", r"veintiún \1", out)   # num2words says "noventa y uno mil"
    out = re.sub(r"\buno (mil|millones)", r"un \1", out)
    if noun_follows and out.endswith("veintiuno"):
        out = out[:-3] + "ún"   # "veintiún minutos"
    elif noun_follows and out.endswith("uno"):
        out = out[:-1]          # "treinta y un minutos"
    if dec:
        out += " punto " + " ".join(num2words(int(d), lang="es") for d in dec)
    return out


def spoken(text: str) -> str:
    """Return the sentence as Piper should read it."""
    t = text
    for pat, rep in TERMS:
        t = re.sub(rf"(?<![\w.]){pat}(?![\w])", rep, t)
    # money: −$163,128 / $5,500
    t = re.sub(rf"([−-])?\$({NUM})", lambda m: ("menos " if m.group(1) else "") + words(m.group(2)) + " pesos", t)
    # ranges: 5–15 min
    t = re.sub(rf"({NUM})–({NUM})\s?min\b", lambda m: f"de {words(m.group(1))} a {words(m.group(2))} minutos", t)
    # 8.2B (parameters)
    t = re.sub(rf"({NUM})B\b(\s+[a-záéíóúñ])?",
               lambda m: words(m.group(1)) + " mil millones" + (" de" + m.group(2) if m.group(2) else ""), t)
    # percentages: 98.0 % / 15 %
    t = re.sub(rf"({NUM})\s?%", lambda m: words(m.group(1)) + " por ciento", t)
    # units: 486 MB, 185 ms, 60 s (= un minuto), 3 min, 7 h

    def unit(m: re.Match) -> str:
        n, u = m.group(1), m.group(2)
        if u == "s" and n == "60":
            return "un minuto"
        one = n.replace(",", "") == "1"
        return ("un" if one else words(n, noun_follows=True)) + " " + UNITS[u][0 if one else 1]
    t = re.sub(rf"({NUM})\s?(MB|GB|ms|min|s|h)\b", unit, t)
    # anything else that is a number
    t = re.sub(NUM, lambda m: words(m.group(0)), t)
    # punctuation the voice does not need: a colon is a pause, like a comma
    t = t.replace(": ", ", ").replace("«", "").replace("»", "")
    return re.sub(r"\s+", " ", t).strip()


def check(said: str, where: str) -> None:
    """Stop the build if the voice text still has a digit, a symbol or a URL."""
    bad = FORBIDDEN.findall(said)
    if bad:
        sys.exit(f"ERROR ({where}): el texto para la voz todavía tiene {sorted(set(bad))}: «{said}»")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        s = spoken(arg)
        check(s, "prueba")
        print(s)
