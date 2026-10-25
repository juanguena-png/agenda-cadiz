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

MIN_ANCHO = 240  # carteles oficiales pequeños (p. ej. 262x350 de la Casa de Iberoamérica) valen: se muestran enteros (contain) sobre fondo desenfocado
MAX_LADO = 1600
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}
# Dominios NO oficiales (jamás se usan como origen de imagen)
NO_OFICIAL = ("instagram.", "facebook.", "fbcdn.", "twitter.", "x.com", "tiktok.", "youtube.", "ytimg.", "eventbrite", "evbuc.", "ticketmaster",
              "entradium", "giglon", "diariodecadiz", "lavozdigital", "cadizdirecto", "diariobahiadecadiz", "vivacadiz", "andaluciainformacion",
              "hoycadiz", "guiadecadiz", "google.", "gstatic.", "wp.com", "gravatar")
# Se aplica solo al nombre/ruta del archivo (los dominios de redes sociales ya se rechazan en NO_OFICIAL). Ojo: «instagram» NO se excluye en la ruta:
# muchos carteles oficiales se llaman «…-post-instagram-vertical.jpg» (Casa de Iberoamérica).
EXCLUIR = re.compile(r"logo|icon|favicon|sprite|avatar|cookies|mapacontenidos|placeholder|share|/themes/|/modules/|iso-face|/img/front/|/assets/|cab-pagina-informativa|header_page", re.I)
# En el nivel «logo» sí se admiten logotipos (del organizador, recinto o festival), pero no iconos ni elementos de la web
EXCLUIR_LOGO = re.compile(r"icon|favicon|sprite|avatar|cookies|mapacontenidos|placeholder|share|/themes/|/modules/|iso-face|/assets/|cab-pagina-informativa|header_page|facebook|twitter|instagram\.png|whatsapp", re.I)
# CDN de los constructores de webs: sirven las imágenes de la web del propio organizador (p. ej. Wix → static.wixstatic.com)
CDN_PROPIOS = ("wixstatic.com", "squarespace-cdn.com", "squarespace.com", "cdn.shopify.com", "llt-services.com")  # llt-services = CDN de las webs oficiales de clubes (cadizcf.com)


def original_drupal(url):
    """Drupal sirve miniaturas en /styles/<estilo>/public/...; el original está sin '/styles/<estilo>/public'."""
    return re.sub(r"/styles/[^/]+/public/", "/", url).split("?")[0]


# Redes sociales: nunca se descargan imágenes de ahí (scraping de IG/FB prohibido por CLAUDE.md y por las normas de Meta)
REDES = ("instagram.", "facebook.", "fbcdn.", "cdninstagram", "twitter.", "x.com", "twimg.", "tiktok.", "threads.net")


def es_oficial(url_imagen, url_pagina, nivel="oficial"):
    host = urlparse(url_imagen).netloc.lower()
    if nivel != "oficial":  # «cualquiera» y «logo»: cualquier web relacionada con el evento (prensa, entradas, agregadores…), salvo redes sociales
        return not any(x in host for x in REDES)
    if any(x in host for x in NO_OFICIAL):
        return False
    h_p = urlparse(url_pagina).netloc.lower()
    raiz = lambda h: ".".join(h.split(".")[-2:])
    if any(host.endswith(c) for c in CDN_PROPIOS) and not any(x in h_p for x in NO_OFICIAL):
        return True  # la página es del organizador y la imagen sale del CDN de su constructor de webs
    return raiz(host) == raiz(h_p)  # misma web que la página oficial del evento


def candidatas(html, url_pagina, nivel="oficial"):
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
        excl = EXCLUIR_LOGO if nivel == "logo" else EXCLUIR
        if o not in vistos and es_oficial(o, url_pagina, nivel) and not excl.search(urlparse(o).path):
            vistos.add(o); res.append(o)
            if u != o and u not in vistos:
                res.append(u)  # la miniatura como respaldo si el original no existe
    return res


