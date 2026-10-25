#!/usr/bin/env python3
"""Simula la cuadrícula del perfil de Instagram con portadas diarias (7 paletas rotatorias), carruseles de finde/mensual y portadas de reel.
   python simular_feed.py [AAAA-MM-DD hasta]   (por defecto: 29 días hasta el 2026-10-29)
Salida: ejemplos/feed-simulado/{perfil.png, cuadricula-completa.png, portadas/*.png}"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

import agenda as ag
import reel
import render as rd

SALIDA = ag.RAIZ / "ejemplos" / "feed-simulado"
PORT = SALIDA / "portadas"


def crop_feed(src, dst, alto):
    """Recorte de la cuadrícula de Instagram (3:4, escalado para cubrir la celda y centrado)."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w / h > 3 / 4:   # más ancho que 3:4 (p. ej. 4:5): se recortan los lados
        nw = round(h * 3 / 4); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
    else:               # más alto (reel 9:16): se recorta arriba y abajo
        nh = round(w * 4 / 3); y = (h - nh) // 2; im = im.crop((0, y, w, y + nh))
    im.resize((540, 720)).save(dst, quality=90)


def main(hasta, dias=29):
    PORT.mkdir(parents=True, exist_ok=True)
    fin = ag.a_fecha(hasta)
    rng = random.Random(7)
    # fotos de ejemplo para las portadas de reel: las del finde de test
    c = ag.dir_dia("2026-10-29", "finde")
    evs = ag.eventos_validos(ag.cargar_eventos(c)["eventos"]); rd.resolver_imagenes(evs, c)
    posts = []  # (fecha, orden, tipo, imagen)
    reels = []
    with rd.Renderer() as r:
        for i in range(dias):
            f = fin - timedelta(days=i)
            pal = rd.paleta(f)
            if f.day == 1:  # agenda mensual
                datos = dict(titulo=f"Lo más destacado de {ag.MESES[f.month - 1]}", subtitulo=f"{ag.MESES[f.month - 1]} {f.year}", total=rng.randint(8, 10), etiqueta="Agenda mensual", sufijo="imprescindibles", paleta=rd.paleta(f + timedelta(days=2)))
                p = PORT / f"{f}-mensual.png"; r.png("portada.html", datos, p, rd.VIEW_FEED); posts.append((f, 2, "carrusel", p))
            if f.weekday() == 3:  # jueves: reel + carrusel del finde
                datos = dict(titulo="Planes del finde", subtitulo=rd.titulos("finde", f, [])[1], total=rng.randint(12, 26), etiqueta="Viernes a domingo", sufijo="para el finde", paleta=rd.paleta(f + timedelta(days=3)))
                p = PORT / f"{f}-finde.png"; r.png("portada.html", datos, p, rd.VIEW_FEED); posts.append((f, 1, "carrusel", p))
                d, n, tot = reel.datos_reel(evs, "Planes del finde", datos["subtitulo"], f)
                q = PORT / f"{f}-reel.png"; reels.append((d, q)); posts.append((f, 0, "reel", q))
            datos = dict(titulo="Qué hacer hoy", subtitulo=ag.fecha_larga(f), total=rng.randint(4, 15), etiqueta="Agenda diaria", sufijo="en la ciudad", paleta=pal)
            p = PORT / f"{f}-diario.png"; r.png("portada.html", datos, p, rd.VIEW_FEED); posts.append((f, 3, "carrusel", p))
    for d, q in reels:  # fuera del Renderer anterior (Playwright no admite anidar)
        reel.capturar_portada(d, q)
    posts.sort(key=lambda x: (-x[0].toordinal(), x[1]))  # más reciente primero; el mismo día: reel, finde, mensual/diario
    miniaturas = []
    for f, _, tipo, src in posts:
        dst = PORT / (src.stem + "-grid.jpg"); crop_feed(src, dst, 0); miniaturas.append({"tipo": tipo, "img": dst.as_uri()})
    marca = ag.RAIZ / "marca"
    datos = {"avatar": (marca / "foto-perfil-320.png").as_uri(), "nombre": "Planes en Cádiz · Agenda diaria",
             "bio": "☀️ Qué hacer hoy en Cádiz, cada día a las 9:00\n🌊 Gratis · Finde · Lo mejor del mes\n👇 Comenta PLANES y te la mandamos",
             "destacadas": [{"t": t, "img": (marca / f"destacada-{k}.png").as_uri()} for t, k in (("Hoy", "hoy"), ("Finde", "finde"), ("Este mes", "mes"), ("Gratis", "gratis"))],
             "posts": miniaturas}
    with rd.Renderer() as r:
        pg = r.browser.new_page(viewport={"width": 1080, "height": 1200})
        pg.goto((rd.PLANTILLA / "feed.html").as_uri())
        pg.add_style_tag(url=(rd.PLANTILLA / "estilos.css").as_uri())
        pg.evaluate("d => render(d)", datos)
        pg.wait_for_timeout(1200)
        pg.screenshot(path=str(SALIDA / "cuadricula-completa.png"), full_page=True)
        pg.set_viewport_size({"width": 1080, "height": 2300})
        pg.screenshot(path=str(SALIDA / "perfil.png"), clip={"x": 0, "y": 0, "width": 1080, "height": 2300})
        pg.close()
    print(len(posts), "publicaciones simuladas")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2026-10-29")
