#!/usr/bin/env python3
"""Comprobación previa a publicar: qué funciona y qué falta por configurar (con las instrucciones exactas).
   python preflight.py"""
import importlib
import json
import os
import shutil
import subprocess
import sys

import requests

import agenda as ag
import publicar

OK, KO, AV = "✅", "❌", "⚠️ "
fallos = []


def linea(ok, msg, ayuda=None, aviso=False):
    print(f"{OK if ok else (AV if aviso else KO)} {msg}")
    if not ok and ayuda:
        print(f"     → {ayuda}")
    if not ok and not aviso:
        fallos.append(msg)


# --- entorno cloud
linea(shutil.which("ffmpeg") is not None, "ffmpeg instalado", "ejecuta `bash setup.sh`")
try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    import render as rd
    with rd.Renderer():
        pass
    linea(True, "Chromium/Playwright funciona")
except Exception as e:
    linea(False, f"Chromium/Playwright: {str(e)[:80]}", "ejecuta `bash setup.sh`")
for m in ("requests", "bs4", "PIL"):
    try:
        importlib.import_module(m); 
    except ImportError:
        linea(False, f"módulo {m}", "pip install -r requirements.txt")
linea(len(__import__("reel").pistas_validas()) >= 3, f"música CC0 en rotación ({len(__import__('reel').pistas_validas())} pistas)", "añade pistas verificadas a musica/licencias.md")
# --- GitHub (las imágenes se sirven por raw.githubusercontent.com desde main)
try:
    repo = publicar.repo_github()
    r = requests.get(f"https://raw.githubusercontent.com/{repo}/main/marca.json", timeout=20)
    linea(r.status_code == 200, f"repo público y servido por raw.githubusercontent.com ({repo})", "el repo debe ser PÚBLICO y la rama main debe existir")
    p = subprocess.run(["git", "-C", str(ag.RAIZ), "push", "--dry-run", "origin", "HEAD:main"], capture_output=True, text=True)
    linea(p.returncode == 0, "permiso de push a main", "instala la app Claude en el repo con permiso de escritura (Contents) y reconecta GitHub")
except Exception as e:
    linea(False, f"GitHub: {e}")
# --- variables
linea(ag.modo() in ("borrador", "publicar"), f"MODO={ag.modo()}", "MODO debe ser borrador o publicar")
for v, ayuda in (("IG_USER_ID", "id de la cuenta de Instagram profesional (README, paso 3.4)"), ("FB_PAGE_ID", "id de la página de Facebook (README, paso 3.4)"), ("EMAIL_DESTINO", "tu email para avisos")):
    linea(bool(ag.secreto(v)), f"{v} definida", f"añádela como variable del entorno: {ayuda}")
# --- Meta
ok, msg, datos = publicar.comprobar_token()
linea(ok, f"META_TOKEN: {msg}", "añade META_TOKEN como Secreto de red (hosts graph.facebook.com y graph.instagram.com) o como variable; README, paso 3")
if ok:
    necesarios = {"instagram_basic", "instagram_content_publish", "pages_show_list", "pages_read_engagement", "pages_manage_posts", "instagram_manage_comments", "instagram_manage_insights",
                  "instagram_manage_messages", "pages_manage_engagement", "pages_messaging", "read_insights"}
    scopes = set(datos.get("scopes") or [])
    if scopes:
        falta = sorted(necesarios - scopes)
        linea(not falta, "permisos del token completos", f"faltan: {', '.join(falta)} (regenera el token con todos)", aviso=True)
    if ag.secreto("IG_USER_ID"):
        try:
            d = publicar.api("GET", ag.secreto("IG_USER_ID"), fields="username,followers_count")
            linea(True, f"Instagram conectado: @{d.get('username')}")
            uso, total = publicar.limite_publicaciones()
            linea(True, f"límite de publicaciones 24 h: {uso}/{total}")
        except publicar.ErrorAPI as e:
            linea(False, f"Instagram: {e}", "comprueba IG_USER_ID y que la cuenta es profesional y está vinculada a la página")
    if ag.secreto("FB_PAGE_ID"):
        try:
            d = publicar.api("GET", ag.secreto("FB_PAGE_ID"), fields="name")
            linea(True, f"Página de Facebook conectada: {d.get('name')}")
        except publicar.ErrorAPI as e:
            linea(False, f"Facebook: {e}", "comprueba FB_PAGE_ID y que el token es de esa página")
# --- Resend
try:
    cab = {"Authorization": f"Bearer {ag.secreto('RESEND_API_KEY')}"} if ag.secreto("RESEND_API_KEY") else {}
    r = requests.get("https://api.resend.com/domains", headers=cab, timeout=20)
    linea(r.status_code == 200, f"Resend responde ({r.status_code})", "añade RESEND_API_KEY como Secreto de red (host api.resend.com)")
except requests.RequestException as e:
    linea(False, f"Resend: {e}")
print()
print("LISTO PARA PUBLICAR" if not fallos else f"FALTAN {len(fallos)} cosas (arriba, con ❌).")
print("Cuando todo esté ✅: cambia MODO=publicar en el entorno. Mientras tanto el agente genera borradores sin publicar.")
sys.exit(1 if fallos else 0)
