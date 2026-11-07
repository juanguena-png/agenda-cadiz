#!/usr/bin/env python3
"""Acciones diarias de crecimiento orgánico con la API OFICIAL de Meta (sin seguir/dar like/comentar en cuentas ajenas, sin scraping).

  python crecimiento.py --aliados                 # quién nos etiqueta/comparte (GET /tags) -> registros/aliados.json
  python crecimiento.py --benchmark               # instantánea diaria de cuentas de referencia (business_discovery, datos públicos)
  python crecimiento.py --hashtags [#a #b …]      # rendimiento de hashtags (ig_hashtag_search, máx. 30 distintos/7 días) -> registros/hashtags.json
  python crecimiento.py --recomendar-hashtags N   # los N hashtags con más rendimiento para el caption de hoy
  python crecimiento.py --informe                 # informe diario (qué publicación trajo más seguidores y qué cambiar mañana)
  python crecimiento.py --semanal                 # revisión semanal (domingo): qué funciona, qué dejar de hacer
  python crecimiento.py --ab                      # experimentos A/B: frase, CTA y nº de hashtags
"""
import argparse
import json
import re
import statistics
from datetime import datetime, timedelta

import agenda as ag
from publicar import ErrorAPI, api

REG = ag.RAIZ / "registros"
ALIADOS = REG / "aliados.json"
COMPETIDORES = REG / "competidores.json"
BENCH = REG / "benchmark.jsonl"
HASHTAGS = REG / "hashtags.json"
HASHTAGS_BASE = ["cadizcapital", "quehacerencadiz", "planescadiz", "cadiz", "agendacadiz", "cadizturismo", "cadizfeelings", "cadizbonito", "andalucia", "flamencocadiz", "carnavaldecadiz", "teatrofalla"]
ROL_PESO = {"organizador": 3, "artista": 3, "lugar": 2, "institucion": 1, "patrocinador": 1}


def _leer(ruta, defecto):
    return ag.cargar_json(ruta, defecto) or defecto


# ----------------------------------------------------------------------------- A. aliados (quién nos etiqueta o comparte)
def aliados_recoger():
    ig = ag.secreto("IG_USER_ID")
    d = _leer(ALIADOS, {"cuentas": {}, "vistos": []})
    try:
        r = api("GET", f"{ig}/tags", fields="id,username,permalink,timestamp,media_type", limit=50)
    except ErrorAPI as e:
        return print(f"No se pudo leer /tags: {e}")
    nuevos = 0
    for m in r.get("data", []):
        if m["id"] in d["vistos"]:
            continue
        d["vistos"].append(m["id"])
        c = d["cuentas"].setdefault(m.get("username") or "?", {"n": 0, "ultima": None, "permalinks": []})
        c["n"] += 1
        c["ultima"] = m.get("timestamp")
        c["permalinks"] = (c["permalinks"] + [m.get("permalink")])[-5:]
        nuevos += 1
    ag.guardar_json(ALIADOS, d)
    print(f"Aliados: {nuevos} publicaciones nuevas en las que nos etiquetan; {len(d['cuentas'])} cuentas aliadas en total.")


def ranking_aliados():
    return sorted(_leer(ALIADOS, {"cuentas": {}})["cuentas"].items(), key=lambda kv: -kv[1]["n"])


# ----------------------------------------------------------------------------- B. colaboradores y comentario de cada publicación
def colaboradores(eventos, maximo=3):
    """Hasta 3 perfiles verificados (organizadores, artistas, lugares) a los que invitar como colaboradores de la publicación (API `collaborators`).
    Cuentan más los que ya nos han compartido (aliados). Nunca nuestra propia cuenta."""
    import etiquetas as et
    dir_ = et.directorio()
    aliados = dict(ranking_aliados())
    puntos = {}
    for ev in eventos:
        for e in ev.get("entidades") or []:
            u = et.limpiar(e.get("instagram"))
            if u in dir_:
                puntos[u] = puntos.get(u, 0) + ROL_PESO.get(str(e.get("rol", "")).lower(), 1) + 4 * (aliados.get(u, {}).get("n", 0) > 0)
    return [u for u, _ in sorted(puntos.items(), key=lambda kv: -kv[1])][:maximo]


