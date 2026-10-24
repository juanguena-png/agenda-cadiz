#!/usr/bin/env python3
"""Stories patrocinadas. DESACTIVADO por defecto (PATROCINIOS=off): con 'off' nada de este módulo altera la publicación.

Reglas (con PATROCINIOS=on): máx. 2 stories patrocinadas al día, intercaladas entre las de eventos (nunca la primera),
etiqueta "Publicidad" visible (la pone plantilla/story-patrocinio.html), un solo anunciante por sector a la vez.

patrocinadores/<slug>.json:
  {"nombre": "...", "sector": "hostelería", "inicio": "2026-11-01", "fin": "2026-11-30",
   "texto": "2-3 frases", "imagen": {"archivo": "patrocinadores/img/slug.jpg", "alt_text": "..."}, "posicion": 3}
  ("posicion" opcional: tras cuántas stories de eventos se intercala; mínimo 1)

  python patrocinios.py --avisos            # email 7 días antes de que caduque un patrocinio
  python patrocinios.py --informe AAAA-MM   # informe mensual por anunciante (por email)
"""
import argparse
from datetime import timedelta

import agenda as ag

CARPETA = ag.RAIZ / "patrocinadores"
MAX_DIA = 2


def todos():
    return [dict(ag.cargar_json(f), _archivo=f.name) for f in sorted(CARPETA.glob("*.json"))]


def activos(fecha, log=print):
    if not ag.patrocinios_activos():
        return []
    f = ag.a_fecha(fecha).isoformat()
    vistos, out = {}, []
    for p in sorted((p for p in todos() if p["inicio"] <= f <= p["fin"]), key=lambda p: p["inicio"]):
        if p["sector"] in vistos:
            log(f"Patrocinio '{p['nombre']}' ignorado: el sector '{p['sector']}' ya lo ocupa '{vistos[p['sector']]}' (exclusividad)")
            continue
        vistos[p["sector"]] = p["nombre"]
        out.append(p)
    return out[:MAX_DIA]


def posiciones(n_eventos, patrocinadores):
    """Índices (1..n) tras los que se intercala cada story patrocinada. Nunca antes de la primera story de evento."""
    if n_eventos < 2 or not patrocinadores:
        return {}
    res, k = {}, len(patrocinadores)
    for i, p in enumerate(patrocinadores):
        pos = p.get("posicion") or round(n_eventos * (i + 1) / (k + 1))
        res[i] = min(max(1, int(pos)), n_eventos)
    return res


def avisos():
    import notificar
    hoy = ag.hoy()
    for p in todos():
        if ag.a_fecha(p["fin"]) - hoy == timedelta(days=7):
            notificar.enviar(f"Caduca en 7 días el patrocinio de {p['nombre']}", f"Fin: {p['fin']} (sector {p['sector']}).")


def informe(mes):
    """Suma vistas e interacciones de las stories de cada anunciante, a partir de registros/patrocinios.jsonl (lo alimenta metricas.py)."""
    import json
    import notificar
    ruta = ag.RAIZ / "registros" / "patrocinios.jsonl"
    filas = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()] if ruta.exists() else []
    res = {}
    for f in filas:
        if f["fecha"].startswith(mes):
            r = res.setdefault(f["anunciante"], {"stories": 0, "alcance": 0, "interacciones": 0})
            r["stories"] += 1; r["alcance"] += f.get("alcance", 0); r["interacciones"] += f.get("interacciones", 0)
    for nombre, r in res.items():
        notificar.enviar(f"Informe de patrocinio {mes}: {nombre}",
                         f"Stories publicadas: {r['stories']}\nAlcance acumulado: {r['alcance']}\nInteracciones (respuestas, toques, compartidos): {r['interacciones']}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--avisos", action="store_true")
    ap.add_argument("--informe")
    a = ap.parse_args()
    if a.avisos:
        avisos()
    if a.informe:
        print(informe(a.informe))
