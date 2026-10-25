#!/usr/bin/env python3
"""Métricas diarias de Instagram y Facebook -> registros/metricas.jsonl, resumen y pruebas A/B.

  python metricas.py --recoger               # guarda la foto del día (cuenta + publicaciones recientes + horas activas + audiencia)
  python metricas.py --resumen [--dias 14]   # imprime tendencias para que el agente decida mejoras
  python metricas.py --ab                    # compara variantes de portada A/B -> registros/ab.json
  python metricas.py --mejora "título" "motivo"   # registra la mejora en registros/mejoras.md y avisa por email

Meta cambia y retira métricas a menudo: cada una se pide por separado y un fallo se registra sin detener el resto.
"""
import argparse
import json
from datetime import timedelta

import agenda as ag
import notificar
from publicar import ErrorAPI, api

SALIDA = ag.RAIZ / "registros" / "metricas.jsonl"
IG_CUENTA = ["reach", "views", "accounts_engaged", "total_interactions", "likes", "comments", "saves", "shares", "follows_and_unfollows", "profile_views"]
IG_MEDIA = ["reach", "saved", "shares", "likes", "comments", "total_interactions", "views"]
FB_PAGINA = ["page_media_view", "page_post_engagements", "page_follows", "page_daily_follows_unique"]


def pedir(ruta, **p):
    try:
        return api("GET", ruta, **p), None
    except ErrorAPI as e:
        return None, str(e)


def insights_cuenta_ig(ig, errores):
    out = {}
    for m in IG_CUENTA:
        d, e = pedir(f"{ig}/insights", metric=m, period="day", metric_type="total_value")
        if e:
            errores.append(f"ig {m}: {e}")
        else:
            dd = d["data"][0] if d.get("data") else {}
            out[m] = dd.get("total_value", {}).get("value") if "total_value" in dd else ((dd.get("values") or [{}])[-1].get("value"))
    d, e = pedir(f"{ig}/insights", metric="online_followers", period="lifetime")
    if not e and d.get("data"):
        horas = (d["data"][0]["values"] or [{}])[-1].get("value", {})
        out["horas_activas"] = dict(sorted(horas.items(), key=lambda kv: -kv[1])[:6])
    for brk in ("city", "country", "age"):
        d, e = pedir(f"{ig}/insights", metric="follower_demographics", period="lifetime", metric_type="total_value", breakdown=brk, timeframe="last_30_days")
        if not e and d.get("data"):
            res = d["data"][0]["total_value"].get("breakdowns", [{}])[0].get("results", [])
            out[f"audiencia_{brk}"] = {"/".join(r["dimension_values"]): r["value"] for r in res[:8]}
    return out


def publicaciones_ig(ig, errores):
    out = []
    d, e = pedir(f"{ig}/media", fields="id,media_type,permalink,timestamp,caption", limit=25)
    if e:
        errores.append(f"ig media: {e}"); return out
    limite = (ag.ahora() - timedelta(days=14)).isoformat()
    for m in d.get("data", []):
        if m["timestamp"] < limite[:10]:
            continue
        fila = {"id": m["id"], "tipo": m["media_type"], "permalink": m["permalink"], "ts": m["timestamp"], "primera_linea": (m.get("caption") or "").split("\n")[0][:90]}
        for metrica in IG_MEDIA:
            r, e = pedir(f"{m['id']}/insights", metric=metrica)
            if not e and r.get("data"):
                fila[metrica] = r["data"][0]["values"][0]["value"]
        out.append(fila)
    return out


def stories_ig(ig, errores):
    out = []
    d, e = pedir(f"{ig}/stories", fields="id,timestamp,permalink")
    if e:
        errores.append(f"ig stories: {e}"); return out
    for s in d.get("data", []):
        fila = {"id": s["id"], "ts": s["timestamp"]}
        for m in ("reach", "replies", "navigation", "shares", "total_interactions", "views"):
            r, e = pedir(f"{s['id']}/insights", metric=m)
            if not e and r.get("data"):
                fila[m] = r["data"][0]["values"][0]["value"]
        out.append(fila)
    return out


def pagina_fb(page, errores):
    out = {}
    d, e = pedir(page, fields="fan_count,followers_count")
    if e:
        errores.append(f"fb pagina: {e}")
    else:
        out.update(d)
    for m in FB_PAGINA:
        r, e = pedir(f"{page}/insights", metric=m, period="day")
        if e:
            errores.append(f"fb {m}: {e}")
        elif r.get("data") and r["data"][0].get("values"):
            out[m] = r["data"][0]["values"][-1]["value"]
    return out


