#!/usr/bin/env python3
"""Cartel PROPIO de un partido del Cádiz CF en casa (la web oficial no publica carteles de partido):
fondo de marca + escudos oficiales de ambos equipos (leídos de la ficha oficial del partido en cadizcf.com) + competición, fecha, hora y estadio.
Nombra los equipos (uso identificativo de los escudos); no imita ningún cartel oficial.

  python cartel_partido.py URL_FICHA_OFICIAL [salida.png]
"""
import re
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

import agenda as ag
import render as rd

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def datos_ficha(url):
    """(local, visitante, bytes_escudo_local, bytes_escudo_visitante) leídos de la ficha oficial con Chromium (la web da 403 a los scripts)."""
    with rd.Renderer() as r:
        ctx = r.browser.new_context(user_agent=UA, locale="es-ES")
        pg = ctx.new_page()
        pg.goto(url, wait_until="networkidle", timeout=45000)
        titulo = (re.findall(r'property="og:title"[^>]*content="([^"]+)"', pg.content()) or [""])[0]
        m = re.match(r"(.+?) vs (.+?) - ", titulo)
        if not m:
            raise ValueError("no es la ficha de un partido")
        local, visitante = m.groups()
        imgs = pg.evaluate("Array.from(document.images).map(i=>[i.currentSrc||i.src,i.alt,i.getBoundingClientRect().width|0])")
        esc = lambda nombre: next(s for s, alt, w in imgs if alt.strip() == nombre and w > 50)
        # los escudos se descargan con el propio navegador (misma sesión y Referer que la web oficial)
        cuerpo = lambda u: ctx.request.get(u, headers={"Referer": url}).body()
        return local, visitante, cuerpo(esc(local)), cuerpo(esc(visitante))


def generar(ev, carpeta):
    """Genera img/<id>-cartel.png y devuelve el bloque `imagen` de eventos.json."""
    url = next((f["url"] for f in ev.get("fuentes", []) if "cadizcf.com/partidos/" in f.get("url", "")), None)
    if not url:
        raise ValueError("el evento no tiene la ficha oficial cadizcf.com/partidos/ entre sus fuentes")
    local, visitante, e1, e2 = datos_ficha(url)
    destino = Path(carpeta) / "img"
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, datos in (("local", e1), ("visitante", e2)):
        Image.open(BytesIO(datos)).convert("RGBA").save(destino / f"{ev['id']}-escudo-{nombre}.png")
    f = ag.a_fecha(ev["fecha"])
    cuando = f"{ag.fecha_larga(ev['fecha']).capitalize()} · {ev.get('hora_inicio') or ''}".strip(" ·")
    comp = re.sub(r"^Cádiz CF [–-] .+? · ", "", ev["nombre"]) or "LaLiga Hypermotion"
    salida = destino / f"{ev['id']}-cartel.png"
    with rd.Renderer() as r:
        r.png("partido.html", {"competicion": comp, "local": local, "visitante": visitante, "cuando": cuando, "lugar": ev.get("lugar", "Estadio Nuevo Mirandilla"),
                               "escudo_local": (destino / f"{ev['id']}-escudo-local.png").resolve().as_uri(),
                               "escudo_visitante": (destino / f"{ev['id']}-escudo-visitante.png").resolve().as_uri()}, salida, {"width": 1080, "height": 1080})
    return {"archivo": f"img/{ev['id']}-cartel.png", "fuente": "Cartel propio de Planes en Cádiz con los escudos oficiales de la web del Cádiz CF", "generada": True,
            "alt_text": f"Cartel del partido {local} contra {visitante}: {comp}, {cuando}, {ev.get('lugar', '')}", "ajuste": "cover"}


if __name__ == "__main__":
    ev = {"id": "prueba-partido", "nombre": "Cádiz CF – Real Oviedo · LALIGA HYPERMOTION J13", "fecha": "2026-11-07", "hora_inicio": "16:15", "lugar": "Estadio Nuevo Mirandilla (JP Financial Estadio)",
          "fuentes": [{"url": sys.argv[1]}]}
    print(generar(ev, Path(sys.argv[2]) if len(sys.argv) > 2 else ag.RAIZ / "ejemplos"))
