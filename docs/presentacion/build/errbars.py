"""Add native error bars (the 95 % confidence intervals) to the simulation chart of enlaza_coloquio.pptx.

    python3 docs/presentacion/build/errbars.py [deck.pptx]      (default: docs/presentacion/enlaza_coloquio.pptx)

pptxgenjs cannot write error bars, so deck.cjs leaves the values in out/errbars.json (series name, plus, minus) and this
script inserts a <c:errBars> with custom values into that series of the chart XML. The chart stays a native,
editable PowerPoint chart (Format → Error bars). Element order follows the OOXML schema (CT_BarSer: … dLbls, trendline,
errBars, cat, val …).
"""
import json
import re
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path

PRES = Path(__file__).resolve().parents[1]
DECK = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else PRES / "enlaza_coloquio.pptx"
SPECS = json.loads((PRES / "out" / "errbars.json").read_text(encoding="utf-8"))


def num_lit(values: list[float]) -> str:
    pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i, v in enumerate(values))
    return f'<c:numLit><c:formatCode>General</c:formatCode><c:ptCount val="{len(values)}"/>{pts}</c:numLit>'


def err_bars(plus: list[float], minus: list[float]) -> str:
    return ('<c:errBars><c:errBarType val="both"/><c:errValType val="cust"/><c:noEndCap val="0"/>'
            f"<c:plus>{num_lit(plus)}</c:plus><c:minus>{num_lit(minus)}</c:minus>"
            '<c:spPr><a:ln w="28575" cap="rnd"><a:solidFill><a:srgbClr val="1B2B38"/></a:solidFill></a:ln></c:spPr>'
            "</c:errBars>")


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(DECK) as z:
        z.extractall(tmp)
        names = z.namelist()
    done = 0
    for chart in sorted((tmp / "ppt" / "charts").glob("chart*.xml")):
        xml = chart.read_text(encoding="utf-8")
        for spec in SPECS:
            # the <c:ser> whose name is the series
            for m in re.finditer(r"<c:ser>.*?</c:ser>", xml, flags=re.S):
                ser = m.group(0)
                if f"<c:v>{spec['series']}</c:v>" not in ser or "<c:errBars>" in ser:
                    continue
                new = ser.replace("<c:cat>", err_bars(spec["plus"], spec["minus"]) + "<c:cat>", 1)
                xml = xml.replace(ser, new)
                done += 1
        chart.write_text(xml, encoding="utf-8")
    if done != len(SPECS):
        raise SystemExit(f"ERROR: barras de error aplicadas a {done} de {len(SPECS)} series")
    out = DECK.with_suffix(".tmp.pptx")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:                      # same order as the original ([Content_Types].xml first)
            if not n.endswith("/"):           # no folder entries: they break opening the file in cloud services
                z.write(tmp / n, n)
    shutil.move(out, DECK)
    shutil.rmtree(tmp)
    print(f"Barras de error (intervalos de confianza): {done} serie(s)")


if __name__ == "__main__":
    main()
