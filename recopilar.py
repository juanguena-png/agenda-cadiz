#!/usr/bin/env python3
"""Recopila candidatos de las fuentes de fuentes.json -> posts/FECHA/candidatos.json + registros/fuentes.log.

Este script SOLO reúne material en bruto. La verificación de Cádiz capital, el contraste entre fuentes, la
redacción con palabras propias y la creación de eventos.json las hace el agente (ver CLAUDE.md).
Nunca scrapea Instagram ni Facebook.

  python recopilar.py [--fecha AAAA-MM-DD] [--hasta AAAA-MM-DD]   # recopila
  python recopilar.py --verificar                                  # solo comprueba qué URLs responden
"""
import argparse
from datetime import date, timedelta
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import agenda as ag

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AgendaCadizBot/1.0 (+agenda de Cádiz; contacto en README)"}
MESES = {m: i + 1 for i, m in enumerate(ag.MESES)}
HOSTS_PROHIBIDOS = ("instagram.com", "facebook.com", "fb.com")
# Dominios caducados/secuestrados o peligrosos: NUNCA se visitan (p. ej. sohoalternative.es sirve spam de apuestas)
DOMINIOS_BLOQUEADOS = ("sohoalternative.es",)


def descargar(url):
    if any(h in urlparse(url).netloc for h in HOSTS_PROHIBIDOS):
        raise ValueError("Prohibido hacer scraping de Instagram/Facebook")
    if any(urlparse(url).netloc.endswith(h) for h in DOMINIOS_BLOQUEADOS):
        raise ValueError("Dominio bloqueado (no seguro)")
    r = requests.get(url, headers=UA, timeout=25)
    r.raise_for_status()
    if "charset" not in r.headers.get("content-type", "").lower():
        # laciudad.cadiz.es sirve UTF-8 válido o cp1252 sin declararlo bien
        try:
            r.encoding = "utf-8"
            r.content.decode("utf-8")
        except UnicodeDecodeError:
            r.encoding = "cp1252"
    return r


def limpio(html, limite=6000):
    s = BeautifulSoup(html, "lxml")
    for t in s(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        t.decompose()
    return re.sub(r"\s+", " ", s.get_text(" ")).strip()[:limite]


def a_iso(dia, mes, ano_pagina=None, hoy=None):
    hoy = hoy or ag.hoy()
    ano = ano_pagina or hoy.year
    d = date(ano, mes, dia)
    if not ano_pagina and d < hoy - timedelta(days=60):
        d = date(ano + 1, mes, dia)
    return d


def _fechas(texto):
    return [date(int(a), int(m), int(d)) for d, m, a in re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto or "")]


def _hora(texto):
    t = (texto or "").lower()
    m = re.search(r"inicio\D{0,15}(\d{1,2})[:.](\d{2})", t) or re.search(r"(\d{1,2})[:.](\d{2})\s*h", t) or re.search(r"\b(\d{1,2})\s*h\b", t)
    if not m:
        return None
    return f"{int(m.group(1)):02d}:{(m.group(2) if m.lastindex > 1 else '00')}"


def detalle_ayto(url):
    """Ficha de evento del Ayuntamiento/Turismo (Drupal): campos con etiqueta + texto + imagen."""
    r = requests.get(url, headers=IMG_UA, timeout=25)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "lxml")
    campos = {}
    for f in s.select(".field"):
        lab, val = f.select_one(".field-label"), f.select_one(".field-items, .field-item")
        if lab and val:
            campos[lab.get_text(strip=True).rstrip(":").lower()] = re.sub(r"\s+", " ", val.get_text(" ")).strip()
    h1 = s.find("h1")
    cuerpo = s.select_one(".field-name-body, .field-type-text-with-summary")
    return {"nombre": h1.get_text(" ", strip=True) if h1 else "", "campos": campos,
            "descripcion": re.sub(r"\s+", " ", cuerpo.get_text(" ")).strip()[:900] if cuerpo else "", "html": r.text, "url": r.url}


