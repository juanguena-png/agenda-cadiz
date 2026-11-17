"""Control de la cuota de la Graph API de Meta (cabecera X-App-Usage).

Meta bloquea TODA la app con el error #4 («Application request limit reached») cuando alguno de los tres contadores
de `X-App-Usage` (call_count, total_cputime, total_time; en % del límite móvil de ~1 h) llega al 100 %. El 17/11/2026
el que se disparó fue `total_time` (210 %) por lecturas masivas de organizadores (business_discovery) y bloqueó la
publicación de las 19:23.

Reglas de este módulo (las usa publicar.api, así que valen para TODOS los scripts):
  · cada respuesta de Meta actualiza el nivel de uso (en memoria y en registros/cuota_meta.json);
  · las LECTURAS MASIVAS (organizadores) paran al llegar a UMBRAL_LECTURAS (50 %) y dejan el resto para la próxima vez;
  · PUBLICAR espera, si hace falta, a que el uso baje de UMBRAL_PUBLICAR (80 %) antes de empezar;
  · un error #4 nunca se reintenta a martillazos: se anota un bloqueo de ~20 min y se espera.
Nada de esto cambia horarios ni reglas editoriales.
"""
import json
import time

import agenda as ag

ARCHIVO = ag.RAIZ / "registros" / "cuota_meta.json"
UMBRAL_LECTURAS = 50   # % a partir del cual paran las lecturas masivas
UMBRAL_PUBLICAR = 80   # % a partir del cual publicar espera
BAJADA_POR_MIN = 4.0   # puntos/min que baja el uso (medido el 17/11: ~7; se usa la mitad por prudencia)
BLOQUEO_MIN = 20       # minutos de espera mínima tras un #4

_nivel = {"uso": None, "ts": 0.0}


def _leer():
    return ag.cargar_json(ARCHIVO, {})


def registrar(cabecera):
    """Guarda el uso de una respuesta (`X-App-Usage`: '{"call_count":76,"total_cputime":0,"total_time":211}')."""
    try:
        d = json.loads(cabecera or "{}")
    except ValueError:
        return
    if not d:
        return
    uso = max(float(d.get("call_count", 0)), float(d.get("total_cputime", 0)), float(d.get("total_time", 0)))
    _nivel["uso"], _nivel["ts"] = uso, time.time()
    previo = _leer()
    if "bloqueo_hasta" in previo or time.time() - getattr(registrar, "_ultimo", 0) >= 5:  # no escribir en cada llamada
        registrar._ultimo = time.time()
        # una respuesta real de Meta con uso < 100 prueba que el bloqueo ya terminó
        ag.guardar_json(ARCHIVO, {**{k: v for k, v in previo.items() if k != "bloqueo_hasta" or uso >= 100},
                                  "uso": uso, "detalle": d, "ts": ag.ahora().isoformat(timespec="seconds"), "epoch": time.time()})


def registrar_bloqueo():
    """Error #4: la app está al 100 %. Se anota hasta cuándo no conviene llamar."""
    _nivel["uso"], _nivel["ts"] = 100.0, time.time()
    ag.guardar_json(ARCHIVO, {**_leer(), "uso": 100.0, "bloqueo_hasta": time.time() + BLOQUEO_MIN * 60,
                              "ts": ag.ahora().isoformat(timespec="seconds"), "epoch": time.time()})


def uso_estimado():
    """Uso actual estimado (%): lo último medido, menos lo que ha bajado desde entonces. None si no hay datos recientes."""
    if _nivel["uso"] is not None:
        base, ts = _nivel["uso"], _nivel["ts"]
    else:
        d = _leer()
        if "uso" not in d:
            return None
        base, ts = float(d["uso"]), float(d.get("epoch", 0))
    est = base - BAJADA_POR_MIN * (time.time() - ts) / 60
    return max(0.0, est) if time.time() - ts < 3 * 3600 else None


def bloqueado():
    return float(_leer().get("bloqueo_hasta", 0)) > time.time()


def hay_margen(umbral=UMBRAL_LECTURAS):
    """True si se puede seguir con lecturas masivas (sin bloqueo y por debajo del umbral)."""
    if bloqueado():
        return False
    u = uso_estimado()
    return u is None or u < umbral


def sonda():
    """Una consulta barata que devuelve X-App-Usage (business_discovery de una cuenta, 1 publicación). Devuelve el uso (%) o 100 si hay #4."""
    import publicar
    try:
        publicar.api("GET", ag.secreto("IG_USER_ID"), reintentos=0, fields="business_discovery.username(teatrofalla){username}")
    except publicar.ErrorAPI as e:
        if e.codigo == 4:
            return 100.0
        # otros errores: el header ya se habrá registrado si la respuesta lo traía
    return uso_estimado() if uso_estimado() is not None else 0.0


def esperar_para_publicar(max_min=30, log=print):
    """Antes de publicar: si la app está por encima del 80 % (o bloqueada), espera hasta max_min minutos a que baje. True si hay margen."""
    fin = time.time() + max_min * 60
    while True:
        u = sonda()
        if u < UMBRAL_PUBLICAR and not bloqueado():
            return True
        if time.time() >= fin:
            log(f"Cuota de Meta alta ({u:.0f} %) tras esperar {max_min} min: se intenta publicar igualmente.")
            return False
        log(f"Cuota de Meta alta ({u:.0f} %): espero 60 s…")
        time.sleep(60)
