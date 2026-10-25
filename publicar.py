#!/usr/bin/env python3
"""Publica en Instagram (Graph API) y replica en la página de Facebook.

  python publicar.py --fecha AAAA-MM-DD --tipo diario|noche|finde|reel|mensual
  python publicar.py --diagnostico                  # comprueba token, límite de publicaciones y acceso a URLs
  python publicar.py --fecha F --marcar-revision    # el agente confirma que ha recomprobado las fuentes antes de publicar

MODO=borrador (por defecto): prepara y muestra lo que haría, sin llamar a la API de publicación ni subir nada.
MODO=publicar: publica. Lo que estado.json marca como "publicado" no se repite.
Tokens: META_TOKEN puede ser una variable normal o un 'Secreto de red' inyectado por el proxy (la sesión no lo ve):
en ese caso las peticiones se envían igualmente a graph.facebook.com sin access_token explícito.
"""
import argparse
import json
import re
import subprocess
import sys
import time

import requests

import agenda as ag
import notificar

HOST = "https://graph.facebook.com"
VERSION = ag.secreto("GRAPH_VERSION") or "v23.0"
CODIGOS_TEMPORALES = {1, 2, 4, 17, 32, 341, 368, 613}


class ErrorAPI(Exception):
    def __init__(self, msg, codigo=None, temporal=False):
        super().__init__(msg)
        self.codigo, self.temporal = codigo, temporal


# ---------------------------------------------------------------- capa HTTP
def api(metodo, ruta, reintentos=4, **params):
    """Llamada a la Graph API con reintentos y espera exponencial ante errores temporales.
    El token (META_TOKEN) se envía como cabecera Bearer solo si es visible; si no, lo añade el proxy del entorno."""
    cab = {}
    tok = ag.secreto("META_TOKEN")
    if tok:
        cab["Authorization"] = f"Bearer {tok}"
    url = ruta if ruta.startswith("http") else f"{HOST}/{VERSION}/{ruta.lstrip('/')}"
    params = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items() if v is not None}
    for i in range(reintentos + 1):
        try:
            r = requests.request(metodo, url, headers=cab, **({"params": params} if metodo == "GET" else {"data": params}), timeout=90)
            datos = r.json() if r.content else {}
        except (requests.RequestException, ValueError) as e:
            if i < reintentos:
                time.sleep(2 ** (i + 1)); continue
            raise ErrorAPI(f"red: {e}", temporal=True)
        if "error" not in datos:
            return datos
        err = datos["error"]
        temporal = err.get("is_transient") or err.get("code") in CODIGOS_TEMPORALES or r.status_code >= 500
        if temporal and i < reintentos:
            time.sleep(2 ** (i + 1)); continue
        raise ErrorAPI(f"{err.get('message')} (code {err.get('code')}/{err.get('error_subcode')})", err.get("code"), temporal)


# ---------------------------------------------------------------- token y límites
def comprobar_token():
    """debug_token si el token es visible; si lo inyecta el proxy, se valida con una lectura /me."""
    tok = ag.secreto("META_TOKEN")
    try:
        if tok:
            d = api("GET", "debug_token", input_token=tok)["data"]
            if not d.get("is_valid"):
                return False, f"debug_token: no válido ({d.get('error', {}).get('message', '')})", d
            return True, "token válido", d
        d = api("GET", "me", fields="id,name")
        return True, f"token inyectado por proxy; /me -> {d.get('name')}", d
    except ErrorAPI as e:
        return False, str(e), {}


def limite_publicaciones():
    d = api("GET", f"{ag.secreto('IG_USER_ID')}/content_publishing_limit", fields="config,quota_usage")
    fila = (d.get("data") or [{}])[0]
    return fila.get("quota_usage", 0), (fila.get("config") or {}).get("quota_total", 100)


