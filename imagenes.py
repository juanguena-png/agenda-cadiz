#!/usr/bin/env python3
"""Imágenes OFICIALES de eventos: búsqueda en la página del propio organizador/recinto/Ayuntamiento, descarga y validación.

Regla 7 (CLAUDE.md): solo imágenes de la web oficial del organizador, del recinto o del Ayuntamiento/Turismo; nunca de agregadores,
prensa ni redes sociales. Si no hay imagen o no se puede descargar con calidad (>= MIN_ANCHO px), el evento usa la genérica de su categoría.

  python imagenes.py --url URL_DETALLE --id ID --fecha AAAA-MM-DD   # busca, descarga y registra la mejor imagen oficial
"""
import argparse
import re
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image

import agenda as ag

MIN_ANCHO = 400
MAX_LADO = 1600
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}
# Dominios NO oficiales (jamás se usan como origen de imagen)
NO_OFICIAL = ("instagram.", "facebook.", "fbcdn.", "twitter.", "x.com", "tiktok.", "youtube.", "ytimg.", "eventbrite", "evbuc.", "ticketmaster",
              "entradium", "giglon", "diariodecadiz", "lavozdigital", "cadizdirecto", "diariobahiadecadiz", "vivacadiz", "andaluciainformacion",
              "hoycadiz", "guiadecadiz", "google.", "gstatic.", "wp.com", "gravatar")
EXCLUIR = re.compile(r"logo|icon|favicon|sprite|avatar|cookies|mapacontenidos|placeholder|share|/themes/|/modules/|facebook|twitter|instagram|iso-face|/img/front/|/assets/", re.I)


def original_drupal(url):
    """Drupal sirve miniaturas en /styles/<estilo>/public/...; el original está sin '/styles/<estilo>/public'."""
    return re.sub(r"/styles/[^/]+/public/", "/", url).split("?")[0]


def es_oficial(url_imagen, url_pagina):
    host = urlparse(url_imagen).netloc.lower()
    if any(x in host for x in NO_OFICIAL):
        return False
    h_p = urlparse(url_pagina).netloc.lower()
    raiz = lambda h: ".".join(h.split(".")[-2:])
    return raiz(host) == raiz(h_p)  # misma web que la página oficial del evento


def candidatas(html, url_pagina):
    """URLs de imagen del contenido de la página (og:image primero, luego imágenes del cuerpo), solo del mismo dominio oficial."""
    s = BeautifulSoup(html, "lxml")
    out = []
    for m in s.find_all("meta", attrs={"property": re.compile("og:image|twitter:image")}):
        if m.get("content"):
            out.append(urljoin(url_pagina, m["content"]))
    cuerpo = s.select_one("main, article, #content, .content, body") or s
    for img in cuerpo.find_all("img"):
        src = img.get("data-src") or img.get("src") or ""
        if src and not EXCLUIR.search(src) and not src.startswith("data:"):
            out.append(urljoin(url_pagina, src))
    vistos, res = set(), []
    for u in out:
        o = original_drupal(u) if "/styles/" in u else u
        if o not in vistos and es_oficial(o, url_pagina) and not EXCLUIR.search(urlparse(o).path):
            vistos.add(o); res.append(o)
            if u != o and u not in vistos:
                res.append(u)  # la miniatura como respaldo si el original no existe
    return res


def descargar(url, destino, referer=None):
    """Descarga y valida (imagen real, ancho >= MIN_ANCHO). Guarda JPEG. Devuelve dict o None."""
    try:
        r = requests.get(url, headers={**UA, **({"Referer": referer} if referer else {})}, timeout=30)
        if r.status_code != 200 or "image" not in r.headers.get("content-type", ""):
            return None
        im = Image.open(BytesIO(r.content))
        im.load()
    except Exception:
        return None
    if im.width < MIN_ANCHO:
        return {"descartada": f"ancho {im.width}px < {MIN_ANCHO}px", "url": url}
    if im.mode in ("RGBA", "LA", "P"):
        fondo = Image.new("RGB", im.size, (255, 255, 255))
        im = im.convert("RGBA"); fondo.paste(im, mask=im.split()[-1]); im = fondo
    else:
        im = im.convert("RGB")
    im.thumbnail((MAX_LADO, MAX_LADO))
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, "JPEG", quality=88)
    return {"ancho": im.width, "alto": im.height, "url": url}


def buscar_y_descargar(url_pagina, id_, carpeta, html=None):
    """Prueba las imágenes candidatas de la página en orden hasta que una sea válida. Devuelve el bloque `imagen` de eventos.json o None."""
    try:
        html = html or requests.get(url_pagina, headers=UA, timeout=30).text
    except requests.RequestException:
        return None
    destino = carpeta / "img" / f"{id_}.jpg"
    motivos = []
    for u in candidatas(html, url_pagina)[:8]:
        res = descargar(u, destino, referer=url_pagina)
        if res and "ancho" in res:
            host = urlparse(url_pagina).netloc
            return {"archivo": f"img/{id_}.jpg", "url_origen": u, "fuente": host, "pagina": url_pagina, "ancho": res["ancho"], "alto": res["alto"], "alt_text": ""}
        if res:
            motivos.append(res["descartada"])
    return {"error": "; ".join(motivos) or "sin imagen oficial descargable"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--fecha", default=ag.hoy().isoformat())
    a = ap.parse_args()
    print(buscar_y_descargar(a.url, a.id, ag.dir_dia(a.fecha)))