def parser_ayto(fuente, ventana):
    """Agenda oficial del Ayuntamiento de Cádiz (institucional.cadiz.es y turismo.cadiz.es): recorre el listado paginado,
    abre cada ficha y devuelve un candidato por cada día de la ventana en que el evento está vigente."""
    ini, fin = ventana
    enlaces, pendientes, vistas = {}, list(fuente["urls"]), set()
    while pendientes and len(vistas) < 14:
        u = pendientes.pop(0)
        if u in vistas:
            continue
        vistas.add(u)
        try:
            h = requests.get(u, headers=IMG_UA, timeout=25)
            h.raise_for_status()
        except requests.RequestException:
            continue
        s = BeautifulSoup(h.text, "lxml")
        for a in s.find_all("a", href=True):
            href = urljoin(h.url, a["href"])
            if re.search(fuente.get("enlace_regex", r"/evento/[^/?#]+$"), urlparse(href).path) and urlparse(href).netloc == urlparse(h.url).netloc:
                enlaces[href] = True
            elif re.search(r"[?&]page=\d+", href) and urlparse(href).path == urlparse(h.url).path:
                pendientes.append(href)
        # calendario mensual de Turismo: meses de la ventana
        for mes in {f"{ini:%Y-%m}", f"{fin:%Y-%m}"}:
            if "turismo.cadiz.es" in h.url and "mini=" not in h.url:
                pendientes.append(h.url + ("&" if "?" in h.url else "?") + f"mini={mes}")
    out, errores = [], 0

    def ficha(u):
        try:
            return u, detalle_ayto(u)
        except Exception:
            return u, None
    with ThreadPoolExecutor(8) as ex:
        for u, d in ex.map(ficha, list(enlaces)):
            if not d:
                errores += 1
                continue
            c = d["campos"]
            fechas = _fechas(c.get("fecha de evento") or c.get("fecha") or c.get("fechas") or "")
            if not fechas:
                continue
            f0, f1 = min(fechas), max(fechas)
            dir_ = c.get("direccion") or c.get("dirección") or ""
            for i in range((fin - ini).days + 1):
                dia = ini + timedelta(days=i)
                if f0 <= dia <= f1:
                    out.append({"nombre": d["nombre"], "categoria_fuente": c.get("categoría") or c.get("categoria"), "fecha": dia.isoformat(),
                                "fecha_inicio_evento": f0.isoformat(), "fecha_fin_evento": f1.isoformat(),
                                "hora_inicio": _hora(c.get("horario")), "horario_texto": c.get("horario"), "precio_texto": c.get("precio"),
                                "direccion": dir_, "lugar": re.split(r"\s*\(", dir_)[0].strip() or None, "descripcion_fuente": d["descripcion"],
                                "url": d["url"], "multidia": f0 != f1, "permanente": (f1 - f0).days > 180})
    vistos, unicos = set(), []
    for c in out:  # la misma ficha puede salir por dos URLs del listado
        k = (c["nombre"].lower(), c["fecha"])
        if k not in vistos:
            vistos.add(k); unicos.append(c)
    return unicos, errores


