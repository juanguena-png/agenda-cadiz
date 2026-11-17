"""Seguimiento de ORGANIZADORES de Cádiz capital con la API oficial de Instagram (business_discovery).

Lee las últimas publicaciones PÚBLICAS de cuentas profesionales (recintos, asociaciones, instituciones, salas,
librerías, peñas…) y saca como PISTAS las que mencionan los días pedidos. Nada de scraping: solo la Graph API
oficial con nuestro token, igual que etiquetas.py y crecimiento.py.

Una publicación del PROPIO organizador cuenta como «fuente del organizador» (CLAUDE.md, regla 4), pero el evento
sigue necesitando la REGLA 1 (dirección o recinto de Cádiz capital escrito en la propia publicación o en su web).

  python organizadores.py --fecha F [--hasta G] [--destino F/finde]   # -> posts/F/candidatos_ig.json
  python organizadores.py --verificar                                  # comprueba las cuentas «por_verificar»
  python organizadores.py --comparar F                                 # cobertura frente a cuentas de referencia
  python organizadores.py --anadir usuario                             # añade una cuenta a seguir (tras verificarla)

Lista de cuentas: registros/organizadores_ig.json
"""
import argparse
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import agenda as ag
import cuota

LISTA = ag.RAIZ / "registros" / "organizadores_ig.json"
COMPARATIVA = ag.RAIZ / "registros" / "cobertura_referencia.jsonl"
DIAS_ANTIGUEDAD = 21  # solo publicaciones de las últimas 3 semanas
CAMPOS = ("business_discovery.username({u}){{username,name,media.limit({n})"
          "{{caption,timestamp,permalink,media_type,media_url,children{{media_url}}}}}}")
SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = [m[:3] for m in MESES]


