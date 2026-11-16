#!/usr/bin/env python3
"""Lanza publicar.py con espera hasta la hora fijada y lo vigila: si el proceso muere o no deja
la publicación hecha, lo relanza (sin esperar) hasta 3 veces. Un proceso en segundo plano que
desaparece sin avisar dejó una vez sin publicar a las 9:00.
Uso: python vigilar_publicacion.py --fecha F --tipo diario|noche|reel|mensual --hasta 09:00"""
import argparse, subprocess, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo
import agenda as ag

def hecho(fecha, tipo):
    carpeta = ag.dir_dia(fecha, "finde" if tipo == "reel" else "mensual" if tipo == "mensual" else "diario")
    est = ag.cargar_estado(carpeta)
    pub = est.get("publicaciones", {})
    clave = {"diario": "carrusel", "noche": "noche", "reel": "reel", "mensual": "carrusel"}[tipo]
    return any(str(k).startswith(clave) and all(v.get("estado") == "publicado" for v in d.values() if isinstance(v, dict)) and d for k, d in pub.items())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", required=True); ap.add_argument("--tipo", required=True)
    ap.add_argument("--hasta", required=True)
    a = ap.parse_args()
    base = [sys.executable, "publicar.py", "--fecha", a.fecha, "--tipo", a.tipo]
    for intento in range(4):
        cmd = base + (["--esperar-hasta", a.hasta] if intento == 0 else [])
        print(f"[{datetime.now(ZoneInfo('Europe/Madrid')):%H:%M:%S}] intento {intento + 1}: {' '.join(cmd[2:])}", flush=True)
        rc = subprocess.run(cmd).returncode
        if hecho(a.fecha, a.tipo):
            print("OK: publicación completada", flush=True); return 0
        print(f"AVISO: publicar.py terminó (rc={rc}) sin dejar la publicación completa; reintento en 20 s", flush=True)
        time.sleep(20)
    print("ERROR: sin publicar tras 4 intentos; revisar a mano", flush=True)
    return 1

if __name__ == "__main__":
    sys.exit(main())
