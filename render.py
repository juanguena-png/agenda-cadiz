#!/usr/bin/env python3
"""Genera las imágenes (PNG) de carrusel, stories y story de tarde a partir de eventos.json.

Uso:
  python render.py --fecha 2026-10-25 [--tipo diario|finde|mensual] [--variante A|B]
  python render.py --demo 5 14 22 33 50      # datos de ejemplo -> ejemplos/demo-N/
"""
import argparse
from datetime import timedelta
import glob
import shutil
import sys
from pathlib import Path

import agenda as ag

PLANTILLA = ag.RAIZ / "plantilla"
VIEW_FEED = {"width": 1080, "height": 1350}
VIEW_STORY = {"width": 1080, "height": 1920}
NOCHE_POR_STORY = 4


def ruta_chromium():
    for p in glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/chrome") + ["/opt/pw-browsers/chromium/chrome-linux64/chrome"]:
        if Path(p).exists():
            return p
    return None  # usa el Chromium que instaló `playwright install`


class Renderer:
    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        exe = ruta_chromium()
        self.browser = self._pw.chromium.launch(executable_path=exe) if exe else self._pw.chromium.launch()
        return self

    def __exit__(self, *a):
        self.browser.close()
        self._pw.stop()

    def png(self, plantilla, datos, salida, viewport):
        """Renderiza una plantilla con la identidad de marca.json (tema, prefijo y ciudad del logo modular)."""
        marca = ag.cargar_json(ag.RAIZ / "marca.json", {})
        datos = {"tema": marca.get("tema", "d1"), "prefijo": marca.get("prefijo", "Planes en"), "ciudad": marca.get("ciudad", "Cádiz"), **datos}
        page = self.browser.new_page(viewport=viewport, device_scale_factor=1)
        page.goto((PLANTILLA / plantilla).as_uri())
        tema = PLANTILLA / "temas" / f"{datos['tema']}.css"
        if tema.exists():
            page.add_style_tag(url=tema.as_uri())
        page.evaluate("d => render(d)", datos)
        page.wait_for_timeout(150)
        page.screenshot(path=str(salida), clip={"x": 0, "y": 0, **viewport})
        page.close()


def resolver_imagenes(eventos, carpeta):
    """Añade imagen.ruta_abs (file://) a cada evento; imagen genérica de categoría si falta o no existe."""
    for ev in eventos:
        img = ev.setdefault("imagen", {})
        cand = [Path(carpeta) / img.get("archivo", "_"), ag.RAIZ / img.get("archivo", "_")]
        ruta = next((c for c in cand if img.get("archivo") and c.is_file()), None)
        if ruta is None:
            # Sin imagen oficial: ilustración PROPIA relacionada con el evento (ilustrar.py). La genérica de categoría es el último recurso.
            try:
                import ilustrar
                img.clear()
                img.update(ilustrar.generar(ev, Path(carpeta) / "img"))
                ruta = ag.RAIZ / img["archivo"] if not Path(img["archivo"]).is_absolute() else Path(img["archivo"])
            except Exception:
                ruta = PLANTILLA / "sin-foto" / f"{ev.get('categoria', 'otros')}.png"
                img.update(archivo=str(ruta.relative_to(ag.RAIZ)), generica=True,
                           alt_text=img.get("alt_text") or f"Imagen genérica de la categoría {ev.get('categoria', 'otros')}")
        img.setdefault("alt_text", f"Imagen de {ev.get('nombre', 'evento')}")
        if not img["alt_text"]:
            img["alt_text"] = f"Imagen de {ev.get('nombre', 'evento')}"
        if not img.get("generica"):
            try:
                from PIL import Image
                with Image.open(ruta) as im_:
                    w, h = im_.size
                if "ajuste" not in img:
                    img["ajuste"] = "contain" if (h / w > 1.2 or h / w < 0.8 or w < 800) else "cover"
            except Exception:
                pass
        img["ruta_abs"] = ruta.resolve().as_uri()
    return eventos


def variante(fecha):
    fijada = (ag.cargar_json(ag.RAIZ / "registros" / "ab.json", {}) or {}).get("fijar")
    return fijada if fijada in ("A", "B") else ("A" if ag.a_fecha(fecha).toordinal() % 2 == 0 else "B")