def parece_logo(im):
    """Heurística: un logotipo tiene gran parte transparente o casi blanca y pocos colores; un cartel o una foto no."""
    try:
        peq = im.convert("RGBA").resize((96, 96))
        px = list(peq.getdata())
        transp = sum(1 for p in px if p[3] < 40) / len(px)
        blanco = sum(1 for p in px if p[3] >= 40 and min(p[:3]) > 235) / len(px)
        colores = len({(p[0] // 32, p[1] // 32, p[2] // 32) for p in px if p[3] >= 40})
        return transp > 0.35 or (blanco + transp > 0.55 and colores < 25)
    except Exception:
        return False


def descargar(url, destino, referer=None, permitir_logo=False):
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
    if parece_logo(im) and not permitir_logo:
        return {"descartada": "parece un logotipo (fondo transparente/blanco liso), no un cartel del evento", "url": url}
    if im.height and im.width / im.height > 3.5:
        return {"descartada": f"banner genérico (proporción {im.width}x{im.height})", "url": url}
    if im.mode in ("RGBA", "LA", "P"):
        fondo = Image.new("RGB", im.size, (255, 255, 255))
        im = im.convert("RGBA"); fondo.paste(im, mask=im.split()[-1]); im = fondo
    else:
        im = im.convert("RGB")
    im.thumbnail((MAX_LADO, MAX_LADO))
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, "JPEG", quality=88)
    return {"ancho": im.width, "alto": im.height, "url": url}


def html_con_navegador(url):
    """HTML de una página con Chromium real (para webs que devuelven 403 a los scripts, p. ej. cadizcf.com)."""
    try:
        import render as rd
        with rd.Renderer() as r:
            ctx = r.browser.new_context(user_agent=UA["User-Agent"], locale="es-ES")
            pg = ctx.new_page()
            resp = pg.goto(url, wait_until="networkidle", timeout=45000)
            return pg.content() if resp and resp.status < 400 else None
    except Exception:
        return None


def buscar_y_descargar(url_pagina, id_, carpeta, html=None, nivel="oficial"):
    """Prueba las imágenes candidatas de la página en orden hasta que una sea válida. Devuelve el bloque `imagen` de eventos.json o None."""
    if nivel != "logo" and urlparse(url_pagina).path in ("", "/"):
        return {"error": "la fuente es la página de inicio, no la ficha del evento: sus imágenes no son del evento"}
    try:
        r_ = None if html else requests.get(url_pagina, headers=UA, timeout=30)
        if r_ is not None and r_.status_code in (403, 429, 503):
            html = html_con_navegador(url_pagina)  # la web bloquea los scripts: se lee con un navegador real (Chromium)
        html = html or (r_.text if r_ is not None else None)
        if not html:
            return {"error": "no se pudo leer la página"}
    except requests.RequestException:
        html = html_con_navegador(url_pagina)
        if not html:
            return None
    destino = carpeta / "img" / f"{id_}.jpg"
    motivos = []
    for u in candidatas(html, url_pagina, nivel)[:8]:
        res = descargar(u, destino, referer=url_pagina, permitir_logo=(nivel == "logo"))
        if res and "ancho" in res:
            host = urlparse(url_pagina).netloc
            return {"archivo": f"img/{id_}.jpg", "url_origen": u, "fuente": host, "pagina": url_pagina, "ancho": res["ancho"], "alto": res["alto"], "alt_text": "", "tipo_imagen": nivel}
        if res:
            motivos.append(res["descartada"])
    return {"error": "; ".join(motivos) or "sin imagen oficial descargable"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--fecha", default=ag.hoy().isoformat())
    ap.add_argument("--nivel", choices=["oficial", "cualquiera", "logo"], default="oficial",
                    help="oficial: web del organizador/Ayuntamiento · cualquiera: cualquier web relacionada con el evento (prensa, entradas, agregadores; nunca redes sociales) · logo: admite logotipos")
    a = ap.parse_args()
    print(buscar_y_descargar(a.url, a.id, ag.dir_dia(a.fecha), nivel=a.nivel))
