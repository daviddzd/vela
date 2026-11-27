"""Crops of the screenshots for the deck without live demo -> docs/presentacion/out_capturas/recortes/*.png

    python3 docs/presentacion/build/recortes.py      (inside the vela-presentacion image; see build_presentacion_capturas.sh)

Each crop keeps only the important zone of a screenshot, so it reads on a projector instead of a whole tiny screen.
Boxes are in pixels of the original file (desktop captures are 3840 x 2160, phone captures 1170 x 2532). A crop smaller
than MIN_W pixels wide is enlarged (Lanczos) so PowerPoint does not blur it. The screenshots are in
docs/presentacion/capturas/ (git-ignored; scripts/build_presentacion_capturas.sh --capturas takes them again).
"""
from pathlib import Path

from PIL import Image

PRES = Path(__file__).resolve().parents[1]
SHOTS = PRES / "capturas"
OUT = PRES / "out_capturas" / "recortes"
MIN_W = 1600

# name: (screenshot, (left, top, right, bottom) or None for the whole file)
CROPS = {
    # 1280 x 800 window at 3x density (PROY=1 in capturas.cjs): the app puts the content in less width, so it reads larger
    "c01_solicitud": ("P01_familia_solicitud.png", (76, 1643, 1012, 2435)),
    "c02_asignada": ("P02_familia_asignada.png", (92, 955, 1028, 1423)),
    "c03_nuevas": ("P03_tablero_nueva_lista.png", None),
    "v27_llegue": ("V27_mis_visitas_llegue.png", (10, 195, 420, 680)),          # video 1, scene 2.7 (430 x 932)
    "c05_urgente": ("P05_aprobaciones_urgente_tarjeta.png", None),
    "c06_nuevas": ("P06_tablero_lista.png", None),
    "c07_mapa": ("P07_contingencia_tarjeta_02.png", (83, 217, 2129, 1787)),
    "c08_propuesta": ("P07_contingencia_tarjeta_03.png", (0, 0, 1461, 1872)),
    "c08_aprobar": ("P07_contingencia_tarjeta_03.png", (0, 2160, 1461, 2990)),
    "c09_escrita": ("C09_voz_escrita.png", (51, 1418, 1013, 2140)),
    "c10_roja": ("C10_voz_roja.png", (51, 557, 1089, 1975)),
    "c11_reporte": ("P11_reportes_voz_tarjeta_01.png", (0, 0, 1839, 1310)),
    "c11_limite": ("P11_reportes_voz_tarjeta_01.png", (0, 2075, 1839, 2230)),
    "c12_fila": ("P12_personal_jornada_fila.png", None),
    "c12_detalle": ("P12_personal_jornada_tarjeta_03.png", (0, 0, 2007, 760)),
    "c13_grafica": ("P13_simulacion_presentacion_tarjeta_03.png", (114, 1258, 3318, 2288)),
    "c14_contadores": ("P14_panorama.png", (48, 1632, 3744, 2026)),
    "c14_cumplimos": ("P14_panorama_tarjeta_05.png", (0, 0, 1839, 630)),
    "c15_escenarios": ("P15_negocio_tarjeta_07.png", (0, 342, 3732, 1296)),
    "c15_completo": ("P15_negocio_tarjeta_07.png", (0, 0, 3732, 3069)),
    "c16_bitacora": ("P16_privacidad_tabla.png", (115, 307, 3706, 614)),
    "c17_ambar": ("C17_voz_ambar.png", (38, 38, 1089, 1975)),
    # two zones of the same report card stacked into one image (rules on top, "no es diagnóstico" below)
    "c11_medica": ("P11_reportes_voz_tarjeta_01.png", [(0, 0, 1839, 1310), (0, 2075, 1839, 2230)]),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (file, box) in CROPS.items():
        src = SHOTS / file
        if not src.exists():
            raise SystemExit(f"ERROR: falta la captura {src} (scripts/build_presentacion_capturas.sh --capturas)")
        im = Image.open(src).convert("RGB")
        boxes = box if isinstance(box, list) else [box] if box else []
        for b in boxes:
            if b[2] > im.width or b[3] > im.height:
                raise SystemExit(f"ERROR: el recorte {name} {b} sale de {file} ({im.width} x {im.height})")
        if len(boxes) == 1:
            im = im.crop(boxes[0])
        elif boxes:                       # stacked zones, with a thin grey line between them
            parts = [im.crop(b) for b in boxes]
            gap = 20
            out = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts) + gap * (len(parts) - 1)), "white")
            y = 0
            for i, part in enumerate(parts):
                out.paste(part, (0, y))
                y += part.height
                if i < len(parts) - 1:
                    out.paste((213, 227, 234), (0, y + gap // 2 - 2, out.width, y + gap // 2 + 2))
                    y += gap
            im = out
        if im.width < MIN_W:
            k = MIN_W / im.width
            im = im.resize((MIN_W, round(im.height * k)), Image.LANCZOS)
        im.save(OUT / f"{name}.png", optimize=True)
    print(f"Recortes: {len(CROPS)} en {OUT}")


if __name__ == "__main__":
    main()
