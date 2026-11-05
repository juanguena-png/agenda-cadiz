#!/usr/bin/env python3
"""Rutina diaria de crecimiento HECHA POR UNA PERSONA desde el móvil (nada se automatiza en Instagram: sin seguir, dar like ni comentar por script).
El script solo PREPARA la lista con la API oficial (business_discovery: datos públicos de cuentas profesionales) y envía el correo de las 23:30:
  A. 15 cuentas gaditanas con las que interactuar (enlace a su última publicación + comentario sugerido, escrito por el agente a partir de lo que dice la publicación)
  B. 10 cuentas a las que seguir (probables seguidores de vuelta)
  C. 12 cuentas que se siguieron hace ≥ 7 días: comprobar si «Te sigue» y, si no, dejar de seguir (el seguido debe ser siempre inferior al de seguidores)

  python rutina.py --preparar                       # arma registros/rutina/AAAA-MM-DD.json (cuentas, enlaces y textos de las publicaciones)
  (el agente escribe registros/rutina/AAAA-MM-DD-comentarios.json: {"usuario": "comentario"})
  python rutina.py --enviar [--esperar-hasta 23:30] [--prueba]
"""
import argparse
import html as H
import json
import re
import time
from datetime import date, datetime, timedelta

import agenda as ag
from publicar import ErrorAPI, api

REG = ag.RAIZ / "registros"
POOL = REG / "pool_cuentas.json"
LIBRO = REG / "seguimiento.json"  # cuentas cuyo seguimiento se recomendó y fecha (solo cuentas profesionales públicas; nunca listas de seguidores)
DIR = REG / "rutina"
NO_CULTURAL = re.compile(r"boda|comuni[oó]n|inmobili|cl[ií]nica|dental|abogad|seguros|ropa|moda mujer|peluquer|tatu|gimnasio|fitness|estetica|est[eé]tica", re.I)
CADIZ = re.compile(r"c[aá]diz|gaditan|bah[ií]a de c|la caleta|la vi[ñn]a|el populo|santa mar[ií]a del mar|carnaval|chirigota|comparsa|tía norica|la isla", re.I)
OTROS = re.compile(r"sevilla|m[aá]laga|madrid|jerez|el puerto|chiclana|san fernando|algeciras|barcelona|valencia|granada|c[oó]rdoba", re.I)
CAMPOS = ("business_discovery.username({u}){{username,name,biography,website,followers_count,follows_count,media_count,"
          "media.limit(3){{permalink,timestamp,caption,media_type,like_count,comments_count}}}}")
NO_COMENTAR = {"puertodecadiz", "zfcadiz", "camaracadiz", "comcadiz", "colegioabogadoscadiz", "caixabank", "unicajabanco", "culturagob", "turismoandaluz", "ifef_cadiz", "diputaciondecadiz"}  # poco encaje para comentarios sobre planes
GRANDES = 12000  # por encima de esto casi nunca siguen de vuelta: solo para interactuar (A), no para seguir (B)


def _j(ruta, defecto):
    return ag.cargar_json(ruta, defecto) or defecto


def perfil(u):
    try:
        return api("GET", ag.secreto("IG_USER_ID"), fields=CAMPOS.format(u=u))["business_discovery"]
    except (ErrorAPI, KeyError):
        return None


def semillas():
    import etiquetas as et
    s = {u: "directorio" for u in et.directorio()}
    for u in _j(REG / "competidores.json", {}).get("cuentas", []):
        s[u] = "agenda"
    for u in _j(REG / "aliados.json", {}).get("cuentas", {}):
        s[u] = "aliado"
    for f in sorted((ag.RAIZ / "posts").glob("20*/eventos.json"))[-14:]:
        for ev in (_j(f, {}).get("eventos") or []):
            for e in ev.get("entidades") or []:
                u = et.limpiar(e.get("instagram"))
                if u:
                    s.setdefault(u, "evento")
    return s


