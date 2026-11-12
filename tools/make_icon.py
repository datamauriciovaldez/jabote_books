"""Genera packaging/icon-1024.png (el icono de la app) sin dependencias extra. Uso: python tools/make_icon.py"""
from pathlib import Path

from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((40, 40, S - 40, S - 40), radius=210, fill=(29, 78, 216, 255))          # azul de la interfaz
w = 70
d.arc((230, 200, S - 230, S - 120), 180, 360, fill=(255, 255, 255, 255), width=w)            # arco de los auriculares
for x0 in (205, S - 205 - 150):
    d.rounded_rectangle((x0, 520, x0 + 150, 790), radius=60, fill=(255, 255, 255, 255))       # almohadillas
d.rounded_rectangle((420, 610, 604, 650), radius=20, fill=(255, 255, 255, 255))              # barras de "sonido"
d.rounded_rectangle((460, 560, 564, 600), radius=20, fill=(255, 255, 255, 255))
d.rounded_rectangle((460, 660, 564, 700), radius=20, fill=(255, 255, 255, 255))
out = Path(__file__).resolve().parent.parent / "packaging" / "icon-1024.png"
img.save(out)
print("escrito", out)
