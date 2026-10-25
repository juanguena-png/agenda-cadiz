#!/usr/bin/env python3
"""Avisos por email con Resend (plan gratuito). Uso: python notificar.py "asunto" "cuerpo" """
import sys

import requests

import agenda as ag

RESEND = "https://api.resend.com/emails"


def enviar(asunto, cuerpo):
    """Registra siempre el aviso en registros/avisos.log y lo envía por email.
    Con 'Secretos de red' la clave la inyecta el proxy: si RESEND_API_KEY no es visible, se envía igualmente sin cabecera."""
    with open(ag.RAIZ / "registros" / "avisos.log", "a", encoding="utf-8") as fh:
        fh.write(f"{ag.ahora().isoformat(timespec='seconds')}\t{asunto}\n{cuerpo}\n---\n")
    destino = ag.secreto("EMAIL_DESTINO")
    if not destino:
        print(f"[aviso sin enviar: falta EMAIL_DESTINO] {asunto}", file=sys.stderr)
        return False
    cab = {"Content-Type": "application/json"}
    clave = ag.secreto("RESEND_API_KEY")
    if clave:
        cab["Authorization"] = f"Bearer {clave}"
    remitente = ag.secreto("EMAIL_REMITENTE") or "Planes en Cádiz <onboarding@resend.dev>"
    try:
        r = requests.post(RESEND, headers=cab, timeout=30,
                          json={"from": remitente, "to": [destino], "subject": f"[Planes en Cádiz] {asunto}", "text": cuerpo})
        if r.status_code >= 300:
            print(f"Resend {r.status_code}: {r.text[:300]}", file=sys.stderr)
        return r.status_code < 300
    except requests.RequestException as e:
        print(f"No se pudo enviar el aviso: {e}", file=sys.stderr)
        return False


INSTRUCCIONES_TOKEN = """El META_TOKEN ya no es válido (o falta). Para regenerarlo:
1. developers.facebook.com/tools/explorer -> elige tu app -> 'Obtener token de acceso de usuario' con los permisos del README.
2. Conviértelo a larga duración: GET /oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=TOKEN_CORTO
3. Obtén el token de página: GET /me/accounts?access_token=TOKEN_LARGO -> copia el access_token de tu página.
4. Pégalo como 'Secreto de red' META_TOKEN en el entorno cloud 'agenda-cadiz' (host graph.facebook.com y graph.instagram.com).
Detalle completo en el README."""

if __name__ == "__main__":
    if len(sys.argv) < 3:
        ag.salir('Uso: notificar.py "asunto" "cuerpo"')
    sys.exit(0 if enviar(sys.argv[1], sys.argv[2]) else 1)
