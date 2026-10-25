#!/usr/bin/env python3
"""Etiquetas de Instagram (user_tags) en las diapositivas del carrusel.

Solo se etiquetan perfiles VERIFICADOS de Cádiz capital: los de perfiles_ig.json (comprobados con la API oficial, business_discovery).
Cada evento se etiqueta con (a) su campo `etiquetas_ig` y (b) los perfiles del directorio cuyas `claves` aparezcan en lugar/nombre/descripción.

  python etiquetas.py --verificar usuario [usuario…]          # ¿existe y quién es? (API oficial, sin scraping)
  python etiquetas.py --anadir usuario "Nombre" "clave1" "clave2"   # verifica y añade al directorio
  python etiquetas.py --evento posts/F/eventos.json          # qué se etiquetaría por evento
"""
import argparse
import json
import re
import sys
import unicodedata

import agenda as ag

RUTA = ag.RAIZ / "perfiles_ig.json"
MAX_ETIQUETAS_IMAGEN = 20  # límite de Instagram por imagen


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def directorio():
    return (ag.cargar_json(RUTA, {}) or {}).get("perfiles", {})


def limpiar(u):
    return str(u or "").strip().lstrip("@").lower()


def verificar(usuario):
    """(existe, nombre, seguidores) con business_discovery (cuentas profesionales públicas). Nunca scraping."""
    from publicar import ErrorAPI, api
    try:
        b = api("GET", ag.secreto("IG_USER_ID"), fields=f"business_discovery.username({limpiar(usuario)}){{username,name,followers_count}}")["business_discovery"]
        return True, b.get("name"), b.get("followers_count")
    except (ErrorAPI, KeyError):
        return False, None, None


def para_evento(ev):
    """Usuarios (sin @) a etiquetar en un evento: etiquetas_ig explícitas válidas + coincidencias del directorio."""
    dir_ = directorio()
    texto = _norm(" ".join(str(ev.get(c) or "") for c in ("lugar", "nombre", "descripcion", "info", "organizador")))
    out = []
    for u in [limpiar(x) for x in (ev.get("etiquetas_ig") or [])]:
        if u in dir_ and u not in out:
            out.append(u)
    for u, d in dir_.items():
        if u not in out and any(re.search(c, texto) for c in d.get("claves", [])):
            out.append(u)
    return out


def para_diapositiva(eventos):
    """Unión (sin repetir, máx. 20) de las etiquetas de los eventos de una diapositiva."""
    out = []
    for ev in eventos:
        for u in para_evento(ev):
            if u not in out:
                out.append(u)
    return out[:MAX_ETIQUETAS_IMAGEN]


def posiciones(usuarios):
    """user_tags de la API: {username, x, y} con x,y entre 0 y 1 (esquina superior izquierda = 0,0); repartidas sin tapar el texto central."""
    n = len(usuarios)
    return [{"username": u, "x": round(0.12 + 0.76 * ((i % 4) + 0.5) / 4, 3), "y": round(0.10 + 0.30 * (i // 4 + 0.5) / max(1, (n + 3) // 4), 3)} for i, u in enumerate(usuarios)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verificar", nargs="+")
    ap.add_argument("--anadir", nargs="+", metavar=("USUARIO", "NOMBRE"))
    ap.add_argument("--evento")
    a = ap.parse_args()
    if a.verificar:
        for u in a.verificar:
            ok, nombre, seg = verificar(u)
            print(f"{'OK ' if ok else 'NO '} @{limpiar(u)} | {nombre} | {seg} seguidores" if ok else f"NO  @{limpiar(u)} (no existe o no es cuenta profesional pública)")
    elif a.anadir:
        u, nombre, *claves = a.anadir
        ok, real, seg = verificar(u)
        if not ok:
            sys.exit(f"@{limpiar(u)} no se puede verificar: no se añade")
        d = ag.cargar_json(RUTA, {})
        d.setdefault("perfiles", {})[limpiar(u)] = {"nombre": nombre, "claves": [_norm(c) for c in claves]}
        ag.guardar_json(RUTA, d)
        print(f"Añadido @{limpiar(u)} ({real}, {seg} seguidores). Comprueba que es de Cádiz capital.")
    elif a.evento:
        for ev in ag.cargar_eventos(__import__("pathlib").Path(a.evento).parent)["eventos"]:
            print(ev["nombre"][:60], "->", [f"@{u}" for u in para_evento(ev)])
