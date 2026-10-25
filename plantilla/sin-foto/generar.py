#!/usr/bin/env python3
"""Regenera las imágenes genéricas por categoría (1200x1200 PNG) con la identidad D1 · Mediterráneo luminoso."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "propuestas-marca"))
import generar as g  # noqa: E402
import render as rd  # noqa: E402

with rd.Renderer() as r:
    pg = r.browser.new_page(viewport={"width": 1200, "height": 1200})
    for i, (cat, trazos) in enumerate(g.ICONOS.items()):
        pg.set_content(f'<body style="margin:0">{g.svg_generica("d1", i, trazos)}</body>')
        pg.screenshot(path=str(Path(__file__).parent / f"{cat}.png"))
        print("ok", cat)