def actualizar_pool(max_consultas=60):
    """Refresca perfiles de las semillas y descubre cuentas nuevas por las menciones (@usuario) de sus publicaciones."""
    pool = _j(POOL, {"cuentas": {}})
    hoy = ag.hoy().isoformat()
    cola = [(u, o) for u, o in semillas().items()]
    cola += [(u, "mencionada") for u, c in pool["cuentas"].items() if c.get("origen") == "pendiente"]
    hechas = 0
    for u, origen in cola:
        c = pool["cuentas"].get(u)
        if c and c.get("origen") != "pendiente" and c.get("actualizado", "") >= (ag.hoy() - timedelta(days=3)).isoformat():
            continue
        if hechas >= max_consultas:
            break
        p = perfil(u)
        hechas += 1
        if not p:
            pool["cuentas"][u] = {"origen": "no_profesional", "actualizado": hoy}
            continue
        ms = p.get("media", {}).get("data", [])
        pool["cuentas"][u] = {"origen": (c or {}).get("origen_real") or origen if (c or {}).get("origen") == "pendiente" else origen, "origen_real": origen,
                              "nombre": p.get("name"), "bio": (p.get("biography") or "")[:200], "seguidores": p.get("followers_count"), "siguiendo": p.get("follows_count"),
                              "publicaciones": p.get("media_count"), "ultima": ms[0] if ms else None, "actualizado": hoy}
        for m in ms:  # descubrimiento por menciones
            for v in re.findall(r"@([A-Za-z0-9._]{3,30})", m.get("caption") or ""):
                v = v.lower().rstrip(".")
                if v not in pool["cuentas"] and v != "planesencadiz":
                    pool["cuentas"][v] = {"origen": "pendiente", "mencionada_por": u, "actualizado": ""}
    ag.guardar_json(POOL, pool)
    return pool


def _relevante(c):
    if c.get("origen_real") == "buscada":  # el agente ya comprobó su relación con Cádiz al buscarla
        return True
    t = " ".join(str(c.get(k) or "") for k in ("nombre", "bio"))
    return bool(CADIZ.search(t)) and not (OTROS.search(t) and not re.search(r"c[aá]diz", t, re.I))


def _reciente(c, dias):
    ult = c.get("ultima") or {}
    return bool(ult.get("timestamp")) and ult["timestamp"][:10] >= (ag.hoy() - timedelta(days=dias)).isoformat()


def preparar():
    pool = actualizar_pool()
    libro = _j(LIBRO, {"cuentas": {}})
    hoy = ag.hoy()
    ya = lambda u, dias: u in libro["cuentas"] and any(x >= (hoy - timedelta(days=dias)).isoformat() for x in libro["cuentas"][u].get("interacciones", []) + [libro["cuentas"][u].get("seguir", "")])
    cuentas = {u: c for u, c in pool["cuentas"].items() if c.get("seguidores") is not None and c.get("origen") not in ("no_profesional", "pendiente")}
    # A. interactuar: cuentas con publicación reciente (≤10 días), variadas
    peso = {"aliado": 6, "evento": 4, "directorio": 4, "agenda": 3, "mencionada": 2}
    A = sorted((u for u, c in cuentas.items() if _reciente(c, 10) and not ya(u, 7) and u != "planesencadiz" and u not in NO_COMENTAR and len(((c.get("ultima") or {}).get("caption") or "")) >= 40),
               key=lambda u: -(peso.get(cuentas[u].get("origen_real"), 1) + (2 if _relevante(cuentas[u]) else 0) + (1 if (cuentas[u]["seguidores"] or 0) < GRANDES else 0)))
    A = A[:15]
    # B. seguir: locales, activas, tamaño con probabilidad de seguir de vuelta
    B = [u for u, c in sorted(cuentas.items(), key=lambda kv: -(kv[1].get("siguiendo") or 0) / max(kv[1].get("seguidores") or 1, 1))
         if u not in libro["cuentas"] and u not in A and 80 <= (c.get("seguidores") or 0) <= GRANDES and (c.get("siguiendo") or 0) >= 0.4 * (c.get("seguidores") or 1)
         and _reciente(c, 14) and _relevante(c) and c.get("origen_real") != "directorio" and not NO_CULTURAL.search((c.get("nombre") or "") + " " + (c.get("bio") or ""))][:10]
    # C. dejar de seguir: seguidas hace ≥ 7 días y sin revisar
    C = sorted((u for u, v in libro["cuentas"].items() if v.get("seguir") and not v.get("revisada") and v["seguir"] <= (hoy - timedelta(days=7)).isoformat()), key=lambda u: libro["cuentas"][u]["seguir"])[:12]
    mi = api("GET", ag.secreto("IG_USER_ID"), fields="followers_count,follows_count")
    def ficha(u):
        c = cuentas.get(u) or pool["cuentas"].get(u) or {}
        ult = c.get("ultima") or {}
        return {"usuario": u, "nombre": c.get("nombre"), "seguidores": c.get("seguidores"), "bio": c.get("bio"), "origen": c.get("origen_real"),
                "publicacion": ult.get("permalink"), "texto_publicacion": (ult.get("caption") or "")[:600], "tipo": ult.get("media_type"), "fecha_publicacion": (ult.get("timestamp") or "")[:10]}
    DIR.mkdir(exist_ok=True)
    datos = {"fecha": hoy.isoformat(), "yo": {"seguidores": mi.get("followers_count"), "seguidos": mi.get("follows_count")}, "A": [ficha(u) for u in A], "B": [ficha(u) for u in B], "C": [ficha(u) | {"seguida_el": libro["cuentas"][u]["seguir"]} for u in C]}
    ag.guardar_json(DIR / f"{hoy.isoformat()}.json", datos)
    print(f"A {len(A)} · B {len(B)} · C {len(C)} · yo {datos['yo']} · pool {len(cuentas)} cuentas")
    return datos