FRASES_COMENTARIO = [
    "¿Cuál de estos planes te apuntas hoy? 👇",
    "Cuéntanos: ¿a cuál vas tú? 🙌",
    "¿Con quién irías a alguno de estos planes? Etiquétale 👇",
    "Si tuvieras que elegir solo uno, ¿cuál sería? 🤔",
    "¿Ya tienes plan o te unes a alguno de estos? 👀",
    "¿Qué plan te apetece más hoy? Te leemos 👇",
    "¿Te animas con alguno? Dinos cuál 😉",
    "¿Cuál te ha llamado más la atención? 🎯",
    "Hoy hay para todos los gustos: ¿cuál es el tuyo? ✨",
    "¿A qué hora te apuntas? Cuéntanos tu plan 🕘",
    "¿Alguien se viene? Deja aquí tu plan de hoy 👇",
    "¿Cuál recomendarías tú a un amigo? 💬",
    "¿Has estado ya en alguno de estos sitios? Cuéntanos 👇",
    "¿Qué plan te falta por probar? 🌟",
    "Elige uno y dinos por qué 👇",
    "¿Dónde nos vemos hoy? 😄",
    "¿Cuál es tu favorito de la lista? ❤️",
    "Responde con un emoji del plan que más te gusta 👇",
    # con la palabra clave PLANES (se envía la agenda del día por mensaje)
    "Comenta PLANES y te mandamos la agenda completa de hoy por mensaje 📩",
    "¿Quieres la lista de hoy en tu móvil? Escribe PLANES aquí abajo 👇",
    "Escribe PLANES y te enviamos todos los planes de hoy por mensaje privado ✉️",
    "¿Te lo guardas para luego? Comenta PLANES y te lo mandamos 📲",
    "Dinos qué plan eliges y comenta PLANES si quieres la agenda por mensaje 😉",
    "Un comentario con la palabra PLANES y la agenda de hoy llega a tu bandeja 📥",
]

# con la palabra clave FINDE (lista de viernes a domingo); solo de miércoles a domingo
FRASES_FINDE = [
    "¿Y el finde? Comenta FINDE y te mandamos los planes de viernes a domingo 📩",
    "Escribe FINDE y te enviamos por mensaje todos los planes del fin de semana ✉️",
    "¿Ya tienes plan para el finde? Comenta FINDE y te lo mandamos 👇",
    "Si quieres los planes del finde en tu móvil, comenta FINDE 📲",
]


def comentario_post(eventos, fecha):
    """Primer comentario de la cuenta en el carrusel: UNA frase corta y cambiante que invite a comentar (sin repetir la lista del día; la API no permite fijarlo).
    La frase rota cada día sin repetirse hasta agotar el banco."""
    d = ag.a_fecha(fecha)
    banco = list(FRASES_COMENTARIO)
    if d.weekday() >= 2:  # miércoles a domingo: también las de la palabra clave FINDE
        banco += FRASES_FINDE
    return banco[d.toordinal() % len(banco)]