def norm(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def api(**kw):
    from publicar import api as _api
    return _api("GET", ag.secreto("IG_USER_ID"), **kw)


def cargar_lista():
    return ag.cargar_json(LISTA, {"cuentas": [], "por_verificar": [], "referencia": [], "fallidas": {}})


CACHE = ag.RAIZ / "registros" / "cache_organizadores.json"
CACHE_HORAS = 4  # una lectura sirve a todas las ejecuciones de las siguientes 4 h (flujo, tarde, simulaciones)


def publicaciones(usuario, n=15):
    """Últimas publicaciones públicas de una cuenta profesional, o None si no es consultable por la API."""
    if not cuota.hay_margen(cuota.UMBRAL_LECTURAS):
        return {"error": "pausada: cuota de la API de Meta alta (se retoma en la próxima ejecución)", "pausada": True}
    try:
        b = api(fields=CAMPOS.format(u=usuario.lstrip("@"), n=n))["business_discovery"]
    except Exception as e:  # cuenta personal, inexistente o renombrada
        return {"error": str(e)[:160]}
    return {"nombre": b.get("name"), "media": (b.get("media") or {}).get("data", [])}


def _mes(txt):
    t = norm(txt)
    for i, m in enumerate(MESES):
        if t.startswith(m[:3]):
            return i + 1
    return None


def coincidencia(texto, dia, publicado):
    """Cómo menciona el texto el día `dia`: 'fecha', 'rango', 'semanal', 'hoy' o None."""
    t = norm(texto)
    d, m = dia.day, dia.month
    mes_rx = "(?:" + "|".join(MESES + MESES_CORTOS) + ")"
    # 17 de noviembre / 17 noviembre / 17 nov
    for x in re.finditer(rf"\b(\d{{1,2}})\s*(?:de\s+)?({mes_rx})\b", t):
        if int(x.group(1)) == d and _mes(x.group(2)) == m:
            return "fecha"
    # 17/11, 17-11, 17.11 (con año opcional)
    for x in re.finditer(r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b", t):
        if int(x.group(1)) == d and int(x.group(2)) == m:
            return "fecha"
    # rangos: del 16 al 22 de noviembre / 16-22 nov / del 2 al 17 de noviembre
    for x in re.finditer(rf"\b(\d{{1,2}})\s*(?:al|a|-|–|—|y)\s*(?:el\s+)?(\d{{1,2}})\s*(?:de\s+)?({mes_rx})\b", t):
        a, b, mm = int(x.group(1)), int(x.group(2)), _mes(x.group(3))
        if mm == m and a <= d <= b:
            return "rango"
    # «martes 17»
    if re.search(rf"\b(?:{SEMANA[dia.weekday()]}|{SEMANA[dia.weekday()][:3]})\s*,?\s*{d}\b", t):
        return "fecha"
    # actividades semanales: «todos los martes», «cada martes», «los martes de 17 a 20»
    if re.search(rf"\b(?:todos los|cada|los)\s+{SEMANA[dia.weekday()]}(?:es|s)?\b", t):
        return "semanal"
    # «hoy» / «esta noche» en una publicación hecha ese mismo día
    if publicado == dia and re.search(r"\b(hoy|esta noche|esta tarde|esta manana)\b", t):
        return "hoy"
    return None


def recopilar(ini, fin, carpeta, n=15):
    """Pistas de los organizadores para cada día de la ventana -> carpeta/candidatos_ig.json."""
    lista = cargar_lista()
    cuentas = sorted(set(lista.get("cuentas", [])))
    limite = ag.hoy() - timedelta(days=DIAS_ANTIGUEDAD)
    dias = [ini + timedelta(days=i) for i in range((fin - ini).days + 1)]
    # Caché de 4 h: no se vuelve a pedir a Meta lo ya leído (la cuota de la app es compartida con la publicación)
    cache = ag.cargar_json(CACHE, {})
    ahora = datetime.now().timestamp()
    res, pendientes = {}, []
    for u in cuentas:
        c = cache.get(u)
        if c and ahora - c.get("epoch", 0) < CACHE_HORAS * 3600 and c.get("n", 0) >= n:
            res[u] = {"nombre": c.get("nombre"), "media": c.get("media", [])}
        else:
            pendientes.append(u)
    # Lectura con 2 hilos y pausa; se para sola al llegar al 50 % de la cuota y el resto queda para la próxima ejecución
    def leer(u):
        r = publicaciones(u, n)
        time.sleep(0.4)
        return r
    pausadas = []
    for i in range(0, len(pendientes), 10):
        if not cuota.hay_margen(cuota.UMBRAL_LECTURAS):
            pausadas += pendientes[i:]
            break
        lote = pendientes[i:i + 10]
        with ThreadPoolExecutor(2) as ex:
            for u, r in zip(lote, ex.map(leer, lote)):
                if r.get("pausada"):
                    pausadas.append(u)
                    continue
                res[u] = r
                if "error" not in r:
                    cache[u] = {"epoch": ahora, "n": n, "nombre": r.get("nombre"), "media": r.get("media", [])}
    ag.guardar_json(CACHE, cache)
    if pausadas:
        print(f"Organizadores: cuota de Meta alta ({cuota.uso_estimado()}): {len(pausadas)} cuentas pendientes para la próxima ejecución")
    pistas, fallidas = [], {}
    for u, r in res.items():
        if "error" in r:
            fallidas[u] = r["error"]
            continue
        for p in r["media"]:
            try:
                pub = datetime.fromisoformat(p["timestamp"].replace("+0000", "+00:00")).astimezone(ag.ahora().tzinfo).date()
            except Exception:
                continue
            if pub < limite:
                continue
            for dia in dias:
                c = coincidencia(p.get("caption"), dia, pub)
                if c:
                    pistas.append({"dia": dia.isoformat(), "cuenta": u, "nombre_cuenta": r.get("nombre"), "coincide": c,
                                   "publicado": pub.isoformat(), "permalink": p.get("permalink"),
                                   "texto": (p.get("caption") or "")[:900],
                                   "imagenes": [x.get("media_url") for x in ((p.get("children") or {}).get("data") or [])][:10] or [p.get("media_url")]})
    salida = {"generado": ag.ahora().isoformat(timespec="seconds"), "ventana": [ini.isoformat(), fin.isoformat()],
              "cuentas_consultadas": len(res) - len(fallidas), "cuentas_pausadas_por_cuota": len(pausadas), "cuentas_fallidas": fallidas, "pistas": pistas,
              "instruccion": ("Pistas de organizadores (API oficial). Cada una: confirma fecha, hora y REGLA 1 (dirección o recinto de "
                              "Cádiz capital en el texto del organizador o en su web), comprueba que no es online ni cancelado y "
                              "redacta con palabras propias. 'semanal' = actividad recurrente: entra si el texto confirma día y hora. "
                              "Guarda en la fuente del evento {'nombre': '@cuenta (Instagram del organizador)', 'url': permalink}.")}
    ag.guardar_json(carpeta / "candidatos_ig.json", salida)
    lista["fallidas"] = fallidas
    ag.guardar_json(LISTA, lista)
    print(f"Organizadores: {salida['cuentas_consultadas']} cuentas leídas, {len(pistas)} pistas, {len(fallidas)} sin acceso")
    return salida


def verificar():
    """Comprueba las cuentas «por_verificar»: si la API las devuelve, pasan a «cuentas» (revisa el nombre)."""
    lista = cargar_lista()
    quedan = []
    for u in lista.get("por_verificar", []):
        r = publicaciones(u, 1)
        if "error" in r:
            print(f"✗ @{u}: {r['error']}")
            quedan.append(u)
        else:
            print(f"✓ @{u}: {r.get('nombre')}  → comprueba que es de Cádiz capital; si no, quítala de cuentas")
            lista.setdefault("cuentas", []).append(u)
    lista["por_verificar"] = quedan
    lista["cuentas"] = sorted(set(lista["cuentas"]))
    ag.guardar_json(LISTA, lista)


def anadir(usuario):
    u = usuario.lstrip("@").lower()
    r = publicaciones(u, 1)
    if "error" in r:
        ag.salir(f"@{u} no es consultable por la API (¿cuenta personal o inexistente?): {r['error']}")
    lista = cargar_lista()
    lista["cuentas"] = sorted(set(lista.get("cuentas", [])) | {u})
    ag.guardar_json(LISTA, lista)
    print(f"Añadida @{u} ({r.get('nombre')})")


def comparar(dia):
    """Mide la cobertura frente a las cuentas de referencia (solo para MEDIR y como pista: nunca se copian textos ni imágenes).
    Busca su publicación de agenda de ese día, cuenta sus diapositivas y saca las líneas que no aparecen en nuestro eventos.json."""
    lista = cargar_lista()
    nuestros = ag.cargar_json(ag.dir_dia(dia) / "eventos.json", {}) or {}
    nombres = [norm(e.get("nombre")) for e in nuestros.get("eventos", [])]
    palabras = [set(re.findall(r"[a-z0-9]{4,}", n)) for n in nombres]
    for ref in lista.get("referencia", []):
        r = publicaciones(ref, 10)
        if "error" in r:
            print(f"@{ref}: sin acceso ({r['error']})"); continue
        for p in r["media"]:
            pub = datetime.fromisoformat(p["timestamp"].replace("+0000", "+00:00")).astimezone(ag.ahora().tzinfo).date()
            if coincidencia(p.get("caption"), dia, pub) not in ("fecha", "hoy") or abs((pub - dia).days) > 1:
                continue
            diapos = len(((p.get("children") or {}).get("data")) or []) or 1
            lineas = [l.strip(" •-·*") for l in (p.get("caption") or "").splitlines() if len(l.strip()) > 12]
            sin_cubrir = [l for l in lineas if not any(len(set(re.findall(r"[a-z0-9]{4,}", norm(l))) & w) >= 2 for w in palabras)]
            reg = {"fecha": dia.isoformat(), "referencia": ref, "permalink": p.get("permalink"), "diapositivas_suyas": diapos,
                   "eventos_nuestros": len(nombres), "lineas_sin_cubrir": sin_cubrir[:40]}
            with open(COMPARATIVA, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
            print(f"@{ref}: {diapos} diapositivas · nosotros {len(nombres)} eventos · {len(sin_cubrir)} líneas suyas sin cubrir")
            for l in sin_cubrir[:40]:
                print("   ·", l[:140])
            break


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=ag.hoy().isoformat())
    ap.add_argument("--hasta")
    ap.add_argument("--destino")
    ap.add_argument("--verificar", action="store_true")
    ap.add_argument("--comparar", metavar="FECHA")
    ap.add_argument("--anadir", metavar="USUARIO")
    a = ap.parse_args()
    if a.verificar:
        verificar()
    elif a.comparar:
        comparar(date.fromisoformat(a.comparar))
    elif a.anadir:
        anadir(a.anadir)
    else:
        ini = date.fromisoformat(a.fecha)
        fin = date.fromisoformat(a.hasta) if a.hasta else ini
        recopilar(ini, fin, ag.dir_dia(*(a.destino.split("/") if a.destino else [ini])))
