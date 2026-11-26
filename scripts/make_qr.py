# /// script
# requires-python = ">=3.10"
# dependencies = ["qrcode[pil]"]
# ///
"""QR codes for the public address. They go to docs/privado/ (git-ignored).

    uv run scripts/make_qr.py                                    # https://enlaza.zenthinks.com
    uv run scripts/make_qr.py https://xxx.trycloudflare.com      # quick tunnel (backup): makes qr_rapido*.png

Writes qr_enlaza.png (to print or share) and qr_enlaza_diapositiva.png (1920x1080 slide, QR + the address).
Error correction "H" so it still scans from the back of the room or on a dim projector. Colors: deep navy and white
from docs/brand.md (dark on light, the contrast a phone camera needs).
"""
import sys
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEEP, TEAL_TEXT, WHITE = "#1B3349", "#137273", "#FFFFFF"   # deep navy, teal-text
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def qr_image(url: str, box: int) -> Image.Image:
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=box, border=4)
    q.add_data(url)
    q.make(fit=True)
    return q.make_image(fill_color=DEEP, back_color=WHITE).convert("RGB")


def main() -> None:
    url = (sys.argv[1] if len(sys.argv) > 1 else "https://enlaza.zenthinks.com").rstrip("/")
    prefix = "qr_enlaza" if "zenthinks.com" in url else "qr_rapido"
    out = ROOT / "docs" / "privado"
    out.mkdir(parents=True, exist_ok=True)

    qr_image(url, 20).save(out / f"{prefix}.png")

    slide = Image.new("RGB", (1920, 1080), WHITE)
    code = qr_image(url, 30)
    code.thumbnail((780, 780), Image.NEAREST)
    slide.paste(code, (1920 - 780 - 140, (1080 - code.height) // 2))
    d = ImageDraw.Draw(slide)
    big, mid = ImageFont.truetype(FONT, 92), ImageFont.truetype(FONT, 52)
    d.text((140, 330), "Entra a Enlaza", font=big, fill=DEEP)
    d.text((140, 470), "desde tu celular", font=mid, fill=TEAL_TEXT)
    d.text((140, 640), url.replace("https://", ""), font=mid, fill=DEEP)
    slide.save(out / f"{prefix}_diapositiva.png")
    print(f"{out / f'{prefix}.png'}\n{out / f'{prefix}_diapositiva.png'}")


if __name__ == "__main__":
    main()