# ----------------------------------------------------------------------------- correo (HTML pensado para el móvil)
def _a(url, txt):
    return f'<a href="{H.escape(url)}" style="color:#0a66c2;text-decoration:none;font-weight:700">{H.escape(txt)}</a>'


def _boton(url, txt, color="#0a66c2"):
    return f'<a href="{H.escape(url)}" style="display:inline-block;background:{color};color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px">{H.escape(txt)}</a>'


PAGINA_COPIAR = "https://raw.githack.com/juanguena-png/agenda-cadiz/main/web/copiar.html"


def _enlace_copiar(publicacion, comentario):
    """Los correos no ejecutan JavaScript: el botón abre una página sencilla que copia el comentario al portapapeles (al tocar) y abre la publicación."""
    from urllib.parse import quote
    return f"{PAGINA_COPIAR}#p={quote(publicacion, safe='')}&t={quote(comentario or '', safe='')}"


def construir_correo(d, comentarios):
    perfil_url = lambda u: f"https://www.instagram.com/{u}/"
    seg, sig = d["yo"]["seguidores"], d["yo"]["seguidos"]
    ok = sig is not None and seg is not None and sig < seg
    h = ['<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:640px;margin:auto;color:#14213d;line-height:1.45">',
         f'<h2 style="margin:0 0 4px">Rutina de hoy · {d["fecha"]}</h2>',
         f'<p style="margin:0 0 12px;color:#555">Unos 10-15 minutos desde el móvil. Hazlo con calma, a mano y repartido en 2-3 tandas; sin copiar y pegar el mismo comentario.</p>',
         f'<div style="background:{"#e8f5e9" if ok else "#fdecea"};padding:10px 12px;border-radius:8px;margin-bottom:16px">Seguidores <b>{seg}</b> · Seguidos <b>{sig}</b> '
         f'{"✅ vamos bien: seguimos a menos gente de la que nos sigue" if ok else "⚠️ ojo: seguimos a más gente de la que nos sigue; prioriza la parte 3"}</div>']
    def seccion(titulo, sub, items, fn):
        h.append(f'<h3 style="margin:22px 0 2px;border-top:2px solid #e5e7eb;padding-top:14px">{titulo}</h3><p style="margin:0 0 10px;color:#555">{sub}</p>')
        if not items and titulo.startswith("3"):
            h.append('<div style="border:1px solid #e5e7eb;border-radius:10px;padding:12px"><p style="margin:0 0 8px">Todavía no tengo la lista de a quién seguimos (Instagram no me la da por su API), así que hoy hazlo desde tu lista de «Seguidos»:</p>'
                     '<ol style="margin:0 0 10px;padding-left:20px"><li>Abre «Seguidos» (botón) y ordena por <b>«Fecha de seguimiento: más antiguos primero»</b>.</li>'
                     '<li>En las 12 primeras cuentas, mira si debajo del nombre pone «Te sigue». Si <b>no</b> lo pone, toca «Siguiendo» → «Dejar de seguir».</li>'
                     '<li>No dejes de seguir a organizadores o recintos clave aunque no nos sigan (Falla, Cajasol, Ayuntamiento…).</li></ol>'
                     + _boton("https://www.instagram.com/planesencadiz/following/", "Abrir «Seguidos»", "#c62828") + '</div>')
        elif not items:
            h.append('<p style="color:#777"><i>Hoy no hay cuentas en esta parte.</i></p>')
        for i, it in enumerate(items, 1):
            h.append(f'<div style="border:1px solid #e5e7eb;border-radius:10px;padding:12px;margin-bottom:10px"><div style="font-size:13px;color:#777">{i}.</div>{fn(it)}</div>')
    def fa(it):
        u = it["usuario"]
        com = comentarios.get(u) or "(sin comentario sugerido: escribe algo concreto sobre su publicación)"
        t = H.escape((it.get("texto_publicacion") or "")[:160].replace("\n", " "))
        return (f'<div>{_a(perfil_url(u), "@" + u)} <span style="color:#777;font-size:13px">· {it.get("seguidores") or "?"} seguidores</span></div>'
                f'<div style="color:#555;font-size:13px;margin:4px 0 8px">«{t}…»</div>'
                f'<div style="background:#f5f7fa;border-left:4px solid #0a66c2;padding:8px 10px;margin-bottom:8px">{H.escape(com)}</div>'
                + (_boton(_enlace_copiar(it["publicacion"], com), "Copiar comentario y abrir publicación") + f'<div style="margin-top:8px;font-size:13px"><a href="{H.escape(it["publicacion"])}" style="color:#777">o abrir solo la publicación</a></div>' if it.get("publicacion") else _boton(perfil_url(u), "Abrir perfil")))
    def fb(it):
        u = it["usuario"]
        return (f'<div>{_a(perfil_url(u), "@" + u)} <span style="color:#777;font-size:13px">· {it.get("seguidores") or "?"} seguidores</span></div>'
                f'<div style="color:#555;font-size:13px;margin:4px 0 8px">{H.escape((it.get("bio") or "")[:120])}</div>' + _boton(perfil_url(u), "Abrir perfil y seguir", "#2e7d32"))
    def fc(it):
        u = it["usuario"]
        return (f'<div>{_a(perfil_url(u), "@" + u)} <span style="color:#777;font-size:13px">· seguida el {it.get("seguida_el")}</span></div>'
                '<div style="color:#555;font-size:13px;margin:4px 0 8px">Si bajo su nombre pone «Te sigue», déjala. Si no, toca «Siguiendo» → «Dejar de seguir».</div>' + _boton(perfil_url(u), "Abrir perfil", "#c62828"))
    seccion("1 · Comentar (15)", "Entra en su última publicación y deja el comentario sugerido (puedes cambiarlo a tu gusto). Un «me gusta» también ayuda.", d["A"], fa)
    seccion("2 · Seguir (10)", "Cuentas gaditanas y activas que suelen seguir de vuelta. Síguelas; mañana no se repiten.", d["B"], fb)
    seccion("3 · Dejar de seguir (12)", "Seguidas por nosotros hace una semana o más. Comprueba si nos siguen y, si no, deja de seguirlas.", d["C"], fc)
    h.append('<p style="color:#888;font-size:12px;margin-top:20px">Consejos: no más de 10-15 acciones seguidas sin pausa, nada de comentarios iguales, y si Instagram avisa de «acción bloqueada» para y retoma al día siguiente.</p></div>')
    texto = [f"Rutina de hoy {d['fecha']} · seguidores {seg} · seguidos {sig}", "", "1 · COMENTAR"] + [f"{i}. https://www.instagram.com/{x['usuario']}/ · {x.get('publicacion') or ''}\n   {comentarios.get(x['usuario'], '')}" for i, x in enumerate(d["A"], 1)]
    texto += ["", "2 · SEGUIR"] + [f"{i}. https://www.instagram.com/{x['usuario']}/" for i, x in enumerate(d["B"], 1)]
    texto += ["", "3 · DEJAR DE SEGUIR (si no pone «Te sigue»)"] + [f"{i}. https://www.instagram.com/{x['usuario']}/" for i, x in enumerate(d["C"], 1)]
    return "\n".join(texto), "".join(h)


