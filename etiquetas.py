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


def instagram_en_web(url):
    """Perfiles de Instagram enlazados en una web OFICIAL (usuario, existe_en_API, nombre real). Es la fuente más fiable para descubrir el perfil de un organizador."""
    import requests
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=UA, timeout=30)
        html = r.text if r.status_code < 400 else None
    except requests.RequestException:
        html = None
    if not html:
        try:
            import imagenes
            html = imagenes.html_con_navegador(url)
        except Exception:
            html = None
    usuarios = []
    for u in re.findall(r"instagram\.com/([A-Za-z0-9._]{3,30})/?", html or ""):
        u = u.lower().rstrip(".")
        if u not in usuarios and u not in ("p", "reel", "reels", "explore", "accounts", "stories", "tv", "about", "developer", "legal", "web", "direct"):
            usuarios.append(u)
    out = []
    for u in usuarios[:10]:
        ok, n, sg = verificar(u)
        out.append((u, ok, n, sg))
    return out


def variantes(nombre):
    """Posibles usuarios de Instagram a partir de un nombre (sin acentos, junto, con _ o . y con sufijos habituales de Cádiz)."""
    base = re.sub(r"[^a-z0-9 ]", "", _norm(nombre)).strip()
    sin_art = re.sub(r"\b(de|del|la|el|los|las|y|en)\b", " ", base)
    out = []
    for b in (base, sin_art):
        pal = b.split()
        if not pal:
            continue
        for sep in ("", "_", "."):
            out.append(sep.join(pal))
        for suf in ("cadiz", "oficial", "_oficial", "_cadiz", "cadiz_"):
            out.append("".join(pal) + suf)
        out.append("".join(pal[:2]))
        out.append("".join(pal[:1]) + "".join(pal[-1:]))
    vistos = []
    for u in out:
        if 3 <= len(u) <= 30 and u not in vistos:
            vistos.append(u)
    return vistos


def buscar(nombre, maximo=14):
    """Prueba variantes del nombre con la API oficial y devuelve [(usuario, nombre_real, seguidores)]. El agente DEBE comprobar que el nombre es el correcto y de Cádiz capital."""
    from concurrent.futures import ThreadPoolExecutor
    cand = variantes(nombre)[:maximo]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(verificar, cand))
    return [(u, n, sg) for u, (ok, n, sg) in zip(cand, res) if ok]


def para_evento(ev):
    """Usuarios (sin @) a etiquetar en un evento: etiquetas_ig explícitas válidas + coincidencias del directorio."""
    dir_ = directorio()
    texto = _norm(" ".join(str(ev.get(c) or "") for c in ("lugar", "nombre", "descripcion", "info", "organizador")))
    out = []
    for u in [limpiar(x) for x in (ev.get("etiquetas_ig") or [])]:
        if u in dir_ and u not in out:
            out.append(u)
    for ent in ev.get("entidades") or []:
        u = limpiar(ent.get("instagram"))
        if u in dir_ and u not in out:
            out.append(u)
    for u, d in dir_.items():
        if u not in out and any(re.search(c, texto) for c in d.get("claves", [])):
            out.append(u)
    return out


def descubrir(eventos):
    """Por cada entidad de cada evento que NO esté en el directorio (cuentas nuevas), busca candidatos: enlaces de Instagram en las webs
    de las fuentes del evento y variantes del nombre con la API oficial. El agente debe comprobar que el nombre devuelto es el correcto
    y de Cádiz capital, y entonces ejecutar --anadir. Devuelve {nombre_entidad: [(usuario, nombre_real, seguidores)]}."""
    dir_ = directorio()
    out = {}
    for ev in eventos:
        webs = [f.get("url") for f in ev.get("fuentes") or [] if f.get("url")]
        enlazados = []
        for w in webs[:2]:
            try:
                enlazados += [(u, n, sg) for u, ok, n, sg in instagram_en_web(w) if ok and u not in dir_]
            except Exception:
                pass
        if enlazados:
            out[f"[web de «{ev.get('nombre', '')[:40]}»]"] = enlazados
        for e in ev.get("entidades") or []:
            if limpiar(e.get("instagram")) in dir_ or e.get("nombre") in out:
                continue
            c = [x for x in buscar(e.get("nombre") or "") if x[0] not in dir_]
            out[e.get("nombre")] = c
    return out