ORDEN_PALETAS = [0, 2, 1, 3, 5, 6]  # 6 variantes (la celeste «bruma» está descartada para siempre); días consecutivos y filas contiguas de la cuadrícula de 3 columnas nunca comparten familia de color


def paleta(fecha):
    """Índice de paleta de la portada (marca.md): rota cada día. Se puede fijar con registros/ab.json -> "paleta"."""
    return ORDEN_PALETAS[ag.a_fecha(fecha).toordinal() % len(ORDEN_PALETAS)]


def titulos(tipo, fecha, eventos):
    f = ag.a_fecha(fecha)
    if tipo == "finde":
        # fin de semana = viernes a domingo siguientes a la publicación (jueves)
        vie = f + timedelta(days=(4 - f.weekday()) % 7 or 7) if f.weekday() != 4 else f
        dom = vie + timedelta(days=2)
        txt = f"{vie.day} – {dom.day} de {ag.MESES[dom.month - 1]}" if vie.month == dom.month else f"{vie.day} {ag.MESES[vie.month - 1][:3]} – {dom.day} {ag.MESES[dom.month - 1][:3]}"
        return "Planes del finde", txt
    if tipo == "mensual":
        return f"Lo más destacado de {ag.MESES[f.month - 1]}", f"{ag.MESES[f.month - 1]} {f.year}"
    return "Qué hacer hoy", ag.fecha_larga(f)  # la ciudad va en el logo modular («Planes en Cádiz»)


PORTADA_EXTRA = {"diario": ("Agenda diaria", "en la ciudad"), "finde": ("Viernes a domingo", "para el finde"), "mensual": ("Agenda mensual", "imprescindibles")}


def render_carrusel(r, eventos, tipo, fecha, salida, var):
    """Portada + hasta 9 diapositivas de eventos. Devuelve el manifiesto de diapositivas."""
    salida.mkdir(parents=True, exist_ok=True)
    for viejo in salida.glob("*.png"):
        viejo.unlink()
    eventos = ag.ordenar(eventos, por_fecha=tipo != "diario")
    grupos = ag.trocear(eventos, ag.reparto(len(eventos)))
    titulo, sub = titulos(tipo, fecha, eventos)
    etiqueta, sufijo = PORTADA_EXTRA[tipo]
    ciudad = (ag.cargar_json(ag.RAIZ / "marca.json", {}) or {}).get("ciudad", "Cádiz")
    r.png("portada.html", {"titulo": titulo, "subtitulo": sub, "total": len(eventos), "etiqueta": etiqueta, "sufijo": sufijo, "paleta": paleta(fecha)}, salida / "01.png", VIEW_FEED)
    import etiquetas
    manifiesto = [{"archivo": "01.png", "tipo": "portada", "etiquetas": etiquetas.para_diapositiva(eventos),
                   "alt_text": f"Portada de Planes en {ciudad}: {titulo}, {sub}. {len(eventos)} planes."}]
    for i, g in enumerate(grupos, start=2):
        r.png("eventos.html", {"eventos": g, "cabecera": f"{i - 1}/{len(grupos)}", "mostrar_fecha": tipo != "diario"}, salida / f"{i:02d}.png", VIEW_FEED)
        manifiesto.append({"archivo": f"{i:02d}.png", "tipo": "eventos", "ids": [e.get("id") for e in g], "etiquetas": etiquetas.para_diapositiva(g),
                           "alt_text": "Eventos: " + "; ".join(f"{e['nombre']} ({e.get('hora_inicio') or 'todo el día'}, {e['lugar']})" for e in g)})
    return manifiesto


