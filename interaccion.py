#!/usr/bin/env python3
"""Comentarios y mensajes (Instagram y Facebook).

  python interaccion.py --recoger            # busca comentarios/mensajes nuevos; responde por palabra clave; deja el resto en registros/pendientes.json
  python interaccion.py --responder ID "texto"   # el agente responde a un pendiente cuya respuesta SÍ está en las fuentes
  python interaccion.py --sin-respuesta ID       # el agente no la encuentra: se avisa por email (enlace + texto) y NO se responde

MODO=borrador: solo lee y lista; no responde ni envía mensajes. Nunca se sigue, se da like ni se comenta en perfiles ajenos.
Palabras clave en registros/palabras_clave.json: {"PLANES": "diario", "FINDE": "finde"}
"""
import argparse
import re

import agenda as ag
import notificar
from publicar import ErrorAPI, api

PENDIENTES = ag.RAIZ / "registros" / "pendientes.json"
CLAVES = ag.RAIZ / "registros" / "palabras_clave.json"
VISTOS = ag.RAIZ / "registros" / "interaccion_vista.json"
AVISADOS = ag.RAIZ / "registros" / "interaccion_avisados.json"  # ya notificados por email (un solo aviso por comentario)
DIAS_ATRAS = 7


def claves():
    return ag.cargar_json(CLAVES, {"PLANES": "diario", "FINDE": "finde"})


def agenda_para(tipo):
    """Resumen de la agenda correspondiente (primeras líneas del caption más reciente de ese tipo)."""
    from datetime import timedelta
    hoy = ag.hoy()
    sub = {"diario": None, "finde": "finde"}[tipo]
    for d in range(0, 35):
        base = ag.RAIZ / "posts" / (hoy - timedelta(days=d)).isoformat() / (sub or "")
        for nombre in ("lista.txt", "caption.txt"):  # lista.txt = lista completa de eventos (el caption del reel es corto)
            c = base / nombre
            if c.exists():
                return c.read_text(encoding="utf-8")
    return None


def comentarios_ig():
    ig = ag.secreto("IG_USER_ID")
    out = []
    for m in api("GET", f"{ig}/media", fields="id,permalink,timestamp", limit=DIAS_ATRAS * 4).get("data", []):
        for c in api("GET", f"{m['id']}/comments", fields="id,text,username,timestamp", limit=50).get("data", []):
            out.append({"id": c["id"], "plataforma": "instagram", "tipo": "comentario", "texto": c.get("text", ""), "autor": c.get("username"),
                        "enlace": m.get("permalink"), "ts": c.get("timestamp")})
    return out


def comentarios_fb():
    page = ag.secreto("FB_PAGE_ID")
    out = []
    for p in api("GET", f"{page}/posts", fields="id,permalink_url,comments.limit(50){id,message,from,created_time}", limit=DIAS_ATRAS * 4).get("data", []):
        for c in (p.get("comments") or {}).get("data", []):
            out.append({"id": c["id"], "plataforma": "facebook", "tipo": "comentario", "texto": c.get("message", ""), "autor": (c.get("from") or {}).get("name"),
                        "enlace": p.get("permalink_url"), "ts": c.get("created_time")})
    return out


def mensajes(plataforma):
    page = ag.secreto("FB_PAGE_ID")
    out = []
    params = {"fields": "id,link,messages.limit(5){id,message,from,created_time}", "limit": 25}
    if plataforma == "instagram":
        params["platform"] = "instagram"
    for conv in api("GET", f"{page}/conversations", **params).get("data", []):
        ms = (conv.get("messages") or {}).get("data", [])
        if not ms:
            continue
        ult = ms[0]  # el más reciente; si lo escribió la propia página/cuenta (nuestra respuesta), ya está atendido
        propios = {page, ag.secreto("IG_USER_ID")}
        if (ult.get("from") or {}).get("id") in propios:
            continue
        out.append({"id": ult["id"], "plataforma": plataforma, "tipo": "mensaje", "texto": ult.get("message", ""), "autor": (ult.get("from") or {}).get("name"),
                    "autor_id": (ult.get("from") or {}).get("id"), "enlace": conv.get("link"), "ts": ult.get("created_time")})
    return out



