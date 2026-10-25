"""Utilidades comunes del agente de Planes en Cádiz (rutas, reparto, validación, estado, secretos)."""
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent
TZ = ZoneInfo("Europe/Madrid")

CATEGORIAS = ["música", "teatro", "infantil", "exposición", "deporte", "gastronomía", "fiesta", "otros"]
HORARIOS = {"diario": "09:00", "stories": "09:00", "tarde": "19:00", "finde": "09:00", "mensual": "09:00"}  # no se tocan
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def ahora():
    return datetime.now(TZ)


def hoy():
    return ahora().date()


def a_fecha(valor):
    return valor if isinstance(valor, date) else date.fromisoformat(valor)


def fecha_larga(f):
    f = a_fecha(f)
    return f"{DIAS[f.weekday()]} {f.day} de {MESES[f.month - 1]}"


def modo():
    return os.environ.get("MODO", "borrador").strip().lower()


def patrocinios_activos():
    return os.environ.get("PATROCINIOS", "off").strip().lower() == "on"


def dir_dia(fecha, subtipo=None):
    """posts/AAAA-MM-DD[/subtipo]. Los posts de finde y mensual usan su propia carpeta para no pisar el diario."""
    d = RAIZ / "posts" / a_fecha(fecha).isoformat()
    if subtipo and subtipo != "diario":
        d = d / subtipo
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- reparto
MIN_EVENTOS = 1  # se publica TODOS los días: basta 1 evento verificado (el agente completa con «Siempre abierto» y, si hace falta, ver CLAUDE.md)


def reparto(n, diapositivas=9):
    """Tamaños de cada diapositiva de eventos.
    N >= 9 -> 9 diapositivas, floor(N/9) o ceil(N/9) eventos, las más cargadas primero.
    N < 9  -> N diapositivas de 1 evento. N = 0 -> []."""
    if n <= 0:
        return []
    if n < diapositivas:
        return [1] * n
    base, resto = divmod(n, diapositivas)
    return [base + 1] * resto + [base] * (diapositivas - resto)


def trocear(lista, tamanos):
    out, i = [], 0
    for t in tamanos:
        out.append(lista[i:i + t])
        i += t
    return out


def clave_orden(ev):
    """Todo el día primero; luego por hora de inicio; luego por nombre (estable)."""
    if ev.get("todo_el_dia") or not ev.get("hora_inicio"):
        return (0, "00:00", ev.get("nombre", ""))
    return (1, ev["hora_inicio"], ev.get("nombre", ""))


def ordenar(eventos, por_fecha=False):
    if por_fecha:
        return sorted(eventos, key=lambda e: (e.get("fecha", ""),) + clave_orden(e))
    return sorted(eventos, key=clave_orden)


def es_nocturno(ev, desde="19:30"):
    h = ev.get("hora_inicio")
    return bool(h) and not ev.get("todo_el_dia") and h >= desde


# ---------------------------------------------------------------- validación
def validar_evento(ev):
    """Devuelve la lista de problemas. Un evento con problemas NO se publica (regla 1, 3 y 7)."""
    e = []
    for c in ("nombre", "fecha", "lugar", "categoria"):
        if not ev.get(c):
            e.append(f"falta {c}")
    if ev.get("categoria") and ev["categoria"] not in CATEGORIAS:
        e.append(f"categoría no válida: {ev['categoria']}")
    if not ev.get("fuentes") or not all(f.get("url") for f in ev["fuentes"]):
        e.append("faltan fuentes con URL (regla 3)")
    v = ev.get("verificacion_cadiz_capital") or {}
    if v.get("confirmado") is not True or not v.get("evidencia") or not v.get("url"):
        e.append("SIN verificación de Cádiz capital (evidencia + URL): se descarta")
    img = ev.get("imagen") or {}
    if img.get("archivo") and not img.get("generica") and not img.get("generada") and not (img.get("url_origen") and img.get("fuente")):
        e.append("imagen oficial sin url_origen/fuente")
    return e


def eventos_validos(eventos, log=print):
    ok = []
    for ev in eventos:
        p = validar_evento(ev)
        if p:
            log(f"DESCARTADO '{ev.get('nombre', '?')}': {'; '.join(p)}")
        else:
            ok.append(ev)
    return ok


def cargar_json(ruta, defecto=None):
    ruta = Path(ruta)
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar_json(ruta, datos):
    Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cargar_eventos(carpeta):
    datos = cargar_json(Path(carpeta) / "eventos.json", {"eventos": []})
    return datos


# ---------------------------------------------------------------- estado (idempotencia)
def cargar_estado(carpeta):
    return cargar_json(Path(carpeta) / "estado.json", {"publicaciones": {}, "registro": []})


def guardar_estado(carpeta, estado):
    guardar_json(Path(carpeta) / "estado.json", estado)


def ya_publicado(estado, clave, plataforma=None):
    p = estado.get("publicaciones", {}).get(clave, {})
    if plataforma:
        return p.get(plataforma, {}).get("estado") == "publicado"
    return p.get("instagram", {}).get("estado") == "publicado" and p.get("facebook", {}).get("estado") == "publicado"


def anotar(estado, clave, plataforma, **datos):
    estado.setdefault("publicaciones", {}).setdefault(clave, {})[plataforma] = {"ts": ahora().isoformat(timespec="seconds"), **datos}


def log_estado(estado, mensaje):
    estado.setdefault("registro", []).append(f"{ahora().isoformat(timespec='seconds')} {mensaje}")


# ---------------------------------------------------------------- secretos
def secreto(nombre):
    """Valor de una variable de entorno, o None si no es visible.
    Con 'Secretos de red' del entorno cloud el valor lo inyecta el proxy en la petición: la sesión puede no verlo.
    Por eso el código NO falla si falta: envía igualmente la petición al host y deja que el proxy la complete."""
    v = os.environ.get(nombre)
    return v.strip() if v and v.strip() else None


def salir(msg, codigo=1):
    print(msg, file=sys.stderr)
    sys.exit(codigo)