def render_stories(r, eventos, fecha, salida):
    """1 story por evento, en orden cronológico. Con PATROCINIOS=on se intercalan las patrocinadas (nunca la primera)."""
    import patrocinios
    salida.mkdir(parents=True, exist_ok=True)
    for viejo in salida.glob("*.png"):
        viejo.unlink()
    evs = ag.ordenar(eventos)
    pat = patrocinios.activos(fecha)
    pos = patrocinios.posiciones(len(evs), pat)
    secuencia = []
    for i, ev in enumerate(evs, start=1):
        secuencia.append(("evento", ev))
        secuencia += [("patro", pat[k]) for k, p in pos.items() if p == i]
    man = []
    for n, (tipo, x) in enumerate(secuencia, start=1):
        archivo = f"{n:02d}.png"
        if tipo == "evento":
            r.png("story.html", {"evento": x, "fecha_larga": ag.fecha_larga(x.get("fecha", fecha))}, salida / archivo, VIEW_STORY)
            man.append({"archivo": archivo, "id": x.get("id"), "alt_text": (x.get("imagen") or {}).get("alt_text", x["nombre"])})
        else:
            img = dict(x.get("imagen") or {})
            img["ruta_abs"] = (ag.RAIZ / img["archivo"]).resolve().as_uri() if img.get("archivo") else ""
            r.png("story-patrocinio.html", {"patrocinador": dict(x, imagen=img)}, salida / archivo, VIEW_STORY)
            man.append({"archivo": archivo, "patrocinador": x["nombre"], "sector": x["sector"], "alt_text": f"Publicidad: {x['nombre']}"})
    return man


def render_noche(r, eventos, fecha, salida, titulo="Esta noche en", filtrar=True):
    salida.mkdir(parents=True, exist_ok=True)
    for viejo in salida.glob("*.png"):
        viejo.unlink()
    noche = ag.ordenar([e for e in eventos if (not filtrar or ag.es_nocturno(e))])
    grupos = [noche[i:i + NOCHE_POR_STORY] for i in range(0, len(noche), NOCHE_POR_STORY)]
    man = []
    for i, g in enumerate(grupos, start=1):
        r.png("story-noche.html", {"eventos": g, "titulo": titulo, "fecha_larga": ag.fecha_larga(fecha), "pagina": i, "total_paginas": len(grupos)}, salida / f"{i:02d}.png", VIEW_STORY)
        man.append({"archivo": f"{i:02d}.png", "ids": [e.get("id") for e in g], "alt_text": f"{titulo} Cádiz: " + "; ".join(e["nombre"] for e in g)})
    return man


def render_dia(fecha, tipo="diario", var=None):
    carpeta = ag.dir_dia(fecha, tipo)
    datos = ag.cargar_eventos(carpeta)
    estado = ag.cargar_estado(carpeta)
    validos = ag.eventos_validos(datos.get("eventos", []), log=lambda m: ag.log_estado(estado, m))
    if len(validos) < ag.MIN_EVENTOS:
        ag.log_estado(estado, f"{tipo}: 0 eventos verificados; el agente debe completar con «Siempre abierto» (regla 9: se publica todos los días)")
        estado["omitido"] = {tipo: "0 eventos verificados: falta contenido (regla 9)"}
        ag.guardar_estado(carpeta, estado)
        print(f"[{tipo}] 0 eventos verificados: añade eventos o relleno «Siempre abierto» a eventos.json (regla 9: se publica todos los días).")
        return None
    resolver_imagenes(validos, carpeta)
    # Persistir en eventos.json la imagen definitiva de cada evento (oficial, ilustración propia o genérica), sin rutas temporales
    import copy
    por_id = {e.get("id"): e for e in validos}
    guardar = copy.deepcopy(datos)
    for e in guardar.get("eventos", []):
        v = por_id.get(e.get("id"))
        if v:
            e["imagen"] = {k: x for k, x in v["imagen"].items() if k != "ruta_abs"}
    ag.guardar_json(carpeta / "eventos.json", guardar)
    var = var or variante(fecha)
    with Renderer() as r:
        man = {"variante": var, "paleta": paleta(fecha), "carrusel": render_carrusel(r, validos, tipo, fecha, carpeta / "carrusel", var)}
        if tipo == "diario":
            man["stories"] = render_stories(r, validos, fecha, carpeta / "stories")
            man["noche"] = render_noche(r, validos, fecha, carpeta / "noche")
            if not man["noche"] and datos.get("noche_manana"):
                # Sin planes nocturnos hoy, la story de las 18:30 sale igualmente como «Mañana en Cádiz» (eventos de mañana, verificados)
                manana = ag.eventos_validos(datos["noche_manana"], log=lambda m: ag.log_estado(estado, m))
                if manana:
                    resolver_imagenes(manana, carpeta)
                    f2 = (ag.a_fecha(fecha) + __import__("datetime").timedelta(days=1)).isoformat()
                    man["noche"] = render_noche(r, manana, f2, carpeta / "noche", titulo="Mañana en", filtrar=False)
    ag.guardar_json(carpeta / "manifiesto.json", man)
    ag.log_estado(estado, f"{tipo}: render OK ({len(validos)} eventos, variante {var})")
    ag.guardar_estado(carpeta, estado)
    return man


