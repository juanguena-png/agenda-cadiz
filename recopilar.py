#!/usr/bin/env python3
"""Recopila candidatos de las fuentes de fuentes.json -> posts/FECHA/candidatos.json + registros/fuentes.log.

Este script SOLO reúne material en bruto. La verificación de Cádiz capital, el contraste entre fuentes, la
redacción con palabras propias y la creación de eventos.json las hace el agente (ver CLAUDE.md).
Nunca scrapea Instagram ni Facebook.

  python recopilar.py [--fecha AAAA-MM-DD] [--hasta AAAA-MM-DD]   # recopila
  python recopilar.py --verificar                                  # solo comprueba qué URLs responden
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
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


PARSERS = {"laciudad": parser_laciudad, "jsonld": parser_jsonld, "texto": parser_texto, "laciudad_indice": parser_texto}


def procesar(fuente):
    res = {"id": fuente["id"], "nombre": fuente["nombre"], "estado": "ok", "paginas": [], "candidatos": []}
    if not fuente["urls"]:
        res.update(estado="sin_url", error=fuente.get("nota", "URL por localizar"))
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
        resultados = list(ex.map(procesar, fuentes))
    cands = [c for r in resultados for c in r["candidatos"] if ini.isoformat() <= (c.get("fecha") or "") <= fin.isoformat()]
    # Páginas de detalle (dirección, precio, descripción) solo para lo que cae en la ventana
    with ThreadPoolExecutor(6) as ex:
        for c, t in zip(cands, ex.map(lambda c: detalle(c["url"]) if c.get("url") else None, cands)):
            c["detalle_texto"] = t
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