def parser_bacantix(fuente, ventana):
    """Venta de entradas oficial del Ayuntamiento (Teatros de Cádiz) en Bacantix: la web se pinta con JavaScript, se renderiza con Chromium
    y se leen los atributos data-* de cada tarjeta (título, fechas, recinto, sinopsis)."""
    import render as rd
    ini, fin = ventana
    out = []
    with rd.Renderer() as r:
        pg = r.browser.new_page(user_agent=IMG_UA["User-Agent"], locale="es-ES")
        pg.goto(fuente["urls"][0], wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(1500)
        tarjetas = pg.evaluate("""() => [...document.querySelectorAll('article[data-literalespectaculo]')].map(a => ({
            nombre: a.dataset.literalespectaculo, ini: a.dataset.fechainicio, fin: a.dataset.fechafin, tipo: (a.dataset.tipoevento || '').split('|')[1] || '',
            busc: a.dataset.buscarevento || '', agotado: /agotado/i.test(a.innerText), enlace: (a.querySelector('a[href]') || {}).href || ''}))""")
        pg.close()
    for t in tarjetas:
        try:
            f0, f1 = date(int(t["ini"][:4]), int(t["ini"][4:6]), int(t["ini"][6:])), date(int(t["fin"][:4]), int(t["fin"][4:6]), int(t["fin"][6:]))
        except Exception:
            continue
        partes = t["busc"].split("|")
        lugar = next((x for x in reversed(partes) if x.strip()), "")
        sinopsis = re.sub(r"\s+", " ", partes[1] if len(partes) > 1 else "")[:600]
        for i in range((fin - ini).days + 1):
            dia = ini + timedelta(days=i)
            if f0 <= dia <= f1:
                out.append({"nombre": t["nombre"], "categoria_fuente": t["tipo"].lower(), "fecha": dia.isoformat(), "fecha_inicio_evento": f0.isoformat(),
                            "fecha_fin_evento": f1.isoformat(), "lugar": lugar, "descripcion_fuente": sinopsis, "agotado": t["agotado"],
                            "url": t["enlace"] or fuente["urls"][0], "multidia": f0 != f1, "permanente": False})
    return out, 0


MES_N = {m: i + 1 for i, m in enumerate(ag.MESES)}


def parser_uca(fuente, ventana):
    """Agenda de eventos de la UCA (uca.es/evento/): solo los etiquetados «Campus Cádiz» (la UCA tiene campus en Puerto Real, Jerez y Algeciras)."""
    ini, fin = ventana
    out = []
    for pag in range(1, 8):
        u = fuente["urls"][0] + (f"page/{pag}/" if pag > 1 else "")
        try:
            h = requests.get(u, headers=IMG_UA, timeout=25)
            h.raise_for_status()
        except requests.RequestException:
            break
        arts = BeautifulSoup(h.text, "lxml").select("article")
        if not arts:
            break
        for a in arts:
            txt = re.sub(r"\s+", " ", a.get_text(" "))
            m = re.search(r"evento \(\s*(\d{1,2}) ([a-záéíóú]+) (\d{4})\s*\)", txt, re.I)
            link = a.find("a", href=True)
            if not (m and link and m.group(2).lower() in MES_N):
                continue
            dia = date(int(m.group(3)), MES_N[m.group(2).lower()], int(m.group(1)))
            if ini <= dia <= fin and "Campus Cádiz" in txt:
                out.append({"nombre": (a.find(["h2", "h3"]) or link).get_text(" ", strip=True), "fecha": dia.isoformat(), "categoria_fuente": "universidad",
                            "descripcion_fuente": txt[:500], "url": link["href"], "lugar": "Campus Cádiz (UCA) — confirmar sede y dirección en la ficha", "multidia": False, "permanente": False})
    return out, 0


JUNTA = "https://www.juntadeandalucia.es"


def parser_junta(fuente, ventana):
    """Agenda Cultural de Andalucía (Junta de Andalucía) filtrada por provincia de Cádiz y por la ventana de fechas. Cada tarjeta trae «Sala - Municipio»:
    el municipio «Cádiz» (sin «(Cádiz)» detrás) indica la capital. Es una fuente oficial; la verificación final sigue siendo del agente."""
    ini, fin = ventana
    out = []
    for pag in range(0, 10):
        params = {"province": fuente.get("provincia_id", "1439"), "date_from": ini.isoformat(), "date_to": fin.isoformat()}
        if pag:
            params["page"] = pag
        h = requests.get(fuente["urls"][0], params=params, headers=IMG_UA, timeout=30)
        h.raise_for_status()
        arts = BeautifulSoup(h.text, "lxml").select("article[role=article]")
        nuevos = 0
        for a in arts:
            link = next((x for x in a.find_all("a", href=True) if "/evento/" in x["href"]), None)
            tit = a.select_one(".headline")
            if not (link and tit):
                continue
            nuevos += 1
            txt = re.sub(r"\s+", " ", a.get_text(" "))
            fechas = [date(int(y), MES_N[m.lower()], int(d)) for d, m, y in re.findall(r"(\d{2}) (" + "|".join(m.capitalize() for m in ag.MESES) + r") (\d{4})", txt) if m.lower() in MES_N]
            lugar_el = a.select_one(".text-accent a") or a.select_one(".text-accent")
            lugar = lugar_el.get_text(" ", strip=True) if lugar_el else ""
            venue, _, muni = lugar.rpartition(" - ")
            hora = re.search(r"(?<![\d/])(\d{1,2})[:.](\d{2})(?!\d)", txt)
            f0, f1 = (min(fechas), max(fechas)) if fechas else (None, None)
            if not f0:
                continue
            url = urljoin(JUNTA, link["href"])
            for i in range((fin - ini).days + 1):
                dia = ini + timedelta(days=i)
                if f0 <= dia <= f1:
                    out.append({"nombre": tit.get_text(" ", strip=True), "fecha": dia.isoformat(), "fecha_inicio_evento": f0.isoformat(), "fecha_fin_evento": f1.isoformat(),
                                "hora_inicio": f"{int(hora.group(1)):02d}:{hora.group(2)}" if hora else None, "lugar": venue or lugar, "municipio": muni.strip() or None,
                                "pista_capital": (muni.strip() == "Cádiz") if muni else None, "url": url, "multidia": f0 != f1, "permanente": (f1 - f0).days > 180})
        if not nuevos:
            break
    vistos, unicos = set(), []
    for c in out:
        k = (c["nombre"].lower(), c["fecha"])
        if k not in vistos:
            vistos.add(k); unicos.append(c)
    return unicos, 0


def parser_guia(fuente, ventana):
    """Guía de Cádiz – Agenda por categorías: cada ficha trae el municipio («Cádiz», «Jerez de la Frontera»…), lo que permite filtrar la capital."""
    ini, fin = ventana
    out = []

    def pagina(u):
        h = requests.get(u, headers=IMG_UA, timeout=30)
        h.raise_for_status()
        return BeautifulSoup(h.text, "lxml")
    for base in fuente["urls"]:
        for pag in range(0, 6):
            try:
                s = pagina(base + (f"?page={pag}" if pag else ""))
            except requests.RequestException:
                break
            tarjetas = [a for a in s.find_all("a", href=True) if a.select_one(".short_info")]
            if not tarjetas:
                break
            for a in tarjetas:
                si = a.select_one(".short_info")
                muni = (si.select_one(".icon_pin").parent.get_text(" ", strip=True) if si.select_one(".icon_pin") else "")
                fechas = [date(int(y), int(m), int(d)) for d, m, y in re.findall(r"(\d{2})/(\d{2})/(\d{4})", si.get_text(" "))]
                if not fechas:
                    continue
                f0, f1 = min(fechas), max(fechas)
                cat = base.rstrip("/").split("/")[-1]
                for i in range((fin - ini).days + 1):
                    dia = ini + timedelta(days=i)
                    if f0 <= dia <= f1:
                        out.append({"nombre": si.find("h3").get_text(" ", strip=True), "categoria_fuente": cat, "fecha": dia.isoformat(), "fecha_inicio_evento": f0.isoformat(),
                                    "fecha_fin_evento": f1.isoformat(), "municipio": muni, "pista_capital": muni.strip().lower() == "cádiz", "url": urljoin("https://www.guiadecadiz.com", a["href"]),
                                    "multidia": f0 != f1, "permanente": (f1 - f0).days > 180})
    vistos, unicos = set(), []
    for c in out:
        k = (c["nombre"].lower(), c["fecha"])
        if k not in vistos:
            vistos.add(k); unicos.append(c)
    return unicos, 0


MESES_ABR = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DIC": 12}


def parser_cadizcf(fuente, ventana):
    """Cádiz CF (web oficial, leída con Chromium porque devuelve 403 a los scripts): próximos partidos COMO LOCAL en el Nuevo Mirandilla (Cádiz capital)
    con fecha, hora, rival, competición, ficha oficial e imagen oficial (og:image)."""
    import render as rd
    ini, fin = ventana
    UA_ = IMG_UA["User-Agent"]
    out = []
    with rd.Renderer() as r:
        ctx = r.browser.new_context(user_agent=UA_, locale="es-ES")
        pg = ctx.new_page()
        pg.goto(fuente["urls"][0], wait_until="networkidle", timeout=45000)
        enlaces = []
        for h in pg.evaluate("Array.from(document.querySelectorAll('a')).map(a=>a.href)"):
            if "/partidos/temporada-" in h and h not in enlaces:
                enlaces.append(h)
        for h in enlaces:
            p2 = ctx.new_page()
            try:
                if p2.goto(h, wait_until="networkidle", timeout=45000).status >= 400:
                    continue
                html = p2.content()
                titulo = (re.findall(r'property="og:title"[^>]*content="([^"]+)"', html) or [""])[0]
                if not titulo.startswith("Cádiz CF vs "):
                    continue  # solo partidos en casa
                texto = p2.inner_text("body")
                m = re.search(r"([A-ZÁÉÍÓÚ]{3}),?\s+(\d{1,2})\s+DE\s+([A-Z]{3})\s*\|?\s*(\d{1,2}):(\d{2})\s*([ap])\.?m", texto.replace("\n", " | "), re.I)
                if not m:
                    continue  # partido ya jugado o sin fecha publicada
                dia, mes = int(m.group(2)), MESES_ABR.get(m.group(3).upper())
                hh = int(m.group(4)) % 12 + (12 if m.group(6).lower() == "p" else 0)
                anio = ini.year if mes >= ini.month or ini.month < 11 else ini.year + 1
                f = date(anio, mes, dia)
                if not (ini <= f <= fin):
                    continue
                rival, comp = re.match(r"Cádiz CF vs (.+?) - (.+)$", titulo).groups()
                est = "JP Financial Estadio" if "JP Financial" in texto else "Nuevo Mirandilla"
                img = (re.findall(r'property="og:image"[^>]*content="([^"]+)"', html) or [None])[0]
                out.append({"nombre": f"Cádiz CF – {rival} · {comp}", "fecha": f.isoformat(), "hora_inicio": f"{hh:02d}:{m.group(5)}", "lugar": f"Estadio Nuevo Mirandilla ({est})",
                            "direccion": "Cádiz", "url": h, "imagen_url_oficial": img, "pista_capital": True, "multidia": False, "permanente": False,
                            "descripcion_fuente": f"Partido en casa del Cádiz CF ({comp}) contra {rival}. Ficha oficial del club.", "precio_texto": "Consultar en entradas.cadizcf.com"})
            finally:
                p2.close()
    return out, 0


def parser_cgf(fuente, ventana):
    """Cádiz Guitar Festival (web del organizador): conciertos con fecha, hora, sala y localidad al final del campo «Location»."""
    ini, fin = ventana
    h = requests.get(fuente["urls"][0], headers=IMG_UA, timeout=30)
    h.raise_for_status()
    t = limpio(h.text, 80000)
    out = []
    M = "|".join(ag.MESES)
    for ciclo, d_, m_, a_, hh, resto, loc, extra in re.findall(r"((?:Ciclo|Concierto)[^“]{0,80}?) (\d{1,2}) de (" + M + r") de (\d{4}) (\d{2}:\d{2}) (.+?) Location (.+?) ENTRADAS & MÁS INFO ([^C]{0,60})", t):
        dia = date(int(a_), MES_N[m_], int(d_))
        if not ini <= dia <= fin:
            continue
        cap = bool(re.search(r"\bC[áa]diz$", loc.strip())) and not OTROS_MUNICIPIOS.search(loc)
        out.append({"nombre": f"Cádiz Guitar Festival · {resto.split('“')[0].strip()}", "categoria_fuente": "música", "fecha": dia.isoformat(), "hora_inicio": hh, "lugar": loc.strip(),
                    "pista_capital": cap, "precio_texto": extra.strip(), "descripcion_fuente": resto[:300], "url": fuente["urls"][0], "multidia": False, "permanente": False})
    return out, 0


def parser_laciudad(r, fuente):
    """Páginas de programación de recintos de laciudad.cadiz.es (bloques .eventitem bajo h3 de mes)."""
    s = BeautifulSoup(r.text, "lxml")
    m = re.search(r"\b(20\d\d)\b", s.get_text(" "))
    ano_pagina = int(m.group(1)) if m else None
    out = []
    for it in s.select(".eventitem"):
        a = it.find("a")
        f = it.select_one(".fechtop")
        if not (a and f):
            continue
        txt = f.get_text(" ")
        cat = it.select_one(".estilfech").get_text(" ").split("·")[0].strip().lower() if it.select_one(".estilfech") else ""
        dm = re.findall(r"(\d{1,2})(?:\s*y\s*(\d{1,2}))?\s+([a-záéíóú]+)", txt.lower())
        hm = re.search(r"(\d{1,2})[.:]?(\d{2})?\s*h", txt.lower())
        if not dm or dm[0][2] not in MESES:
            continue
        dias = [int(x) for x in dm[0][:2] if x]
        fechas = [a_iso(d, MESES[dm[0][2]], ano_pagina).isoformat() for d in dias]
        hora = f"{int(hm.group(1)):02d}:{hm.group(2) or '00'}" if hm else None
        suspendido = "suspendid" in it.get_text(" ").lower() or "cancelad" in it.get_text(" ").lower()
        for fe in fechas:
            out.append({"nombre": a.get_text(" ", strip=True), "categoria_fuente": cat, "fecha": fe, "hora_inicio": hora,
                        "url": urljoin(r.url, a.get("href", "")), "horario_texto": txt.strip(), "suspendido": suspendido})
    return out


CP_CADIZ = re.compile(r"\b110(0[1-9]|1[0-2])\b")
OTROS_MUNICIPIOS = re.compile(r"san fernando|puerto real|puerto de santa|chiclana|jerez|rota|chipiona|sanl[uú]car|conil|vejer|barbate|algeciras|la l[ií]nea|tarifa|el bosque|medina|arcos|ubrique|villamart[ií]n|sotogrande|san roque", re.I)


def pista_capital(*textos):
    """Pista (NO verificación) de que el lugar está en Cádiz capital: código postal 11001-11012 o «Cádiz» sin otro municipio."""
    t = " ".join(x for x in textos if x)
    if not t.strip():
        return None          # sin información: el agente debe verificar
    if OTROS_MUNICIPIOS.search(t) or re.search(r"\b(sevilla|m[aá]laga|madrid|online|virtual)\b", t, re.I):
        return False
    return True if (CP_CADIZ.search(t) or re.search(r"\bC[áa]diz\b", t, re.I)) else None


def _loc(x):
    loc = x.get("location") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    addr = loc.get("address") or {}
    if isinstance(addr, str):
        addr = {"streetAddress": addr}
    calle = ", ".join(str(addr.get(k)) for k in ("streetAddress", "postalCode", "addressLocality") if addr.get(k))
    return loc.get("name"), calle


def parser_jsonld(r, fuente):
    out = []
    s = BeautifulSoup(r.text, "lxml")
    for tag in s.find_all("script", type="application/ld+json"):
        try:
            datos = json.loads(tag.string or "")
        except Exception:
            continue
        pila = datos if isinstance(datos, list) else [datos]
        while pila:
            x = pila.pop()
            if isinstance(x, dict):
                if isinstance(x.get("itemListElement"), list):
                    pila += [i.get("item", i) if isinstance(i, dict) else i for i in x["itemListElement"]]
                if "Event" in str(x.get("@type", "")):
                    nombre_lugar, calle = _loc(x)
                    img = x.get("image")
                    out.append({"nombre": x.get("name"), "fecha": (x.get("startDate") or "")[:10], "hora_inicio": (x.get("startDate") or "")[11:16] or None, "url": x.get("url"),
                                "lugar": nombre_lugar, "direccion": calle or None, "imagen_url": img if isinstance(img, str) else None,
                                "descripcion_fuente": (x.get("description") or "")[:400], "pista_capital": pista_capital(nombre_lugar, calle, x.get("description")),
                                "multidia": False, "permanente": False})
    return out


def enriquecer_con_ficha(cands, limite=40):
    """Los listados (Eventbrite…) no traen el lugar: se abre la ficha de cada evento de la ventana y se lee su JSON-LD."""
    def una(c):
        try:
            h = requests.get(c["url"], headers=IMG_UA, timeout=25)
            for tag in BeautifulSoup(h.text, "lxml").find_all("script", type="application/ld+json"):
                j = json.loads(tag.string or "")
                for x in (j if isinstance(j, list) else [j]):
                    if isinstance(x, dict) and "Event" in str(x.get("@type", "")):
                        n, calle = _loc(x)
                        c["lugar"], c["direccion"] = n or c.get("lugar"), calle or c.get("direccion")
                        c["pista_capital"] = pista_capital(n, calle, c.get("descripcion_fuente"))
                        return
        except Exception:
            pass
    pend = [c for c in cands if c.get("url") and not c.get("direccion")][:limite]
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(una, pend))


