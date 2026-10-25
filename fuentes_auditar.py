#!/usr/bin/env python3
"""Auditoría de fuentes: qué fuentes responden, cuáles aportan candidatos y qué búsquedas de descubrimiento rinden.
   python fuentes_auditar.py [--dias 14]   -> imprime y escribe registros/auditoria-fuentes.md
Sirve a la mejora continua: el agente añade fuentes nuevas, sustituye las que nunca rinden y deja constancia en registros/fuentes-nuevas.md."""
import argparse
import json
from collections import defaultdict
from datetime import timedelta

import agenda as ag

LOG = ag.RAIZ / "registros" / "fuentes.log"
SALIDA = ag.RAIZ / "registros" / "auditoria-fuentes.md"


def main(dias, dias_atras=7):
    desde = (ag.ahora() - timedelta(days=dias)).isoformat()
    stats = defaultdict(lambda: {"ok": 0, "fallo": 0, "web": 0, "cand": 0, "dias": set(), "id": None})
    if LOG.exists():
        for l in LOG.read_text(encoding="utf-8").splitlines():
            p = l.split("\t")
            if len(p) < 5 or p[0] < desde:
                continue
            ts, fid, est, n, nombre = p[:5]
            s = stats[nombre]
            s["id"] = fid
            s["dias"].add(ts[:10])
            if est == "ok":
                s["ok"] += 1
                s["cand"] += int(n or 0)
            elif est == "web":
                s["web"] += 1
            else:
                s["fallo"] += 1
    caidas = sorted((n for n, s in stats.items() if s["fallo"] and not s["ok"]), key=str)
    mudas = sorted((n for n, s in stats.items() if s["ok"] and not s["cand"]), key=str)
    out = [f"# Auditoría de fuentes (últimos {dias} días)\n", f"Fuentes registradas: {len(stats)}\n", "## Caídas (nunca responden): sustituir o buscar la URL nueva"]
    out += [f"- {n}" for n in caidas] or ["- ninguna"]
    out += ["\n## Responden pero no aportan candidatos: revisar parser o enlace"]
    out += [f"- {n}" for n in mudas] or ["- ninguna"]
    out += ["\n## Las que más aportan"]
    out += [f"- {n}: {s['cand']} candidatos" for n, s in sorted(stats.items(), key=lambda x: -x[1]["cand"])[:10]]
    out += ["\n## Descubrimiento (estado.json → descubiertos_web)"]
    rinden, vacias = defaultdict(int), defaultdict(int)
    for est in sorted((ag.RAIZ / "posts").glob("*/estado.json")):
        dw = (ag.cargar_json(est, {}) or {}).get("descubiertos_web") or {}
        for k, v in (dw.items() if isinstance(dw, dict) else []):
            (rinden if v else vacias)[k] += 1
    out += [f"- rinde ({v} días): {k}" for k, v in sorted(rinden.items(), key=lambda x: -x[1])] or ["- (aún sin datos: el agente debe rellenar descubiertos_web cada día)"]
    out += [f"- NUNCA rinde ({v} días): {k} → proponer sustituirla" for k, v in vacias.items() if k not in rinden]
    # Control de lectura: las fuentes «via: web» y las búsquedas de descubrimiento deben anotarse en estado.json → fuentes_leidas cada día
    web = [f["nombre"] for f in (ag.cargar_json(ag.RAIZ / "fuentes.json", {}) or {}).get("fuentes", []) if f.get("via") == "web"]
    leidas, dias = set(), 0
    for est in sorted((ag.RAIZ / "posts").glob("*/estado.json"))[-dias_atras:]:
        fl = (ag.cargar_json(est, {}) or {}).get("fuentes_leidas")
        if fl:
            dias += 1
            leidas |= set(fl)
    out += ["\n## Control de lectura de fuentes web (estado.json → fuentes_leidas)"]
    if not dias:
        out += ["- ⚠️ Ningún día registra `fuentes_leidas`: el agente no está dejando constancia de qué fuentes web lee."]
    else:
        out += [f"- NO leída en {dias} día(s) registrado(s): {n}" for n in web if n not in leidas] or ["- Todas las fuentes web se han leído."]
    txt = "\n".join(out) + "\n"
    SALIDA.write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=14)
    main(ap.parse_args().dias)