def mensaje_privado(item, msg):
    """Respuesta privada a un comentario (Messenger Platform): Facebook con el ID de la página; Instagram con el ID de la página y, si no, con el de Instagram."""
    destino = {"comment_id": item["id"]}
    if item["plataforma"] == "instagram":
        ultimo = None
        for base in (ag.secreto("FB_PAGE_ID"), ag.secreto("IG_USER_ID")):
            try:
                return api("POST", f"{base}/messages", recipient=destino, message={"text": msg})
            except ErrorAPI as e:
                ultimo = e
        raise ultimo
    return api("POST", f"{ag.secreto('FB_PAGE_ID')}/messages", recipient=destino, message={"text": msg}, messaging_type="RESPONSE")


def responder_publico(item, texto):
    """Respuesta pública breve bajo el comentario (avisa de que se ha enviado el mensaje)."""
    try:
        ruta = f"{item['id']}/replies" if item["plataforma"] == "instagram" else f"{item['id']}/comments"
        api("POST", ruta, message=texto)
    except ErrorAPI as e:
        print(f"AVISO respuesta pública: {e}")


LIMITE_MSG = 950  # Instagram/Messenger admiten 1000 caracteres por mensaje


def trocear_mensaje(texto, limite=LIMITE_MSG):
    """Divide un texto largo en mensajes de <= limite caracteres, cortando siempre por líneas completas (nunca en mitad de un plan)."""
    partes, actual = [], ""
    for linea in texto.splitlines():
        while len(linea) > limite:
            corte = linea.rfind(" ", 0, limite) or limite
            partes.append((actual + "\n" + linea[:corte]).strip()); actual, linea = "", linea[corte:].strip()
        if len(actual) + len(linea) + 1 > limite:
            partes.append(actual.strip()); actual = ""
        actual += linea + "\n"
    if actual.strip():
        partes.append(actual.strip())
    return [x for x in partes if x]


def enviar_dm(item, partes):
    """Mensajes directos consecutivos a quien nos escribe (se pueden enviar varios dentro de la ventana de 24 h)."""
    for t in partes:
        api("POST", f"{ag.secreto('FB_PAGE_ID')}/messages", recipient={"id": item["autor_id"]}, message={"text": t}, messaging_type="RESPONSE")


def responder_clave(item, tipo_agenda):
    texto = agenda_para(tipo_agenda)
    if not texto:
        return False
    cabecera, pie = "¡Hola! Aquí tienes la agenda de Cádiz 👇", "Guárdala y compártela con alguien. ¡Nos vemos por la ciudad!"
    if item["tipo"] == "mensaje":  # conversación abierta: el texto completo, en los mensajes que hagan falta
        partes = trocear_mensaje(f"{cabecera}\n\n{texto}\n\n{pie}")
        enviar_dm(item, partes)
        return True
    # respuesta privada a un comentario: Meta solo permite UN mensaje, así que se recorta por líneas completas y se indica cómo seguir
    cuerpo = ""
    for linea in texto.splitlines():
        if len(cabecera) + len(cuerpo) + len(linea) + 160 > LIMITE_MSG:
            cuerpo += "\n… y más planes: escríbenos PLANES por mensaje directo y te mandamos la lista completa 📩"
            break
        cuerpo += "\n" + linea
    msg = f"{cabecera}\n{cuerpo}".strip()
    if len(msg) + len(pie) + 2 <= LIMITE_MSG:
        msg += f"\n\n{pie}"
    mensaje_privado(item, msg)
    responder_publico(item, "¡Enviado! Revisa tus mensajes 📩")
    return True


def enviar_respuesta(item, texto):
    if item["tipo"] == "comentario":
        ruta = f"{item['id']}/replies" if item["plataforma"] == "instagram" else f"{item['id']}/comments"
        api("POST", ruta, message=texto)
    else:
        api("POST", f"{ag.secreto('FB_PAGE_ID')}/messages", recipient={"id": item["autor_id"]}, message={"text": texto}, messaging_type="RESPONSE")


MAX_DIAS = 3  # lo más antiguo es histórico: se marca como visto sin responder ni avisar