def enviar(esperar=None, prueba=False):
    import notificar
    hoy = ag.hoy().isoformat()
    d = _j(DIR / f"{hoy}.json", None)
    if not d or not d.get("A"):
        return print("Falta preparar la rutina de hoy (rutina.py --preparar).")
    com = _j(DIR / f"{hoy}-comentarios.json", {})
    faltan = [x["usuario"] for x in d["A"] if not com.get(x["usuario"])]
    if faltan:
        print("AVISO: faltan comentarios sugeridos para:", ", ".join(faltan))
    texto, cuerpo = construir_correo(d, com)
    if esperar:
        hh, mm = map(int, esperar.split(":"))
        objetivo = ag.ahora().replace(hour=hh, minute=mm, second=0, microsecond=0)
        while ag.ahora() < objetivo:
            time.sleep(min(30, max(1, (objetivo - ag.ahora()).total_seconds())))
    asunto = f"Rutina 23:30{' (PRUEBA)' if prueba else ''} · {len(d['A'])} comentar · {len(d['B'])} seguir · {len(d['C'])} dejar de seguir"
    ok = notificar.enviar(asunto, texto, html=cuerpo)
    print("Correo enviado" if ok else "No se pudo enviar el correo")
    if ok:  # anota en el libro lo que se recomendó hoy
        libro = _j(LIBRO, {"cuentas": {}})
        for x in d["A"]:
            libro["cuentas"].setdefault(x["usuario"], {}).setdefault("interacciones", []).append(hoy)
        for x in d["B"]:
            libro["cuentas"].setdefault(x["usuario"], {})["seguir"] = hoy
        for x in d["C"]:
            libro["cuentas"].setdefault(x["usuario"], {})["revisada"] = hoy
        ag.guardar_json(LIBRO, libro)