def parser_texto(r, fuente):
    return []  # sin candidatos estructurados: el agente lee 'texto' de la fuente


IMG_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept-Language": "es-ES,es;q=0.9"}
import parsers_extra as _pe
PARSERS_EXTRA = {"onda": _pe.parser_onda, "casaibero": _pe.parser_casaibero, "palacio": _pe.parser_palacio, "ganzua": _pe.parser_ganzua, "cajasol": _pe.parser_cajasol}
PARSERS = {"laciudad": parser_laciudad, "jsonld": parser_jsonld, "texto": parser_texto, "laciudad_indice": parser_texto, "ayto": parser_texto, "bacantix": parser_texto, "uca": parser_texto, "junta": parser_texto, "guia": parser_texto, "cgf": parser_texto, "cadizcf": parser_texto, "onda": parser_texto, "casaibero": parser_texto, "palacio": parser_texto, "ganzua": parser_texto, "cajasol": parser_texto}


def procesar(fuente, ventana=None):
    res = {"id": fuente["id"], "nombre": fuente["nombre"], "estado": "ok", "paginas": [], "candidatos": []}
    if fuente.get("via") == "web" or fuente.get("activa") is False:
        res.update(estado="web" if fuente.get("via") == "web" else "inactiva", error=fuente.get("nota", ""))
        res["consulta_web"] = {"fuente": fuente["nombre"], "urls": fuente.get("urls", []), "busqueda": fuente.get("consulta", ""), "nota": fuente.get("nota", "")}
        return res
    if not fuente["urls"]:
        res.update(estado="sin_url", error=fuente.get("nota", "URL por localizar"))
        return res
    if fuente["parser"] in ("ayto", "bacantix", "uca", "junta", "guia", "cgf", "cadizcf", "onda", "casaibero", "palacio", "ganzua", "cajasol"):
        try:
            cands, errores = {"ayto": parser_ayto, "bacantix": parser_bacantix, "uca": parser_uca, "junta": parser_junta, "guia": parser_guia, "cgf": parser_cgf, "cadizcf": parser_cadizcf, **PARSERS_EXTRA}[fuente["parser"]](fuente, ventana)
            for c in cands:
                c.update(fuente_id=fuente["id"], fuente=fuente["nombre"], provincial=fuente["provincial"], tipo_fuente=fuente["tipo"])
            res["candidatos"] = cands
            res["paginas"].append({"url": fuente["urls"][0], "http": 200, "fichas_con_error": errores})
        except Exception as e:
            res.update(estado="fallo", error=str(e)[:300])
        return res
    for url in fuente["urls"]:
        try:
            r = descargar(url)
            cands = PARSERS[fuente["parser"]](r, fuente)
            if fuente["parser"] == "jsonld" and ventana:
                cands = [c for c in cands if ventana[0].isoformat() <= (c.get("fecha") or "") <= ventana[1].isoformat()]
                if fuente.get("enriquecer", True):
                    enriquecer_con_ficha(cands)
            for c in cands:
                c.update(fuente_id=fuente["id"], fuente=fuente["nombre"], provincial=fuente["provincial"], tipo_fuente=fuente["tipo"])
            res["candidatos"] += cands
            res["paginas"].append({"url": r.url, "http": r.status_code, "texto": limpio(r.text) if fuente["parser"] in ("texto", "laciudad", "laciudad_indice") else None})
        except Exception as e:  # una fuente caída no detiene el resto
            res["paginas"].append({"url": url, "error": str(e)[:200]})
    if not any("error" not in p for p in res["paginas"]):
        res["estado"] = "fallo"
        res["error"] = "; ".join(p.get("error", "") for p in res["paginas"])[:300]
    return res