def recoger():
    ig, page = ag.secreto("IG_USER_ID"), ag.secreto("FB_PAGE_ID")
    errores = []
    cuenta, e = pedir(ig, fields="followers_count,follows_count,media_count")
    if e:
        errores.append(f"ig cuenta: {e}")
    fila = {"fecha": ag.hoy().isoformat(), "instagram": {"cuenta": cuenta, "insights": insights_cuenta_ig(ig, errores), "publicaciones": publicaciones_ig(ig, errores)},
            "facebook": pagina_fb(page, errores), "errores": errores}
    stories = stories_ig(ig, errores)
    fila["instagram"]["stories"] = stories
    with open(SALIDA, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
    registrar_patrocinadas(stories)
    print(f"Métricas guardadas ({len(errores)} métricas no disponibles).")
    if errores:
        print("\n".join(errores[:12]))


def registrar_patrocinadas(stories):
    """Relaciona las stories de hoy con las patrocinadas (por orden en el manifiesto) para el informe mensual."""
    man = ag.cargar_json(ag.dir_dia(ag.hoy()) / "manifiesto.json", {}) or {}
    est = ag.cargar_estado(ag.dir_dia(ag.hoy()))
    with open(ag.RAIZ / "registros" / "patrocinios.jsonl", "a", encoding="utf-8") as fh:
        for s in man.get("stories", []):
            if not s.get("patrocinador"):
                continue
            res = (est["publicaciones"].get(f"stories/{s['archivo']}", {}).get("instagram", {}) or {}).get("resultado") or [None]
            sid = res[0]
            ins = next((x for x in stories if x["id"] == sid), None)
            if ins:
                fh.write(json.dumps({"fecha": ag.hoy().isoformat(), "anunciante": s["patrocinador"], "alcance": ins.get("reach", 0),
                                     "interacciones": (ins.get("replies") or 0) + (ins.get("shares") or 0) + (ins.get("navigation") or 0)}, ensure_ascii=False) + "\n")


def leer(dias):
    if not SALIDA.exists():
        return []
    filas = [json.loads(l) for l in SALIDA.read_text(encoding="utf-8").splitlines() if l.strip()]
    return filas[-dias:]


def resumen(dias):
    filas = leer(dias)
    if not filas:
        return print("Sin métricas todavía.")
    print(f"Últimos {len(filas)} días de métricas")
    for f in filas:
        i = f["instagram"]
        print(f"{f['fecha']} · IG seguidores {((i.get('cuenta') or {}).get('followers_count'))} · alcance {i['insights'].get('reach')} · guardados {i['insights'].get('saves')} · "
              f"compartidos {i['insights'].get('shares')} · interacc. {i['insights'].get('total_interactions')} · FB seguidores {f['facebook'].get('followers_count')}")
    ult = filas[-1]["instagram"]["insights"]
    print("Horas con más actividad (UTC):", ult.get("horas_activas"))
    for k in ("audiencia_city", "audiencia_country", "audiencia_age"):
        print(k, ult.get(k))
    print("\nPublicaciones recientes (mejor alcance primero):")
    pubs = {}
    for f in filas:
        for p in f["instagram"]["publicaciones"]:
            pubs[p["id"]] = p
    for p in sorted(pubs.values(), key=lambda p: -(p.get("reach") or 0))[:10]:
        print(f"  {p['tipo']:<15} alcance {p.get('reach')} guardados {p.get('saved')} compartidos {p.get('shares')} · {p['primera_linea']}")


def ab():
    """Compara alcance medio de carruseles por variante de portada (A/B). Fija la ganadora con >=10 muestras por variante y >15 % de diferencia."""
    pubs = {}
    for f in leer(60):
        for p in f["instagram"]["publicaciones"]:
            pubs[p["permalink"]] = p
    por = {"A": [], "B": []}
    for p in pubs.values():
        if p["tipo"] != "CAROUSEL_ALBUM" or p.get("reach") is None:
            continue
        dia = p["ts"][:10]
        man = ag.cargar_json(ag.RAIZ / "posts" / dia / "manifiesto.json", {}) or {}
        if man.get("variante") in por:
            por[man["variante"]].append(p["reach"])
    medias = {k: (sum(v) / len(v) if v else None) for k, v in por.items()}
    res = {"muestras": {k: len(v) for k, v in por.items()}, "alcance_medio": medias}
    a, b = medias["A"], medias["B"]
    if min(len(por["A"]), len(por["B"])) >= 10 and a and b and max(a, b) / min(a, b) > 1.15:
        res["fijar"] = "A" if a > b else "B"
    ag.guardar_json(ag.RAIZ / "registros" / "ab.json", res)
    print(json.dumps(res, ensure_ascii=False, indent=1))


def mejora(titulo, motivo):
    with open(ag.RAIZ / "registros" / "mejoras.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## {ag.hoy().isoformat()} · {titulo}\n\n{motivo}\n")
    notificar.enviar(f"Mejora aplicada: {titulo}", f"{motivo}\n\n(Registrada en registros/mejoras.md. No altera las reglas del agente, la condición de Cádiz capital ni los horarios 9:00 y 19:00.)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recoger", action="store_true")
    ap.add_argument("--resumen", action="store_true")
    ap.add_argument("--dias", type=int, default=14)
    ap.add_argument("--ab", action="store_true")
    ap.add_argument("--mejora", nargs=2, metavar=("TITULO", "MOTIVO"))
    a = ap.parse_args()
    if a.recoger: recoger()
    if a.resumen: resumen(a.dias)
    if a.ab: ab()
    if a.mejora: mejora(*a.mejora)