# ---------------------------------------------------------------- URLs públicas (raw.githubusercontent.com)
def repo_github():
    r = ag.secreto("GITHUB_REPO")
    if r:
        return r
    url = subprocess.run(["git", "-C", str(ag.RAIZ), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    m = re.search(r"github\.com[:/]+([^/]+/[^/.]+)", url)
    return m.group(1) if m else ag.salir("No se puede deducir GITHUB_REPO")


def url_publica(ruta):
    rel = ruta.resolve().relative_to(ag.RAIZ).as_posix()
    return f"https://raw.githubusercontent.com/{repo_github()}/main/{rel}"


def subir_a_main(carpeta, fecha):
    """Commit y push de la carpeta del día a main (repo público)."""
    rel = carpeta.resolve().relative_to(ag.RAIZ).as_posix()
    g = lambda *a: subprocess.run(["git", "-C", str(ag.RAIZ), *a], capture_output=True, text=True)
    g("add", "-f", rel)
    if g("diff", "--cached", "--quiet", "--", rel).returncode != 0:
        c = g("commit", "-m", f"posts {fecha}: imágenes y vídeo para publicar")
        if c.returncode:
            raise ErrorAPI(f"git commit: {c.stderr[-300:]}")
    for i in range(4):
        p = g("push", "origin", "HEAD:main")
        if p.returncode == 0:
            return
        time.sleep(2 ** (i + 1))
    raise ErrorAPI(f"git push a main falló: {p.stderr[-300:]}")


def esperar_200(url, intentos=30):
    for _ in range(intentos):
        try:
            if requests.head(url, timeout=15, allow_redirects=True).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(6)
    raise ErrorAPI(f"La URL pública no responde 200: {url}")


# ---------------------------------------------------------------- Instagram
def ig_esperar(cid, intentos=60, pausa=5):
    for _ in range(intentos):
        s = api("GET", cid, fields="status_code,status")
        if s.get("status_code") == "FINISHED":
            return
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise ErrorAPI(f"contenedor {cid}: {s.get('status_code')} {s.get('status')}")
        time.sleep(pausa)
    raise ErrorAPI(f"contenedor {cid}: tiempo de espera agotado")


def ig_publicar(cid):
    ig = ag.secreto("IG_USER_ID")
    r = api("POST", f"{ig}/media_publish", creation_id=cid)
    perma = api("GET", r["id"], fields="permalink").get("permalink")
    return r["id"], perma


def ig_carrusel(urls, alts, caption):
    ig = ag.secreto("IG_USER_ID")
    hijos = []
    for u, alt in zip(urls, alts):
        c = api("POST", f"{ig}/media", image_url=u, is_carousel_item="true", alt_text=alt[:1000])["id"]
        ig_esperar(c)
        hijos.append(c)
    padre = api("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(hijos), caption=caption)["id"]
    ig_esperar(padre)
    return ig_publicar(padre)


def ig_story(url):
    ig = ag.secreto("IG_USER_ID")
    c = api("POST", f"{ig}/media", media_type="STORIES", image_url=url)["id"]
    ig_esperar(c)
    return ig_publicar(c)


def ig_reel(url, caption, cover=None):
    """cover = URL pública de la portada del reel (reel/portada.png): formato propio, distinto del resto de publicaciones."""
    ig = ag.secreto("IG_USER_ID")
    c = api("POST", f"{ig}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true", cover_url=cover)["id"]
    ig_esperar(c, intentos=120, pausa=5)
    return ig_publicar(c)


# ---------------------------------------------------------------- Facebook (página)
def fb_carrusel(urls, caption):
    page = ag.secreto("FB_PAGE_ID")
    ids = [api("POST", f"{page}/photos", url=u, published="false")["id"] for u in urls]
    attached = {f"attached_media[{i}]": {"media_fbid": x} for i, x in enumerate(ids)}
    r = api("POST", f"{page}/feed", message=caption, **attached)
    return r["id"]


def fb_story(url):
    page = ag.secreto("FB_PAGE_ID")
    foto = api("POST", f"{page}/photos", url=url, published="false")["id"]
    return api("POST", f"{page}/photo_stories", photo_id=foto).get("post_id")


def fb_reel(url, caption):
    page = ag.secreto("FB_PAGE_ID")
    ini = api("POST", f"{page}/video_reels", upload_phase="start")
    cab = {"file_url": url}
    tok = ag.secreto("META_TOKEN")
    if tok:
        cab["Authorization"] = f"OAuth {tok}"
    r = requests.post(ini["upload_url"], headers=cab, timeout=300)
    if r.status_code >= 300:
        raise ErrorAPI(f"subida de reel a Facebook: {r.status_code} {r.text[:200]}")
    api("POST", f"{page}/video_reels", video_id=ini["video_id"], upload_phase="finish", video_state="PUBLISHED", description=caption)
    return ini["video_id"]


# ---------------------------------------------------------------- orquestación
def carpetas(fecha, tipo):
    sub = {"finde": "finde", "reel": "finde", "mensual": "mensual"}.get(tipo)
    return ag.dir_dia(fecha, sub)


def intentar(estado, clave, plataforma, fn, *a):
    """Ejecuta una publicación idempotente y deja el resultado (o el error claro) en estado.json."""
    if ag.ya_publicado(estado, clave, plataforma):
        print(f"  {clave}/{plataforma}: ya publicado, se omite")
        return True
    try:
        res = fn(*a)
        ag.anotar(estado, clave, plataforma, estado="publicado", resultado=res)
        print(f"  {clave}/{plataforma}: publicado")
        return True
    except ErrorAPI as e:
        ag.anotar(estado, clave, plataforma, estado="error", error=str(e), temporal=e.temporal)
        ag.log_estado(estado, f"ERROR {clave}/{plataforma}: {e}")
        print(f"  {clave}/{plataforma}: ERROR {e}", file=sys.stderr)
        return False


def esperar_hora(hhmm):
    """Bloquea hasta HH:MM (Europe/Madrid) para publicar en punto; si ya pasó, sigue (máx. 100 min de espera)."""
    if not hhmm:
        return
    h, m = map(int, hhmm.split(":"))
    objetivo = ag.ahora().replace(hour=h, minute=m, second=0, microsecond=0)
    falta = (objetivo - ag.ahora()).total_seconds()
    if 0 < falta <= 100 * 60:
        print(f"Esperando {int(falta)} s hasta las {hhmm}")
        time.sleep(falta)


def publicar(fecha, tipo, esperar=None):
    carpeta = carpetas(fecha, tipo)
    estado = ag.cargar_estado(carpeta)
    man = ag.cargar_json(carpeta / "manifiesto.json")
    if not man and tipo != "reel":
        ag.salir(f"No hay manifiesto en {carpeta}: ejecuta render.py antes (o hay <2 eventos verificados: ver estado.json).", 0)
    datos = ag.cargar_eventos(carpeta)
    validos = ag.eventos_validos(datos.get("eventos", []))
    if len(validos) < 2:
        ag.log_estado(estado, f"{tipo}: <2 eventos verificados, no se publica")
        ag.guardar_estado(carpeta, estado)
        return print("Menos de 2 eventos verificados: no se publica.")
    if not (estado.get("revision_final") or {}).get("hecha"):
        ag.salir("Falta la revisión final de fuentes (cancelaciones/cambios de hora). Ejecuta --marcar-revision tras comprobarlas.")

    publicando = ag.modo() == "publicar"
    print(f"MODO={ag.modo()} · {tipo} · {fecha} · {len(validos)} eventos")
    if publicando:
        ok, msg, _ = comprobar_token()
        if not ok:
            notificar.enviar("Token de Meta no válido: no se ha publicado nada", f"{msg}\n\n{notificar.INSTRUCCIONES_TOKEN}")
            ag.log_estado(estado, f"token inválido: {msg}")
            ag.guardar_estado(carpeta, estado)
            ag.salir(f"Token no válido: {msg}")
        uso, total = limite_publicaciones()
        estado["limite_publicaciones"] = {"uso": uso, "total": total, "ts": ag.ahora().isoformat(timespec="seconds")}
        necesarias = len((man or {}).get("stories", [])) + len((man or {}).get("noche", [])) + 2
        if uso + necesarias > total:
            notificar.enviar("Límite de publicaciones de 24 h cerca/superado", f"Uso {uso}/{total}, se necesitan ~{necesarias}. Nada publicado.")
            ag.guardar_estado(carpeta, estado)
            ag.salir("Límite de publicaciones insuficiente")
        if uso >= 0.8 * total:
            notificar.enviar("Se acerca el límite de publicaciones de 24 h", f"Uso {uso}/{total}")

    plan = construir_plan(carpeta, tipo, man, validos, fecha)
    if not publicando:
        for p in plan:
            print(f"  [borrador] {p['clave']}: {len(p['archivos'])} archivo(s)")
        ag.log_estado(estado, f"borrador {tipo}: {len(plan)} publicaciones preparadas, nada publicado")
        ag.guardar_estado(carpeta, estado)
        return

    subir_a_main(carpeta, fecha)
    previas = []
    for p in plan:  # todo el material ya responde 200 ANTES de la hora de publicación
        try:
            for a_ in p["archivos"]:
                esperar_200(url_publica(a_))
        except ErrorAPI as e:
            previas.append(f"{p['clave']}: {e}")
    esperar_hora(esperar)
    fallos = list(previas)
    carrusel_ok = True
    for p in plan:
        if p["clave"].startswith("stories") and tipo == "diario" and not carrusel_ok:
            ag.log_estado(estado, f"{p['clave']} omitida: falló el carrusel")
            continue
        urls = [url_publica(a) for a in p["archivos"]]
        if any(p["clave"] in x for x in previas):
            ag.log_estado(estado, f"{p['clave']} omitida: material no accesible")
            if p["clave"] == "carrusel":
                carrusel_ok = False
            continue
        ok_ig = intentar(estado, p["clave"], "instagram", p["ig"], urls)
        ok_fb = intentar(estado, p["clave"], "facebook", p["fb"], urls)
        ag.guardar_estado(carpeta, estado)
        if p["clave"] == "carrusel" and not ok_ig:
            carrusel_ok = False
        if not (ok_ig and ok_fb):
            fallos.append(p["clave"])
    estado["ultima_ejecucion"] = ag.ahora().isoformat(timespec="seconds")
    ag.guardar_estado(carpeta, estado)
    if fallos:
        notificar.enviar(f"Fallo al publicar ({tipo} {fecha})", "Fallos: " + ", ".join(fallos) + "\nDetalle en " + str(carpeta / "estado.json"))


def construir_plan(carpeta, tipo, man, eventos, fecha):
    """Lista de publicaciones: cada una con archivos, caption y funciones de IG/FB."""
    plan = []
    caption = (carpeta / "caption.txt").read_text(encoding="utf-8") if (carpeta / "caption.txt").exists() else ""
    if tipo in ("diario", "mensual"):  # «Planes del finde» solo sale como reel (tipo reel); no hay carrusel de finde
        if not caption:
            ag.salir(f"Falta {carpeta/'caption.txt'}")
        imgs = [carpeta / "carrusel" / d["archivo"] for d in man["carrusel"]]
        alts = [d["alt_text"] for d in man["carrusel"]]
        plan.append({"clave": "carrusel", "archivos": imgs,
                     "ig": lambda urls, alts=alts: ig_carrusel(urls, alts, caption), "fb": lambda urls: fb_carrusel(urls, caption)})
    if tipo == "diario":
        for d in man.get("stories", []):
            plan.append({"clave": f"stories/{d['archivo']}", "archivos": [carpeta / "stories" / d["archivo"]],
                         "ig": lambda urls: ig_story(urls[0]), "fb": lambda urls: fb_story(urls[0])})
    if tipo == "noche":
        for d in man.get("noche", []):
            plan.append({"clave": f"noche/{d['archivo']}", "archivos": [carpeta / "noche" / d["archivo"]],
                         "ig": lambda urls: ig_story(urls[0]), "fb": lambda urls: fb_story(urls[0])})
    if tipo == "reel":
        v = carpeta / "reel" / "reel.mp4"
        cap = (carpeta / "caption.txt").read_text(encoding="utf-8") if (carpeta / "caption.txt").exists() else ag.salir("Falta caption.txt")
        plan.append({"clave": "reel", "archivos": [v, carpeta / "reel" / "portada.png"], "ig": lambda urls: ig_reel(urls[0], cap, urls[1]), "fb": lambda urls: fb_reel(urls[0], cap)})
    return plan


def diagnostico():
    ok, msg, d = comprobar_token()
    print("Token:", "OK" if ok else "FALLO", "-", msg)
    if d.get("scopes"):
        print("Permisos:", ", ".join(d["scopes"]))
    for v in ("IG_USER_ID", "FB_PAGE_ID", "EMAIL_DESTINO"):
        print(f"{v}:", "definida" if ag.secreto(v) else "NO visible")
    print("MODO:", ag.modo(), "· PATROCINIOS:", "on" if ag.patrocinios_activos() else "off")
    if ok and ag.secreto("IG_USER_ID"):
        try:
            print("Límite 24 h (uso/total):", limite_publicaciones())
        except ErrorAPI as e:
            print("Límite: error", e)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=ag.hoy().isoformat())
    ap.add_argument("--tipo", choices=["diario", "noche", "finde", "reel", "mensual"], default="diario")
    ap.add_argument("--esperar-hasta", metavar="HH:MM", help="espera a esa hora (Europe/Madrid) antes de llamar a la API, p. ej. 09:00")
    ap.add_argument("--diagnostico", action="store_true")
    ap.add_argument("--marcar-revision", action="store_true")
    a = ap.parse_args()
    if a.tipo == "finde":  # «Planes del finde» es solo reel: --tipo finde se trata como --tipo reel
        print("Aviso: «Planes del finde» solo se publica en formato reel; se usa --tipo reel.")
        a.tipo = "reel"
    if a.diagnostico:
        diagnostico()
    elif a.marcar_revision:
        c = carpetas(a.fecha, a.tipo)
        e = ag.cargar_estado(c)
        e["revision_final"] = {"hecha": True, "ts": ag.ahora().isoformat(timespec="seconds")}
        ag.guardar_estado(c, e)
        print("Revisión final registrada.")
    else:
        publicar(a.fecha, a.tipo, a.esperar_hasta)
