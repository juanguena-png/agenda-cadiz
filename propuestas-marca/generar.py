#!/usr/bin/env python3
"""Genera las 3 propuestas de identidad visual con las plantillas HTML y render.py.
   python propuestas-marca/generar.py [d1 d2 d3]
Todo el contenido es de ejemplo: imágenes ilustradas generadas aquí (sin material de terceros ni símbolos oficiales)."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import agenda as ag  # noqa: E402
import render as rd  # noqa: E402

AQUI = Path(__file__).parent
PLANT = ag.RAIZ / "plantilla"
VF, VS = rd.VIEW_FEED, rd.VIEW_STORY

# ---------------------------------------------------------------- paletas de ilustración por tema
PAL = {
    "d1": dict(bg1="#BFE6EE", bg2="#0E6BA8", a="#FFC62B", b="#FFFFFF", c="#0A2E4D", ink="#FAF8F2"),
    "d2": dict(bg1="#FF4F93", bg2="#2A0B4F", a="#FFD83D", b="#25D9C7", c="#FF8A1F", ink="#FFFFFF"),
    "d3": dict(bg1="#F1EEE8", bg2="#DAD5CB", a="#B72D19", b="#111111", c="#8C8579", ink="#111111"),
}
CATCOL = {  # color de fondo de las imágenes genéricas por categoría (por tema)
    "d1": ["#0E6BA8", "#2A86B8", "#F2A900", "#1C7FA6", "#2F8F83", "#D9822B", "#0A5C8F", "#4B7BA8"],
    "d2": ["#FF4F93", "#8E44EC", "#FF8A1F", "#25B8D9", "#29C46B", "#E8A800", "#E83E8C", "#5E5CE6"],
    "d3": ["#F1EEE8"] * 8,
}
ICONOS = {  # trazos 100x100
    "música": '<path d="M38 70V30l34-8v40" /><circle cx="30" cy="70" r="9"/><circle cx="64" cy="62" r="9"/>',
    "teatro": '<path d="M20 28h34v22a17 17 0 0 1-34 0z"/><path d="M46 44h34v22a17 17 0 0 1-34 0z"/><path d="M30 40q4 4 8 0M58 58q4 4 8 0"/>',
    "infantil": '<circle cx="50" cy="40" r="22"/><path d="M50 62v26M50 74l8 6"/>',
    "exposición": '<rect x="22" y="24" width="56" height="44" rx="3"/><path d="M30 60l14-16 10 10 8-8 10 14"/><path d="M40 78h20"/>',
    "deporte": '<circle cx="50" cy="50" r="30"/><path d="M50 20v60M20 50h60M29 29q21 21 42 0M29 71q21-21 42 0"/>',
    "gastronomía": '<path d="M32 22v22a6 6 0 0 0 12 0V22M38 22v56M66 22c-8 8-8 30 0 34v22"/>',
    "fiesta": '<path d="M24 78l14-40 28 28z"/><path d="M52 30l4-10M66 38l10-4M62 52l12 2"/><circle cx="76" cy="22" r="2"/><circle cx="84" cy="44" r="2"/>',
    "otros": '<path d="M50 20l8 20 22 2-17 14 6 22-19-12-19 12 6-22-17-14 22-2z"/>',
}


def svg_generica(t, i, trazos):
    p = PAL[t]
    trazo = {"d1": "#FFFFFF", "d2": "#FFFFFF", "d3": "#111111"}[t]
    sol = {"d1": '<circle cx="82" cy="18" r="22" fill="#FFC62B"/>', "d2": '<circle cx="82" cy="18" r="22" fill="#FFD83D"/><circle cx="14" cy="88" r="12" fill="#25D9C7"/>',
           "d3": '<circle cx="82" cy="18" r="9" fill="#B72D19"/>'}[t]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="1200" height="1200"><rect width="100" height="100" fill="{CATCOL[t][i]}"/>{sol}'
            f'<g fill="none" stroke="{trazo}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">{trazos}</g></svg>')


def escenas(t):
    p = PAL[t]
    g = f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p["bg1"]}"/><stop offset="1" stop-color="{p["bg2"]}"/></linearGradient></defs><rect width="120" height="120" fill="url(#g)"/>'
    S = {}
    S["concierto"] = g + (f'<polygon points="30,0 18,70 46,70" fill="{p["a"]}" opacity=".45"/><polygon points="90,0 74,70 102,70" fill="{p["b"]}" opacity=".45"/>'
                          f'<rect x="0" y="78" width="120" height="42" fill="{p["c"]}"/>' + "".join(f'<circle cx="{8+i*14}" cy="{88+(i%3)*5}" r="6" fill="{p["bg2"] if t!="d3" else "#111"}"/>' for i in range(9)))
    S["mar"] = g + (f'<circle cx="60" cy="62" r="24" fill="{p["a"]}"/><rect x="0" y="66" width="120" height="54" fill="{p["bg2"] if t!="d3" else "#8C8579"}"/>'
                    f'<g fill="none" stroke="{p["b"]}" stroke-width="1.6" opacity=".8"><path d="M0 78q10-5 20 0t20 0 20 0 20 0 20 0 20 0"/><path d="M0 92q10-5 20 0t20 0 20 0 20 0 20 0 20 0"/></g>'
                    f'<path d="M20 64l16 0-8-18z" fill="{p["ink"]}"/>')
    S["teatro"] = g + (f'<circle cx="60" cy="70" r="30" fill="{p["a"]}" opacity=".5"/><path d="M0 0h42q-14 40-6 120H0z" fill="{p["c"]}"/><path d="M120 0H78q14 40 6 120h36z" fill="{p["c"]}"/>'
                       f'<rect x="0" y="104" width="120" height="16" fill="{p["bg2"] if t!="d3" else "#111"}"/>')
    S["globos"] = g + "".join(f'<ellipse cx="{x}" cy="{y}" rx="13" ry="16" fill="{col}"/><path d="M{x} {y+16}q-4 14 2 30" stroke="{p["ink"]}" fill="none" stroke-width="1"/>'
                              for x, y, col in [(30, 40, p["a"]), (60, 26, p["b"]), (90, 44, p["c"]), (45, 70, p["c"]), (78, 78, p["a"])])
    S["futbol"] = (f'<rect width="120" height="120" fill="{p["bg2"] if t!="d3" else "#DAD5CB"}"/><g fill="none" stroke="{p["ink"]}" stroke-width="1.6" opacity=".8"><rect x="10" y="10" width="100" height="100"/><path d="M10 60h100"/><circle cx="60" cy="60" r="14"/></g>'
                   f'<circle cx="60" cy="60" r="9" fill="{p["a"]}" stroke="{p["ink"]}" stroke-width="1.6"/>')
    S["gastro"] = g + (f'<circle cx="60" cy="66" r="34" fill="{p["ink"]}"/><circle cx="60" cy="66" r="24" fill="none" stroke="{p["c"]}" stroke-width="2"/>'
                       f'<circle cx="52" cy="62" r="7" fill="{p["a"]}"/><circle cx="68" cy="70" r="6" fill="{p["b"] if t!="d1" else p["c"]}"/>'
                       f'<g fill="none" stroke="{p["ink"]}" stroke-width="1.6" stroke-linecap="round" opacity=".8"><path d="M50 22q-6 8 0 14M64 18q-6 8 0 14"/></g>')
    return {k: f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="1200" height="1200">{v}</svg>' for k, v in S.items()}


def pngs_ilustraciones(r, t, carpeta):
    carpeta.mkdir(parents=True, exist_ok=True)
    pg = r.browser.new_page(viewport={"width": 1200, "height": 1200})
    for i, (cat, tr) in enumerate(ICONOS.items()):
        pg.set_content(f'<body style="margin:0">{svg_generica(t, i, tr)}</body>')
        pg.screenshot(path=str(carpeta / f"sinfoto-{cat}.png"))
    for k, s in escenas(t).items():
        pg.set_content(f'<body style="margin:0">{s}</body>')
        pg.screenshot(path=str(carpeta / f"ej-{k}.png"))
    pg.close()


# ---------------------------------------------------------------- datos de ejemplo
EJ = [  # nombre, categoria, ini, fin, lugar, precio, publico, imagen
    ("Concierto de jazz frente al mar", "música", "20:30", "22:00", "Paseo marítimo", "Gratis", "Todos los públicos", "concierto"),
    ("Cuentacuentos y globos", "infantil", "11:00", "12:00", "Biblioteca municipal", "Gratis", "Infantil", "globos"),
    ("La función del fantasma", "teatro", "21:00", "22:30", "Teatro principal", "12 €", "Adultos", "teatro"),
    ("Exposición de fotografía del puerto", "exposición", "10:00", "20:00", "Sala de exposiciones", "Gratis", "Todos los públicos", "mar"),
    ("Carrera popular de la bahía", "deporte", "09:30", None, "Parque de la ciudad", "5 €", "Todos los públicos", "futbol"),
    ("Gran concierto extraordinario de la orquesta sinfónica con coro infantil y solistas invitados", "música", "19:00", None, "Auditorio municipal", "8–15 €", "Todos los públicos", "concierto"),
]


def eventos_ej(t, n, base):
    evs = []
    for i in range(n):
        nombre, cat, ini, fin, lugar, precio, pub, img = EJ[i % len(EJ)]
        evs.append({"id": f"ej{i}", "nombre": nombre, "categoria": cat, "fecha": "2026-11-06", "hora_inicio": ini, "hora_fin": fin, "todo_el_dia": False,
                    "lugar": lugar, "direccion": "Calle de ejemplo 1, 11001 Cádiz", "precio": precio, "publico": pub,
                    "descripcion": "Una cita para disfrutar en familia o con amigos, con propuesta cuidada y ambiente de barrio. Plazas limitadas.",
                    "info": "Más info: ejemplo.es", "imagen": {"archivo": str((base / f"ej-{img}.png").relative_to(ag.RAIZ)), "alt_text": f"Ilustración de ejemplo: {cat}"}})
    return rd.resolver_imagenes(evs, ag.RAIZ)


# ---------------------------------------------------------------- render con tema + auditoría
AUDIT_JS = """() => {
 const pr = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if(!m) return null; const p = m[1].split(',').map(Number); return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}; };
 const lum = c => { const f = v => { v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4)}; return .2126*f(c.r)+.7152*f(c.g)+.0722*f(c.b); };
 const fondo = el => { for (let e=el; e; e=e.parentElement) { const cs=getComputedStyle(e); const c=pr(cs.backgroundColor);
     if (c && c.a>0.95) return c;
     if (cs.backgroundImage.includes('gradient')) { const m=cs.backgroundImage.match(/rgb[a]?\\([^)]+\\)/); if(m) return pr(m[0]); } } return {r:255,g:255,b:255,a:1}; };
 const out=[]; const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 while(w.nextNode()){ const n=w.currentNode; if(!n.textContent.trim()) continue; const el=n.parentElement; const cs=getComputedStyle(el);
   if(cs.display==='none'||cs.visibility==='hidden') continue; const fg=pr(cs.color); const bg=fondo(el);
   const L1=lum(fg),L2=lum(bg); const ratio=(Math.max(L1,L2)+.05)/(Math.min(L1,L2)+.05);
   out.push({t:n.textContent.trim().slice(0,28), px:parseFloat(cs.fontSize), peso:cs.fontWeight, ratio:+ratio.toFixed(2)}); }
 return out; }"""
AUDITORIA = {}


def png_t(r, t, plantilla, datos, salida, vp, auditar=None):
    pg = r.browser.new_page(viewport=vp, device_scale_factor=1)
    pg.goto((PLANT / plantilla).as_uri())
    pg.add_style_tag(url=(PLANT / "temas" / f"{t}.css").as_uri())
    datos = dict(datos, tema=t)
    pg.evaluate("d => render(d)", datos)
    pg.wait_for_timeout(250)
    if auditar:
        AUDITORIA.setdefault(t, {})[auditar] = pg.evaluate(AUDIT_JS)
    pg.screenshot(path=str(salida), clip={"x": 0, "y": 0, **vp})
    pg.close()


def png_alto(r, t, plantilla, datos, salida, ancho):
    pg = r.browser.new_page(viewport={"width": ancho, "height": 800})
    pg.goto((PLANT / plantilla).as_uri())
    pg.add_style_tag(url=(PLANT / "temas" / f"{t}.css").as_uri())
    pg.evaluate("d => render(d)", dict(datos, tema=t))
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(salida), full_page=True)
    pg.close()


TEXTOS = {
    "d1": dict(nombre="Planes en Cádiz · Agenda diaria", bio="☀️ Qué hacer hoy en Cádiz, cada mañana a las 9:00\n🌊 Gratis · Finde · Lo mejor del mes\n👇 Comenta PLANES y te la mandamos"),
    "d2": dict(nombre="Planes en Cádiz · Agenda diaria", bio="🎉 Todos los planes de Cádiz, cada día a las 9:00\n🎭 Gratis, finde y fiesta\n💬 Comenta PLANES y te la enviamos"),
    "d3": dict(nombre="Planes en Cádiz · Agenda diaria", bio="La agenda de Cádiz, cada día a las 9:00.\nCultura, música, teatro, deporte y plan gratis.\nComenta PLANES y la recibes en tu bandeja."),
}


def direccion(r, t):
    out = AQUI / {"d1": "direccion-1", "d2": "direccion-2", "d3": "direccion-3"}[t]
    out.mkdir(exist_ok=True)
    ilu = out / "ilustraciones"
    pngs_ilustraciones(r, t, ilu)
    # logo modular
    ciudades = [dict(prefijo="Planes en", ciudad="Cádiz", nota="Cádiz (corto)"), dict(prefijo="Planes en", ciudad="Valladolid", nota="Valladolid (largo)"),
                dict(prefijo="Plans in", ciudad="Lisbon", nota="Plans in Lisbon (EN)")]
    png_alto(r, t, "logo.html", {"ciudades": ciudades}, out / "01-logo-modular.png", 1600)
    png_alto(r, t, "logo.html", {"ciudades": [dict(prefijo="Planes en", ciudad="San Cristóbal de las Casas", nota="Nombre muy largo"), dict(prefijo="Planes en", ciudad="Roma", nota="Nombre muy corto"),
                                                dict(prefijo="Planes en", ciudad="Bogotá", nota="Bogotá")]}, out / "01b-logo-nombres-extremos.png", 1600)
    # perfil
    png_t(r, t, "perfil.html", {"modo": "avatar", "ciudad": "Cádiz"}, out / "02-foto-perfil-320.png", {"width": 320, "height": 320})
    png_t(r, t, "perfil.html", {"modo": "prueba", "ciudad": "Cádiz"}, out / "02b-foto-perfil-prueba-circulo.png", {"width": 1000, "height": 440})
    # portadas
    base = dict(ciudad="Cádiz", prefijo="Planes en")
    png_t(r, t, "portada.html", dict(base, titulo="Qué hacer hoy", subtitulo="viernes 6 de noviembre", total=12, etiqueta="Agenda diaria"), out / "03-portada-diaria.png", VF, "portada")
    png_t(r, t, "portada.html", dict(base, titulo="Planes del finde", subtitulo="6 – 8 de noviembre", total=24, etiqueta="Viernes a domingo", sufijo="para el finde"), out / "09-portada-finde.png", VF)
    png_t(r, t, "portada.html", dict(base, titulo="Lo más destacado de noviembre", subtitulo="noviembre 2026", total=9, etiqueta="Agenda mensual", sufijo="imprescindibles"), out / "10-portada-mensual.png", VF)
    # eventos 1, 3, 6
    for n in (1, 3, 6):
        png_t(r, t, "eventos.html", dict(base, eventos=eventos_ej(t, n, ilu), cabecera="2/9"), out / f"04-eventos-{n}.png", VF, f"eventos{n}")
    ev0 = eventos_ej(t, 1, ilu)[0]
    png_t(r, t, "story.html", dict(base, evento=ev0, fecha_larga="viernes 6 de noviembre"), out / "05-story-evento.png", VS, "story")
    png_t(r, t, "story-noche.html", dict(base, eventos=eventos_ej(t, 3, ilu)[:3], fecha_larga="viernes 6 de noviembre", pagina=1, total_paginas=1), out / "06-story-esta-noche.png", VS, "noche")
    # sin foto (2 categorías) -> la propia imagen genérica
    for cat in ("música", "infantil"):
        (out / f"07-sin-foto-{cat}.png").write_bytes((ilu / f"sinfoto-{cat}.png").read_bytes())
    # destacadas
    for k, et in (("hoy", "Hoy"), ("finde", "Finde"), ("mes", "Este mes"), ("gratis", "Gratis")):
        png_t(r, t, "destacada.html", dict(base, icono=k, etiqueta=et), out / f"08-destacada-{k}.png", VS, "destacada" if k == "hoy" else None)
    # patrocinada
    patro = {"nombre": "Heladería Ejemplo", "texto": "Helados artesanos en el centro. Enseña esta story y llévate un topping gratis.", "imagen": {"ruta_abs": (ilu / "ej-gastro.png").as_uri(), "alt_text": "Ilustración de ejemplo: plato"}}
    png_t(r, t, "story-patrocinio.html", dict(base, patrocinador=patro), out / "11-story-patrocinada.png", VS, "patrocinio")
    # mosaico 3x3
    seq = ["03-portada-diaria", "04-eventos-3", "09-portada-finde", "04-eventos-1", "10-portada-mensual", "04-eventos-6", "03-portada-diaria", "04-eventos-3", "09-portada-finde"]
    t_ = TEXTOS[t]
    png_alto(r, t, "mosaico.html", {"avatar": (out / "02-foto-perfil-320.png").as_uri(), "nombre": t_["nombre"], "bio": t_["bio"], "imagenes": [(out / f"{s}.png").as_uri() for s in seq]},
             out / "12-mosaico-perfil.png", 1080)
    return out


def main(temas):
    with rd.Renderer() as r:
        for t in temas:
            print("tema", t, direccion(r, t))
    ag.guardar_json(AQUI / "auditoria.json", AUDITORIA)


if __name__ == "__main__":
    main(sys.argv[1:] or ["d1", "d2", "d3"])