MIN_ETIQUETAS_EVENTO = 3  # umbral de aviso: lugar + organizador + al menos una entidad o artista


def auditar(eventos, fecha=None):
    """Controla que cada evento lleve TODAS sus etiquetas. El agente declara en `entidades` quién está relacionado con el evento
    ([{"rol": "artista|organizador|lugar|institucion|patrocinador", "nombre": "…", "instagram": "usuario" | null}]).
    Devuelve [(evento, usuarios, problemas)]; los nombres sin perfil verificado se anotan en registros/etiquetas-pendientes.json."""
    dir_ = directorio()
    pend_ruta = ag.RAIZ / "registros" / "etiquetas-pendientes.json"
    pend = ag.cargar_json(pend_ruta, {}) or {}
    informe = []
    for ev in eventos:
        tags = para_evento(ev)
        problemas = []
        ents = ev.get("entidades") or []
        if not ents:
            problemas.append("sin `entidades` declaradas (artistas, organizador, lugar, instituciones)")
        roles = {str(e.get("rol", "")).lower() for e in ents}
        for rol in ("lugar", "organizador"):
            if ents and rol not in roles:
                problemas.append(f"falta la entidad con rol «{rol}»")
        for e in ents:
            u = limpiar(e.get("instagram"))
            if not u or u not in dir_:
                if not u and not e.get("buscado"):
                    problemas.append(f"perfil NO buscado todavía: {e.get('nombre')} ({e.get('rol')}); ejecuta --descubrir y marca `buscado` (fecha) si no existe")
                else:
                    problemas.append(f"sin perfil verificado: {e.get('nombre')} ({e.get('rol')})")
                pend[e.get("nombre") or "?"] = {"rol": e.get("rol"), "evento": ev.get("nombre"), "fecha": fecha or ev.get("fecha"), "instagram_probado": u or None}
        if len(tags) < MIN_ETIQUETAS_EVENTO:
            problemas.append(f"solo {len(tags)} etiqueta(s) (mínimo {MIN_ETIQUETAS_EVENTO})")
        informe.append((ev, tags, problemas))
    ag.guardar_json(pend_ruta, pend)
    return informe


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
    ap.add_argument("--descubrir", metavar="eventos.json", help="busca perfiles NUEVOS (no están en el directorio) de las entidades de cada evento")
    ap.add_argument("--auditar", metavar="eventos.json", help="informe de etiquetas por evento (entidades sin perfil, mínimos)")
    ap.add_argument("--web", nargs="+", metavar="URL", help="busca los enlaces de Instagram en webs oficiales de organizadores/recintos")
    ap.add_argument("--buscar", nargs="+", metavar="NOMBRE", help="prueba variantes de cada nombre y muestra los perfiles que existen (hay que comprobar que son los correctos)")
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
    elif a.web:
        for u in a.web:
            print(f"## {u}")
            for us, ok, n, sg in instagram_en_web(u):
                print(f"   @{us} | {'verificado API: ' + str(n) + ' (' + str(sg) + ')' if ok else 'cuenta no profesional/no verificable por API'}")
    elif a.buscar:
        for n in a.buscar:
            print(f"## {n}")
            for u, nom, sg in buscar(n):
                print(f"   @{u} | {nom} | {sg} seguidores")
    elif a.descubrir:
        import pathlib
        for nombre, cands in descubrir(ag.cargar_eventos(pathlib.Path(a.descubrir).parent)["eventos"]).items():
            print(f"## {nombre}")
            for u, n, sg in cands:
                print(f"   @{u} | {n} | {sg} seguidores  -> si es correcto: --anadir {u} \"{n}\" clave…")
            if not cands:
                print("   (sin candidatos: busca su web/prensa o márcala `buscado` con la fecha)")
    elif a.auditar:
        import pathlib
        ruta = pathlib.Path(a.auditar)
        for ev, tags, probs in auditar(ag.cargar_eventos(ruta.parent)["eventos"], fecha=ruta.parent.name):
            print(("✅ " if not probs else "⚠️ ") + ev["nombre"][:60], "->", [f"@{u}" for u in tags])
            for p in probs:
                print("     -", p)
    elif a.evento:
        for ev in ag.cargar_eventos(__import__("pathlib").Path(a.evento).parent)["eventos"]:
            print(ev["nombre"][:60], "->", [f"@{u}" for u in para_evento(ev)])