def anadir(usuarios, origen="buscada"):
    """Añade al pool cuentas encontradas (búsquedas, recomendaciones…) tras comprobar con la API oficial que son profesionales públicas."""
    pool = _j(POOL, {"cuentas": {}})
    for u in usuarios:
        u = u.lstrip("@").lower().rstrip("/")
        p = perfil(u)
        if not p:
            print(f"@{u}: no verificable (cuenta personal o inexistente)"); continue
        ms = p.get("media", {}).get("data", [])
        pool["cuentas"][u] = {"origen": origen, "origen_real": origen, "nombre": p.get("name"), "bio": (p.get("biography") or "")[:200], "seguidores": p.get("followers_count"),
                              "siguiendo": p.get("follows_count"), "publicaciones": p.get("media_count"), "ultima": ms[0] if ms else None, "actualizado": ag.hoy().isoformat()}
        print(f"@{u}: {p.get('name')} · {p.get('followers_count')} seg. · {(p.get('biography') or '')[:70]!r}")
    ag.guardar_json(POOL, pool)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preparar", action="store_true")
    ap.add_argument("--enviar", action="store_true")
    ap.add_argument("--esperar-hasta")
    ap.add_argument("--prueba", action="store_true")
    ap.add_argument("--anadir", nargs="+")
    a = ap.parse_args()
    if a.anadir:
        anadir(a.anadir)
    if a.preparar:
        preparar()
    if a.enviar:
        enviar(a.esperar_hasta, a.prueba)