# ----------------------------------------------------------------------------- C. experimentos A/B
def experimentos(fecha):
    """Variables de prueba por día (se anotan en manifiesto.json): frase del gancho (A pregunta / B dato), CTA (A guardar / B compartir) y nº de hashtags (5 / 8)."""
    o = ag.a_fecha(fecha).toordinal()
    fijados = _leer(REG / "ab.json", {}).get("fijados", {})
    return {"frase": fijados.get("frase") or ("A" if o % 2 == 0 else "B"), "cta": fijados.get("cta") or ("A" if (o // 2) % 2 == 0 else "B"),
            "hashtags": fijados.get("hashtags") or ("5" if (o // 4) % 2 == 0 else "8")}


def _filas():
    import metricas
    return metricas.leer(60)


def _posts():
    pubs = {}
    for f in _filas():
        for p in f["instagram"]["publicaciones"]:
            pubs[p["permalink"]] = p
    return list(pubs.values())


def ab():
    res = {"experimentos": {}, "fijados": _leer(REG / "ab.json", {}).get("fijados", {})}
    for var in ("frase", "cta", "hashtags"):
        grupos = {}
        for p in _posts():
            if p["tipo"] != "CAROUSEL_ALBUM" or p.get("reach") is None:
                continue
            man = ag.cargar_json(ag.RAIZ / "posts" / p["ts"][:10] / "manifiesto.json", {}) or {}
            v = (man.get("experimentos") or {}).get(var) or (man.get("variante") if var == "frase" else None)
            if v:
                grupos.setdefault(v, []).append({"reach": p["reach"], "follows": p.get("follows") or 0, "saved": p.get("saved") or 0})
        stats = {k: {"n": len(v), "alcance": round(statistics.mean(x["reach"] for x in v), 1), "seguidores": round(statistics.mean(x["follows"] for x in v), 2),
                     "guardados": round(statistics.mean(x["saved"] for x in v), 2)} for k, v in grupos.items()}
        res["experimentos"][var] = stats
        if len(stats) == 2 and min(s["n"] for s in stats.values()) >= 10:
            (a, sa), (b, sb) = list(stats.items())
            ga, gb = sa["seguidores"] * 5 + sa["alcance"] / 100, sb["seguidores"] * 5 + sb["alcance"] / 100
            if max(ga, gb) / max(min(ga, gb), 0.01) > 1.15:
                res["fijados"][var] = a if ga > gb else b
    ag.guardar_json(REG / "ab.json", res)
    print(json.dumps(res, ensure_ascii=False, indent=1))


# ----------------------------------------------------------------------------- D. benchmark de cuentas de referencia (datos públicos, API oficial)
def benchmark():
    ig = ag.secreto("IG_USER_ID")
    cfg = _leer(COMPETIDORES, {"cuentas": ["gaditanisimamente"]})
    for u in cfg["cuentas"]:
        try:
            b = api("GET", ig, fields=f"business_discovery.username({u}){{username,followers_count,media_count,media.limit(12){{like_count,comments_count,timestamp,media_type}}}}")["business_discovery"]
        except (ErrorAPI, KeyError) as e:
            print(f"@{u}: no disponible ({e})"); continue
        ms = b.get("media", {}).get("data", [])
        fila = {"fecha": ag.hoy().isoformat(), "cuenta": u, "seguidores": b.get("followers_count"), "publicaciones": b.get("media_count"),
                "likes_medios": round(statistics.mean(m.get("like_count", 0) for m in ms), 1) if ms else None,
                "comentarios_medios": round(statistics.mean(m.get("comments_count", 0) for m in ms), 1) if ms else None,
                "formatos": {t: sum(1 for m in ms if m["media_type"] == t) for t in {m["media_type"] for m in ms}}, "horas_publicacion": sorted(m["timestamp"][11:13] for m in ms)}
        with open(BENCH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
        print(f"@{u}: {fila['seguidores']} seguidores · likes medios {fila['likes_medios']} · formatos {fila['formatos']}")


# ----------------------------------------------------------------------------- E. hashtags (investigación con la búsqueda oficial; máx. 30 distintos cada 7 días)
def hashtags_investigar(lista=None):
    ig = ag.secreto("IG_USER_ID")
    d = _leer(HASHTAGS, {"consultas": {}, "datos": {}})
    hace7 = (ag.ahora() - timedelta(days=7)).isoformat()
    usados = {h for h, ts in d["consultas"].items() if ts >= hace7}
    for h in [x.lstrip("#").lower() for x in (lista or HASHTAGS_BASE)]:
        if h not in usados and len(usados) >= 28:
            print(f"#{h}: límite de 30 hashtags/7 días casi alcanzado; se retoma la semana que viene"); continue
        try:
            hid = api("GET", "ig_hashtag_search", user_id=ig, q=h)["data"][0]["id"]
            ms = api("GET", f"{hid}/top_media", user_id=ig, fields="id,like_count,comments_count,timestamp", limit=9).get("data", [])
        except (ErrorAPI, IndexError, KeyError) as e:
            print(f"#{h}: {str(e)[:80]}"); continue
        usados.add(h)
        d["consultas"][h] = ag.ahora().isoformat(timespec="seconds")
        inter = [m.get("like_count", 0) + 3 * m.get("comments_count", 0) for m in ms]
        d["datos"][h] = {"actualizado": ag.hoy().isoformat(), "interacciones_top_media": round(statistics.mean(inter), 1) if inter else None, "muestras": len(inter)}
        print(f"#{h}: interacciones medias del top {d['datos'][h]['interacciones_top_media']}")
    ag.guardar_json(HASHTAGS, d)


def hashtags_recomendar(n):
    datos = _leer(HASHTAGS, {"datos": {}})["datos"]
    fijos = ["cadizcapital", "planescadiz"]  # identidad de marca: siempre
    resto = [h for h, v in sorted(datos.items(), key=lambda kv: -(kv[1].get("interacciones_top_media") or 0)) if h not in fijos]
    print(" ".join("#" + h for h in (fijos + resto)[:n]))


# ----------------------------------------------------------------------------- F. informe diario y revisión semanal
def _por_formato(posts):
    out = {}
    for p in posts:
        out.setdefault(p["tipo"], []).append(p)
    return out


def informe():
    posts = [p for p in _posts() if p["ts"][:10] >= (ag.hoy() - timedelta(days=2)).isoformat()]
    filas = _filas()
    seg = [(f["fecha"], ((f["instagram"].get("cuenta") or {}).get("followers_count"))) for f in filas][-8:]
    L = [f"# Informe diario {ag.hoy().isoformat()}", "", f"Seguidores IG (últimos días): {', '.join(f'{d[5:]}: {s}' for d, s in seg)}", ""]
    if posts:
        L.append("| Publicación | Formato | Alcance | Guardados | Compartidos | Seguidores nuevos |")
        L.append("|---|---|---|---|---|---|")
        for p in sorted(posts, key=lambda p: -(p.get("follows") or 0) * 1000 - (p.get("reach") or 0)):
            L.append(f"| {p['primera_linea'][:50]} | {p['tipo']} | {p.get('reach')} | {p.get('saved')} | {p.get('shares')} | {p.get('follows')} |")
    pf = _por_formato([p for p in _posts() if p.get("reach") is not None])
    medias = {t: statistics.mean(p["reach"] for p in v) for t, v in pf.items() if len(v) >= 2}
    L += ["", "Alcance medio por formato (últimos 14 días): " + ", ".join(f"{t} {m:.0f}" for t, m in medias.items())]
    mejor = max(medias, key=medias.get) if medias else None
    if mejor:
        L.append(f"**Para mañana:** priorizar el formato «{mejor}» (el de mayor alcance medio) y repetir la estructura de la publicación con más seguidores nuevos.")
    ruta = REG / "informes" / f"{ag.hoy().isoformat()}.md"
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def semanal():
    filas = _filas()[-8:]
    seg = [((f["instagram"].get("cuenta") or {}).get("followers_count")) for f in filas]
    seg = [s for s in seg if s is not None]
    crec = (seg[-1] - seg[0]) if len(seg) >= 2 else None
    posts = [p for p in _posts() if p.get("reach") is not None and p["ts"][:10] >= (ag.hoy() - timedelta(days=7)).isoformat()]
    L = [f"# Revisión semanal {ag.hoy().isoformat()}", "", f"Crecimiento de seguidores en 7 días: {crec}"]
    if posts:
        orden = sorted(posts, key=lambda p: -(p.get("follows") or 0) * 1000 - p["reach"])
        L += ["", "Mejores:"] + [f"- {p['tipo']} · alcance {p['reach']} · +{p.get('follows') or 0} seguidores · {p['primera_linea'][:60]}" for p in orden[:3]]
        L += ["", "Peores (candidatos a dejar de hacer o cambiar):"] + [f"- {p['tipo']} · alcance {p['reach']} · {p['primera_linea'][:60]}" for p in orden[-3:]]
    L += ["", "Aliados que más nos comparten: " + (", ".join(f"@{u} ({v['n']})" for u, v in ranking_aliados()[:8]) or "ninguno todavía")]
    bench = [json.loads(x) for x in BENCH.read_text(encoding="utf-8").splitlines()] if BENCH.exists() else []
    if bench:
        ult = {}
        for b in bench:
            ult[b["cuenta"]] = b
        L += ["", "Cuentas de referencia: " + "; ".join(f"@{c}: {b['seguidores']} seg., likes medios {b['likes_medios']}" for c, b in ult.items())]
    ab_ = _leer(REG / "ab.json", {})
    L += ["", "Experimentos A/B: " + json.dumps(ab_.get("experimentos", {}), ensure_ascii=False)]
    ruta = REG / "informes" / f"semanal-{ag.hoy().isoformat()}.md"
    ruta.parent.mkdir(exist_ok=True)
    ruta.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--aliados", action="store_true")
    ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--hashtags", nargs="*")
    ap.add_argument("--recomendar-hashtags", type=int)
    ap.add_argument("--informe", action="store_true")
    ap.add_argument("--semanal", action="store_true")
    ap.add_argument("--ab", action="store_true")
    a = ap.parse_args()
    if a.aliados:
        aliados_recoger()
    if a.benchmark:
        benchmark()
    if a.hashtags is not None:
        hashtags_investigar(a.hashtags or None)
    if a.recomendar_hashtags:
        hashtags_recomendar(a.recomendar_hashtags)
    if a.informe:
        informe()
    if a.semanal:
        semanal()
    if a.ab:
        ab()
