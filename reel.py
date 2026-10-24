#!/usr/bin/env python3
"""Reel vertical 1080x1920 de 15-30 s (ffmpeg) a partir de la portada y los eventos del finde.

  python reel.py --fecha AAAA-MM-DD            # usa posts/FECHA/finde/{eventos.json,carrusel/}
  python reel.py --demo                        # datos de ejemplo -> ejemplos/reel-demo.mp4
La música sale de musica/ (solo pistas listadas en musica/licencias.md con licencia confirmada). Sin pistas -> reel mudo.
"""
import argparse
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import agenda as ag
import render as rd

W, H, FPS = 1080, 1920, 30
T_PORTADA, T_EVENTO, T_TRANS = 3.0, 2.6, 0.5
MIN_S, MAX_S = 15.0, 30.0


def pistas_validas():
    """Pistas de musica/ que figuran en licencias.md (una fila por archivo, con licencia)."""
    lic = ag.RAIZ / "musica" / "licencias.md"
    if not lic.exists():
        return []
    texto = lic.read_text(encoding="utf-8")
    return [p for p in sorted((ag.RAIZ / "musica").glob("*.*")) if p.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a", ".flac") and p.name in texto]


def elegir_pista(fecha):
    ps = pistas_validas()
    return ps[ag.a_fecha(fecha).toordinal() % len(ps)] if ps else None  # rotación determinista


def planificar(n_eventos):
    """Cuántos eventos caben en 15-30 s. Devuelve (nº de eventos mostrados como clips, duración total)."""
    max_clips = int((MAX_S - T_PORTADA) // (T_EVENTO - T_TRANS * 0) )
    clips = max(1, min(n_eventos, max_clips))
    dur = T_PORTADA + clips * T_EVENTO
    return clips, max(MIN_S, min(MAX_S, dur))


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:])


def fotogramas(r, eventos, titulo, sub, var, tmp):
    """Cada clip es una story-nocturna-like: usa story.html (1080x1920) -> PNG; portada en versión vertical."""
    pngs = []
    p = tmp / "p0.png"
    r.png("portada.html", {"titulo": titulo, "subtitulo": sub, "total": len(eventos), "variante": var}, p, rd.VIEW_FEED)
    # la portada es 1080x1350: se pone sobre fondo 1080x1920 en ffmpeg
    pngs.append((p, T_PORTADA, True))
    for i, ev in enumerate(eventos):
        q = tmp / f"e{i}.png"
        r.png("story.html", {"evento": ev, "fecha_larga": ag.fecha_larga(ev["fecha"])}, q, rd.VIEW_STORY)
        pngs.append((q, T_EVENTO, False))
    return pngs


def rotulo_animado(total):
    """Texto que entra deslizando en cada clip de evento (zona segura superior libre) y una barra de progreso."""
    f = subprocess.run(["fc-match", "-f", "%{file}", "Inter:bold"], capture_output=True, text=True).stdout
    if not f or not Path(f).exists():
        return None
    base = "fontfile=%s:fontcolor=0xFFC93C:fontsize=46:borderw=0" % f
    return (f"drawtext={base}:text='AGENDA CÁDIZ  ·  PLANES DEL FINDE':x='if(lt(t,0.9),-tw+(tw+80)*t/0.9,80)':y=120:enable='between(t,0,{total:.2f})',"
            f"drawbox=x=0:y=1904:w='iw*t/{total:.2f}':h=16:color=0xFFC93C:t=fill")


def componer(pngs, salida, pista=None):
    """Cadena xfade entre clips con zoom suave (Ken Burns) y fundido final; música con fade in/out."""
    entradas, filtros, ult = [], [], None
    total = 0.0
    for i, (png, dur, es_portada) in enumerate(pngs):
        d = dur + T_TRANS
        entradas += ["-loop", "1", "-t", f"{d}", "-i", str(png)]
        fondo = f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if not es_portada else \
            f"[{i}:v]pad={W}:{H}:0:285:color=0x0B2A4A"
        filtros.append(f"{fondo},zoompan=z='min(zoom+0.0006,1.06)':d={int(d * FPS)}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v{i}]")
    ult = "v0"
    t = pngs[0][1]
    for i in range(1, len(pngs)):
        filtros.append(f"[{ult}][v{i}]xfade=transition={'slideleft' if i % 2 else 'fade'}:duration={T_TRANS}:offset={t - T_TRANS + T_TRANS:.2f}[x{i}]")
        ult = f"x{i}"
        t += pngs[i][1]
    total = t
    rotulo = rotulo_animado(total)
    if rotulo:
        filtros.append(f"[{ult}]{rotulo}[{ult}t]")
        ult = f"{ult}t"
    filtros.append(f"[{ult}]fade=t=out:st={total - 0.6:.2f}:d=0.6[vf]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + entradas
    if pista:
        cmd += ["-i", str(pista)]
        filtros.append(f"[{len(pngs)}:a]atrim=0:{total:.2f},afade=t=in:d=1,afade=t=out:st={total - 1.5:.2f}:d=1.5[a]")
    cmd += ["-filter_complex", ";".join(filtros), "-map", "[vf]"] + (["-map", "[a]", "-c:a", "aac", "-b:a", "160k"] if pista else []) + \
           ["-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(salida)]
    sh(cmd)
    return total


def hacer_reel(eventos, titulo, sub, fecha, salida, var="A"):
    eventos = ag.ordenar(eventos, por_fecha=True)
    clips, _ = planificar(len(eventos))
    # Con muchos eventos el reel muestra un clip por evento hasta el máximo; el resto queda en el carrusel (aviso en el caption)
    elegidos = eventos[:clips]
    with tempfile.TemporaryDirectory() as tmp, rd.Renderer() as r:
        pngs = fotogramas(r, elegidos, titulo, sub, var, Path(tmp))
        dur = componer(pngs, salida, elegir_pista(fecha))
    return {"duracion": round(dur, 1), "eventos_en_reel": clips, "eventos_total": len(eventos), "musica": (elegir_pista(fecha) or Path("sin-musica")).name}


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
        print(hacer_reel(evs, "Planes del finde en Cádiz", "30 oct – 1 nov", "2026-10-29", base / "reel-demo.mp4"))
    else:
        carpeta = ag.dir_dia(a.fecha, "finde")
        evs = ag.eventos_validos(ag.cargar_eventos(carpeta)["eventos"])
        if len(evs) < 2:
            ag.salir("Menos de 2 eventos verificados: no se genera el reel.", 0)
        rd.resolver_imagenes(evs, carpeta)
        titulo, sub = rd.titulos("finde", a.fecha, evs)
        out = carpeta / "reel"
        out.mkdir(exist_ok=True)
        info = hacer_reel(evs, titulo, sub, a.fecha, out / "reel.mp4", rd.variante(a.fecha))
        ag.guardar_json(out / "reel.json", info)
        print(info)
