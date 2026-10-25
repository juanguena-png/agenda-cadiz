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


def descargar(url):
    if any(h in urlparse(url).netloc for h in HOSTS_PROHIBIDOS):
        raise ValueError("Prohibido hacer scraping de Instagram/Facebook")
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
            if re.search(r"/evento/[^/?#]+$", urlparse(href).path) and urlparse(href).netloc == urlparse(h.url).netloc:
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
                    loc = x.get("location") or {}
                    addr = loc.get("address") or {}
                    out.append({"nombre": x.get("name"), "fecha": (x.get("startDate") or "")[:10],
                                "hora_inicio": (x.get("startDate") or "")[11:16] or None, "url": x.get("url"),
                                "lugar": loc.get("name"), "direccion": json.dumps(addr, ensure_ascii=False) if addr else None,
                                "imagen_url": x.get("image") if isinstance(x.get("image"), str) else None,
                                "descripcion_fuente": (x.get("description") or "")[:400]})
    return out


def parser_texto(r, fuente):
    return []  # sin candidatos estructurados: el agente lee 'texto' de la fuente


IMG_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept-Language": "es-ES,es;q=0.9"}
PARSERS = {"laciudad": parser_laciudad, "jsonld": parser_jsonld, "texto": parser_texto, "laciudad_indice": parser_texto, "ayto": parser_texto}


def procesar(fuente, ventana=None):
    res = {"id": fuente["id"], "nombre": fuente["nombre"], "estado": "ok", "paginas": [], "candidatos": []}
    if not fuente["urls"]:
        res.update(estado="sin_url", error=fuente.get("nota", "URL por localizar"))
        return res
    if fuente["parser"] == "ayto":
        try:
            cands, errores = parser_ayto(fuente, ventana)
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
    carpeta_img = ag.dir_dia(ini)
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
    carpeta = ag.dir_dia(ini)
    ag.guardar_json(carpeta / "candidatos.json", {"generado": ag.ahora().isoformat(timespec="seconds"), "ventana": [ini.isoformat(), fin.isoformat()],
                                                  "candidatos": cands, "fuentes": resultados})
    with open(ag.RAIZ / "registros" / "fuentes.log", "a", encoding="utf-8") as fh:
        for f in fuentes_log:
            fh.write(f"{ag.ahora().isoformat(timespec='seconds')}\t{f['id']}\t{f['estado']}\t{f['candidatos']}\t{f['nombre']}\t{f.get('error') or ''}\n")
    print(f"{len(cands)} candidatos en la ventana; fuentes ok: {sum(f['estado'] == 'ok' for f in fuentes_log)}/{len(fuentes_log)}")
    fallos = [f["nombre"] for f in fuentes_log if f["estado"] != "ok"]
    if fallos:
        print("Fuentes sin respuesta:", "; ".join(fallos))


if __name__ == "__main__":
    main()
