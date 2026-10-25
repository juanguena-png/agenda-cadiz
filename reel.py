#!/usr/bin/env python3
"""Reel «Planes del finde» (vertical 1080x1920, 15-45 s). Plantilla ÚNICA: plantilla/reel.html (animación con Web Animations API).

Cada fotograma se obtiene fijando la línea de tiempo en un instante (window.seek(t)) y capturando la página con Chromium; ffmpeg ensambla los
fotogramas y mezcla la música (normalizada de volumen, con fundido de entrada y salida). Estructura fija: intro (3 s) + 1 escena por evento
(4,2 s, para dar tiempo a leer) + cierre con llamada a la acción (2,8 s); transiciones con el «sol» de la marca.

  python reel.py --fecha AAAA-MM-DD     # usa posts/FECHA/finde/eventos.json (FECHA = jueves de publicación)
  python reel.py --demo                 # datos de ejemplo -> ejemplos/reel-demo.mp4
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import agenda as ag
import render as rd

W, H, FPS = 1080, 1920, 30
INTRO, POR_EVENTO, OUTRO = 3.0, 4.2, 2.8
MIN_S, MAX_S = 15.0, 45.0
PISTAS_JSON = ag.RAIZ / "musica" / "pistas.json"


# ---------------------------------------------------------------- música
def pistas_validas():
    """Pistas de musica/ que figuran en licencias.md Y están marcadas para reel en pistas.json (energía/volumen adecuados)."""
    lic = (ag.RAIZ / "musica" / "licencias.md").read_text(encoding="utf-8") if (ag.RAIZ / "musica" / "licencias.md").exists() else ""
    meta = ag.cargar_json(PISTAS_JSON, {})
    out = []
    for p in sorted((ag.RAIZ / "musica").glob("*.*")):
        if p.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a", ".flac") and p.name in lic and meta.get(p.name, {}).get("reel", True):
            out.append(p)
    return out


def elegir_pista(fecha):
    ps = pistas_validas()
    return ps[ag.a_fecha(fecha).toordinal() % len(ps)] if ps else None  # rotación determinista


# ---------------------------------------------------------------- plan
def planificar(n_eventos):
    """(eventos mostrados, segundos por evento, duración total). Entre 15 y 45 s (4,2 s de lectura por evento; máx. 9 eventos)."""
    maxn = int((MAX_S - INTRO - OUTRO) // POR_EVENTO)
    n = max(1, min(n_eventos, maxn))
    por = POR_EVENTO
    if INTRO + n * por + OUTRO < MIN_S:
        por = (MIN_S - INTRO - OUTRO) / n  # con pocos eventos cada escena dura más (siempre ≥ 15 s en total)
    return n, por, INTRO + n * por + OUTRO


def dias_finde(fecha):
    f = ag.a_fecha(fecha)
    vie = f + timedelta(days=(4 - f.weekday()) % 7) if f.weekday() <= 4 else f + timedelta(days=(4 - f.weekday()) % 7)
    return [{"abr": a, "num": (vie + timedelta(days=i)).day, "iso": (vie + timedelta(days=i)).isoformat()} for i, a in enumerate(("VIE", "SÁB", "DOM"))]


def fotos_portada(eventos):
    """Hasta 3 imágenes distintas para la portada: primero las fotos oficiales, luego las ilustraciones propias."""
    ordenadas = sorted(eventos, key=lambda e: bool((e.get("imagen") or {}).get("generada") or (e.get("imagen") or {}).get("generica")))
    vistas, out = set(), []
    for e in ordenadas:
        u = (e.get("imagen") or {}).get("ruta_abs")
        if u and u not in vistas:
            vistas.add(u); out.append(u)
    return out[:3]


def datos_reel(eventos, titulo, sub, fecha):
    eventos = ag.ordenar(eventos, por_fecha=True)
    n, por, total = planificar(len(eventos))
    marca = ag.cargar_json(ag.RAIZ / "marca.json", {}) or {}
    return {"tema": marca.get("tema", "d1"), "prefijo": marca.get("prefijo", "Planes en"), "ciudad": marca.get("ciudad", "Cádiz"), "usuario": marca.get("usuario", "@planesencadiz"),
            "paleta": rd.paleta(fecha), "layout": (ag.a_fecha(fecha).toordinal() % 3) + 1, "fondo": ["noche", "sol", "mar"][(ag.a_fecha(fecha).toordinal() // 3) % 3],
            "fotos": fotos_portada(eventos), "titulo": titulo, "subtitulo": sub, "etiqueta": "Viernes a domingo", "sufijo": "para el finde", "total": len(eventos),
            "eventos": eventos[:n], "intro": INTRO, "por_evento": por, "outro": OUTRO, "total_s": total, "dias": dias_finde(fecha)}, n, total


# ---------------------------------------------------------------- render
def capturar(datos, salida, pista=None, log=print):
    total = datos["total_s"]
    n_fot = int(round(total * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-"]
    if pista:
        cmd += ["-i", str(pista)]
        cmd += ["-filter_complex", f"[1:a]atrim=0:{total:.2f},asetpts=PTS-STARTPTS,loudnorm=I=-15:TP=-1.5:LRA=9,afade=t=in:st=0:d=0.8,afade=t=out:st={total - 1.8:.2f}:d=1.8[a]",
                "-map", "0:v", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), "-t", f"{total:.2f}", "-movflags", "+faststart", str(salida)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with rd.Renderer() as r:
        pg = r.browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto((rd.PLANTILLA / "reel.html").as_uri())
        pg.add_style_tag(url=(rd.PLANTILLA / "temas" / f"{datos['tema']}.css").as_uri())
        pg.evaluate("d => render(d)", datos)
        pg.wait_for_timeout(500)
        for i in range(n_fot):
            pg.evaluate("t => seek(t)", i / FPS)
            ff.stdin.write(pg.screenshot(type="jpeg", quality=93))
            if i % 150 == 0:
                log(f"  fotograma {i}/{n_fot}")
        pg.close()
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg falló")


def capturar_portada(datos, destino):
    """Portada del reel (1080x1920) = la composición de la intro con todos los elementos ya animados. Se sube como cover_url."""
    with rd.Renderer() as r:
        pg = r.browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto((rd.PLANTILLA / "reel.html").as_uri())
        pg.add_style_tag(url=(rd.PLANTILLA / "temas" / f"{datos['tema']}.css").as_uri())
        pg.evaluate("d => render(d)", datos)
        pg.wait_for_timeout(500)
        pg.evaluate("t => seek(t)", datos["intro"] - 0.55)
        pg.screenshot(path=str(destino), type="png")
        pg.close()


def hacer_reel(eventos, titulo, sub, fecha, salida, log=print):
    datos, n, total = datos_reel(eventos, titulo, sub, fecha)
    pista = elegir_pista(fecha)
    capturar(datos, salida, pista, log)
    portada = Path(salida).parent / "portada.png"
    capturar_portada(datos, portada)
    return {"duracion": round(total, 1), "eventos_en_reel": n, "eventos_total": len(eventos), "musica": pista.name if pista else "sin-musica", "portada": f"layout {datos['layout']} · fondo {datos['fondo']}"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        base = ag.RAIZ / "ejemplos"
        rd.hacer_fotos_demo(base / "_demo")
        evs = rd.resolver_imagenes(rd.demo_eventos(8, True), base)
        for i, e in enumerate(evs):
            e["fecha"] = ["2026-10-30", "2026-10-31", "2026-11-01"][i % 3]
        print(hacer_reel(evs, "Planes del finde", "30 oct – 1 nov", "2026-10-29", base / "reel-demo.mp4"))
    else:
        carpeta = ag.dir_dia(a.fecha, "finde")
        evs = ag.eventos_validos(ag.cargar_eventos(carpeta)["eventos"])
        if len(evs) < ag.MIN_EVENTOS:
            ag.salir("0 eventos verificados: no se genera el reel (regla 9: añade eventos o «Siempre abierto»).", 0)
        rd.resolver_imagenes(evs, carpeta)
        titulo, sub = rd.titulos("finde", a.fecha, evs)
        out = carpeta / "reel"
        out.mkdir(exist_ok=True)
        info = hacer_reel(evs, titulo, sub, a.fecha, out / "reel.mp4")
        ag.guardar_json(out / "reel.json", info)
        print(info)
