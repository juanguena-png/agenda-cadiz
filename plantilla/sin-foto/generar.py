#!/usr/bin/env python3
"""Regenera las imágenes genéricas por categoría (1200x1200 PNG) a partir de SVG sencillos."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from render import ruta_chromium

AQUI = Path(__file__).parent
# (fondo, color del icono, trazos del icono en un lienzo 100x100)
ICONOS = {
    "música": ("#14B8A6", '<path d="M38 70V30l34-8v40" /><circle cx="30" cy="70" r="9"/><circle cx="64" cy="62" r="9"/>'),
    "teatro": ("#7C3AED", '<path d="M20 28h34v22a17 17 0 0 1-34 0z"/><path d="M46 44h34v22a17 17 0 0 1-34 0z"/><path d="M30 40q4 4 8 0M58 58q4 4 8 0"/>'),
    "infantil": ("#F97316", '<circle cx="50" cy="40" r="22"/><path d="M50 62v26M50 74l8 6"/>'),
    "exposición": ("#E11D48", '<rect x="22" y="24" width="56" height="44" rx="3"/><path d="M30 60l14-16 10 10 8-8 10 14"/><path d="M40 78h20"/>'),
    "deporte": ("#16A34A", '<circle cx="50" cy="50" r="30"/><path d="M50 20v60M20 50h60M29 29q21 21 42 0M29 71q21-21 42 0"/>'),
    "gastronomía": ("#CA8A04", '<path d="M32 22v22a6 6 0 0 0 12 0V22M38 22v56M66 22c-8 8-8 30 0 34v22"/>'),
    "fiesta": ("#DB2777", '<path d="M24 78l14-40 28 28z"/><path d="M52 30l4-10M66 38l10-4M62 52l12 2"/><circle cx="76" cy="22" r="2"/><circle cx="84" cy="44" r="2"/>'),
    "otros": ("#0EA5E9", '<path d="M50 20l8 20 22 2-17 14 6 22-19-12-19 12 6-22-17-14 22-2z"/>'),
}


def svg(fondo, trazos):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="0 0 100 100">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{fondo}"/><stop offset="1" stop-color="#0B2A4A"/></linearGradient></defs>
<rect width="100" height="100" fill="url(#g)"/><circle cx="82" cy="18" r="22" fill="#FFC93C" opacity=".9"/>
<g fill="none" stroke="#FFF8EA" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">{trazos}</g></svg>'''


with sync_playwright() as p:
    exe = ruta_chromium()
    b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 1200})
    for cat, (fondo, trazos) in ICONOS.items():
        pg.set_content(f'<body style="margin:0">{svg(fondo, trazos)}</body>')
        pg.screenshot(path=str(AQUI / f"{cat}.png"))
        print("ok", cat)
    b.close()