def es_reciente(ts):
    from datetime import datetime, timezone, timedelta
    try:
        t = datetime.strptime(ts.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
    except (ValueError, AttributeError):
        return True
    return t > datetime.now(timezone.utc) - timedelta(days=MAX_DIAS)


def avisar(it, estado):
    """Email por CADA comentario o mensaje nuevo (asunto con el texto, enlace y qué se ha hecho). Una sola vez por comentario."""
    ya = set(ag.cargar_json(AVISADOS, []))
    if it["id"] in ya:
        return
    ya.add(it["id"]); ag.guardar_json(AVISADOS, sorted(ya))
    quien = it.get("autor") or "alguien"
    cuerpo = (f"{it['plataforma'].capitalize()} · {it['tipo']} de {quien}\n\n«{it['texto']}»\n\nEnlace: {it.get('enlace') or 'bandeja de mensajes'}\n"
              f"Fecha: {it.get('ts')}\n\nEstado: {estado}")
    notificar.enviar(f"Nuevo {it['tipo']} en {it['plataforma']}: «{it['texto'][:50]}»", cuerpo)


def recoger():
    visto = set(ag.cargar_json(VISTOS, []))
    pendientes = {p["id"]: p for p in ag.cargar_json(PENDIENTES, [])}
    items = []
    for fuente in (comentarios_ig, comentarios_fb, lambda: mensajes("instagram"), lambda: mensajes("facebook")):
        try:
            items += fuente()
        except ErrorAPI as e:
            print(f"AVISO lectura: {e}")
    marca = ag.cargar_json(ag.RAIZ / "marca.json", {}) or {}
    propio = (marca.get("usuario") or "@planesencadiz").lstrip("@").lower()
    publicar = ag.modo() == "publicar"
    nuevos = []
    for i in items:
        if i["id"] in visto:
            continue
        if (i.get("autor") or "").lower() in (propio, "planes en cádiz · agenda diaria") or not (i.get("texto") or "").strip() or not es_reciente(i.get("ts")):
            visto.add(i["id"]); continue  # nuestras propias respuestas, vacíos e histórico
        nuevos.append(i)
    for it in nuevos:
        clave = next((k for k in claves() if re.search(rf"\b{re.escape(k)}\b", it["texto"], re.I)), None)
        estado = "pendiente de revisión por el agente"
        if clave and publicar:
            try:
                if responder_clave(it, claves()[clave]):
                    visto.add(it["id"]); estado = f"respondido automáticamente (palabra clave {clave})"
                    print(f"Palabra clave {clave}: respondido {it['id']}")
                    avisar(it, estado); continue
            except ErrorAPI as e:
                estado = f"FALLO al responder la palabra clave {clave}: {e}"
                print(f"Fallo al responder palabra clave: {e}")
        elif clave:
            estado = f"palabra clave {clave} detectada; MODO=borrador: no se responde"
        pendientes[it["id"]] = it  # en borrador todo queda pendiente (incluidas las palabras clave); no se marca como visto
        avisar(it, estado)
    ag.guardar_json(PENDIENTES, list(pendientes.values()))
    ag.guardar_json(VISTOS, sorted(visto))
    print(f"{len(nuevos)} nuevos; {len(pendientes)} pendientes de revisar por el agente (registros/pendientes.json)")


def cerrar(id_):
    pend = ag.cargar_json(PENDIENTES, [])
    item = next((p for p in pend if p["id"] == id_), None)
    if not item:
        ag.salir(f"No hay pendiente con id {id_}")
    ag.guardar_json(PENDIENTES, [p for p in pend if p["id"] != id_])
    visto = set(ag.cargar_json(VISTOS, [])); visto.add(id_); ag.guardar_json(VISTOS, sorted(visto))
    return item


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recoger", action="store_true")
    ap.add_argument("--responder", nargs=2, metavar=("ID", "TEXTO"))
    ap.add_argument("--sin-respuesta", metavar="ID")
    a = ap.parse_args()
    if a.recoger:
        recoger()
    elif a.responder:
        if ag.modo() != "publicar":
            print("[borrador] no se responde. Texto:", a.responder[1])
        else:
            item = cerrar(a.responder[0]); enviar_respuesta(item, a.responder[1]); print("Respondido.")
    elif a.sin_respuesta:
        item = cerrar(a.sin_respuesta) if ag.modo() == "publicar" else next(p for p in ag.cargar_json(PENDIENTES, []) if p["id"] == a.sin_respuesta)
        notificar.enviar(f"{item['tipo'].capitalize()} pendiente en {item['plataforma']}",
                         f"De: {item.get('autor')}\nEnlace: {item.get('enlace')}\nTexto: {item['texto']}\n\nNo he encontrado la respuesta en las fuentes consultadas, así que no he respondido.")