# ---------------------------------------------------------------- demo
NOMBRES_LARGOS = [
    "Gran Concierto Extraordinario de la Orquesta Sinfónica Provincial con Coro Infantil y Solistas Invitados",
    "XLI Festival Iberoamericano de Teatro: Homenaje a las Compañías Históricas de la Ciudad de Cádiz",
    "Taller familiar de cuentacuentos y marionetas tradicionales gaditanas para todas las edades",
]
LUGARES = ["Gran Teatro Falla", "Sala Central Lechera", "Baluarte de la Candelaria", "Castillo de Santa Catalina",
           "Teatro del Títere La Tía Norica", "Museo de Cádiz", "Casa de Iberoamérica", "Palacio de Congresos de Cádiz", "Plaza de San Antonio"]
CATS = ag.CATEGORIAS


def demo_eventos(n, con_fotos):
    evs = []
    for i in range(n):
        cat = CATS[i % len(CATS)]
        nombre = NOMBRES_LARGOS[i % 3] if i % 7 == 3 else f"{cat.capitalize()} de ejemplo número {i + 1}"
        h = 10 + (i * 37) % 13
        ev = {"id": f"demo-{i}", "nombre": nombre, "categoria": cat, "fecha": "2026-10-25",
              "hora_inicio": None if i % 11 == 0 else f"{h:02d}:{(i * 15) % 60:02d}", "todo_el_dia": i % 11 == 0,
              "lugar": LUGARES[i % len(LUGARES)], "direccion": "Plaza Fragela s/n, 11003 Cádiz",
              "precio": ["Gratis", "12 €", "Consultar", "8–15 €"][i % 4], "publico": ["Todos los públicos", "Infantil", "Adultos"][i % 3],
              "descripcion": "Una cita para disfrutar en familia o con amigos, con propuesta cuidada y ambiente de barrio.",
              "info": "Entradas y más info: teatrofalla.com",
              "imagen": {"archivo": "", "alt_text": f"Cartel de {nombre}"}}
        if con_fotos and i % 3 != 0:
            ev["imagen"]["archivo"] = f"_demo/foto{i % 4}.jpg"
        evs.append(ev)
    return evs


def hacer_fotos_demo(destino):
    from PIL import Image, ImageDraw
    destino.mkdir(parents=True, exist_ok=True)
    cols = [(220, 90, 60), (40, 120, 190), (90, 160, 90), (170, 80, 170)]
    for k, c in enumerate(cols):
        im = Image.new("RGB", (900, 700), c)
        d = ImageDraw.Draw(im)
        for j in range(0, 900, 60):
            d.line([(j, 0), (900 - j, 700)], fill=tuple(min(255, x + 40) for x in c), width=14)
        im.save(destino / f"foto{k}.jpg", quality=88)


def demo(ns):
    base = ag.RAIZ / "ejemplos"
    tmp = base / "_demo"
    hacer_fotos_demo(tmp)
    with Renderer() as r:
        for n in ns:
            carpeta = base / f"demo-{n}"
            if carpeta.exists():
                shutil.rmtree(carpeta)
            carpeta.mkdir(parents=True)
            evs = resolver_imagenes(demo_eventos(n, True), base)
            m = render_carrusel(r, evs, "diario", "2026-10-25", carpeta / "carrusel", "A")
            print(f"demo {n}: reparto {ag.reparto(n)} -> {len(m)} imágenes")
            if n == 5:
                render_stories(r, evs[:2], "2026-10-25", carpeta / "stories")
                render_noche(r, [dict(e, hora_inicio="21:00", todo_el_dia=False) for e in evs], "2026-10-25", carpeta / "noche")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=None)
    ap.add_argument("--tipo", default="diario", choices=["diario", "finde", "mensual"])
    ap.add_argument("--variante", choices=["A", "B"])
    ap.add_argument("--demo", nargs="*", type=int)
    a = ap.parse_args()
    if a.demo is not None:
        demo(a.demo or [5, 14, 22, 33, 50])
    else:
        render_dia(a.fecha or ag.hoy().isoformat(), a.tipo, a.variante)