def detalle(url):
    try:
        return limpio(descargar(url).text, 2500)
    except Exception as e:
        return f"[no se pudo leer: {e}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=ag.hoy().isoformat())
    ap.add_argument("--hasta")
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--destino", help="carpeta de salida AAAA-MM-DD[/finde|/mensual] (p. ej. 2026-10-29/finde para el reel del jueves)")
    a = ap.parse_args()
    fuentes = ag.cargar_json(ag.RAIZ / "fuentes.json")["fuentes"]
    ini = date.fromisoformat(a.fecha)
    fin = date.fromisoformat(a.hasta) if a.hasta else ini
    with ThreadPoolExecutor(6) as ex:
        resultados = list(ex.map(lambda f: procesar(f, (ini, fin)), fuentes))
    cands = [c for r in resultados for c in r["candidatos"] if ini.isoformat() <= (c.get("fecha") or "") <= fin.isoformat()]
    # Páginas de detalle (dirección, precio, descripción) solo para lo que cae en la ventana
    with ThreadPoolExecutor(6) as ex:
        for c, t in zip(cands, ex.map(lambda c: detalle(c["url"]) if c.get("url") else None, cands)):
            c["detalle_texto"] = t
    # Imágenes oficiales de cada candidato (misma web oficial de la ficha); se guardan en posts/F/img/
    import imagenes
    carpeta_img = ag.dir_dia(*(a.destino.split("/") if a.destino else [ini]))
    hechas = {}
    def img(c):
        if c["url"] in hechas or not c.get("url") or c.get("tipo_fuente") not in ("oficial", "recinto"):
            return hechas.get(c.get("url"))
        id_ = re.sub(r"[^a-z0-9]+", "-", urlparse(c["url"]).path.lower()).strip("-")[-60:]
        hechas[c["url"]] = imagenes.buscar_y_descargar(c["url"], id_, carpeta_img)
        return hechas[c["url"]]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(img, cands))
    for c in cands:
        c["imagen_oficial"] = hechas.get(c["url"])
    fuentes_log = [{k: r.get(k) for k in ("id", "nombre", "estado", "error")} | {"candidatos": len(r["candidatos"])} for r in resultados]
    if a.verificar:
        for f in fuentes_log:
            print(f"{f['id']:>2} {f['estado']:<8} {f['candidatos']:>3}  {f['nombre']}  {f.get('error') or ''}")
        return
    carpeta = ag.dir_dia(*(a.destino.split("/") if a.destino else [ini]))
    consultas = [r["consulta_web"] for r in resultados if r.get("consulta_web")]
    for c in consultas:  # búsquedas listas para el agente, con el mes/año de la ventana
        c["busqueda"] = c["busqueda"].replace("{mes}", ag.MESES[ini.month - 1]).replace("{año}", str(ini.year)).replace("{fecha}", f"{ini.day} de {ag.MESES[ini.month - 1]} de {ini.year}")
    ag.guardar_json(carpeta / "candidatos.json", {"generado": ag.ahora().isoformat(timespec="seconds"), "ventana": [ini.isoformat(), fin.isoformat()],
                                                  "candidatos": cands, "fuentes": resultados, "consultas_web": consultas,
                                                  "instruccion": "Consulta TODAS las 'consultas_web' con WebFetch/WebSearch cada día (fuentes que bloquean a los bots o no se pueden leer con el script) y revisa el texto de las fuentes sin parser."})
    with open(ag.RAIZ / "registros" / "fuentes.log", "a", encoding="utf-8") as fh:
        for f in fuentes_log:
            fh.write(f"{ag.ahora().isoformat(timespec='seconds')}\t{f['id']}\t{f['estado']}\t{f['candidatos']}\t{f['nombre']}\t{f.get('error') or ''}\n")
    cob = {}
    for c in cands:
        if not c.get("permanente") and c.get("pista_capital") is not False:
            cob.setdefault(c["fecha"], set()).add((c["nombre"] or "").lower()[:40])
    with open(ag.RAIZ / "registros" / "cobertura.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": ag.ahora().isoformat(timespec="seconds"), "ventana": [ini.isoformat(), fin.isoformat()], "candidatos_automaticos_por_dia": {d_: len(v) for d_, v in sorted(cob.items())},
                             "fuentes_ok": sum(f["estado"] == "ok" for f in fuentes_log), "fuentes_web": len(consultas)}, ensure_ascii=False) + "\n")
    print(f"{len(consultas)} fuentes para consultar con WebFetch/WebSearch (ver consultas_web en candidatos.json)")
    print(f"{len(cands)} candidatos en la ventana; fuentes ok: {sum(f['estado'] == 'ok' for f in fuentes_log)}/{len(fuentes_log)}")
    fallos = [f["nombre"] for f in fuentes_log if f["estado"] not in ("ok", "web", "inactiva")]
    if fallos:
        print("Fuentes sin respuesta:", "; ".join(fallos))


if __name__ == "__main__":
    main()
