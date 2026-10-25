#!/usr/bin/env python3
"""Audita contraste (WCAG AA 4,5:1) de las 7 paletas de portada y genera una hoja comparativa."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
import generar as g  # noqa: E402
import render as rd  # noqa: E402
from PIL import Image  # noqa: E402

out = Path(__file__).parent / "paletas-portada"
out.mkdir(exist_ok=True)
base = dict(ciudad="Cádiz", prefijo="Planes en", titulo="Qué hacer hoy", subtitulo="lunes 26 de octubre", total=12, etiqueta="Agenda diaria")
malos = []
with rd.Renderer() as r:
    for i in range(7):
        g.AUDITORIA.clear()
        g.png_t(r, "d1", "portada.html", dict(base, paleta=i), out / f"paleta-{i}.png", rd.VIEW_FEED, auditar="portada")
        items = g.AUDITORIA["d1"]["portada"]
        peor = min(items, key=lambda x: x["ratio"])
        print(i, "peor contraste", peor["ratio"], peor["t"])
        if peor["ratio"] < 4.5:
            malos.append(i)
ims = [Image.open(out / f"paleta-{i}.png").convert("RGB").resize((340, 425)) for i in range(7)]
S = Image.new("RGB", (7 * 348 + 8, 441), "#777")
for i, im in enumerate(ims):
    S.paste(im, (8 + i * 348, 8))
S.save(out / "hoja-paletas.png")
print("FALLAN:", malos)
