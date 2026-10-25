#!/usr/bin/env python3
"""Genera los recursos gráficos de los perfiles: python marca/generar_perfiles.py"""
import sys
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import render as rd  # noqa: E402

OUT = RAIZ / "marca" / "perfiles"


def png(r, plantilla, datos, salida, vp, escala=1):
    import agenda as ag
    marca = ag.cargar_json(RAIZ / "marca.json", {})
    datos = {"tema": marca.get("tema", "d1"), "prefijo": marca.get("prefijo", "Planes en"), "ciudad": marca.get("ciudad", "Cádiz"), **datos}
    pg = r.browser.new_page(viewport=vp, device_scale_factor=escala)
    pg.goto((RAIZ / "plantilla" / plantilla).as_uri())
    pg.add_style_tag(url=(RAIZ / "plantilla" / "temas" / f"{datos['tema']}.css").as_uri())
    pg.evaluate("d => render(d)", datos)
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(salida), clip={"x": 0, "y": 0, **vp})
    pg.close()


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    with rd.Renderer() as r:
        png(r, "cabecera.html", {}, OUT / "facebook-cabecera-1640x624.png", {"width": 1640, "height": 624})
        png(r, "perfil.html", {"modo": "avatar"}, OUT / "foto-perfil-960.png", {"width": 320, "height": 320}, 3)
    print("ok", OUT)
