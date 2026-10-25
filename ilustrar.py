#!/usr/bin/env python3
"""Ilustraciones PROPIAS para eventos sin imagen oficial (regla 7).

Cada ilustración se compone con motivos vectoriales relacionados con el propio evento (guitarra para un concierto de flamenco, barco para
una muestra sobre el mar, calabaza para Halloween...), elegidos por palabras clave del nombre, la descripción y la categoría, en la paleta
de la marca (D1: mar, noche, cal, bruma, sol). Sin texto, sin logos ni material de terceros.

  python ilustrar.py --nombre "Concierto de jazz" --categoria música            # vista previa en ejemplos/ilustraciones/
  python ilustrar.py --catalogo                                                  # hoja con todos los motivos

El agente puede afinar una ilustración en eventos.json: "ilustracion": {"motivos": ["barco", "marco"], "fondo": "mar"}.
"""
import argparse
import hashlib
import re
import unicodedata
from pathlib import Path

import agenda as ag

FONDOS = {  # nombre: (fondo1, fondo2, trazo, acento, hueco)
    "mar": ("#0E6BA8", "#0A5A94", "#FAF8F2", "#FFC62B", "#0A5A94"),
    "bruma": ("#BFE6EE", "#9FD3E0", "#0A2E4D", "#FFC62B", "#BFE6EE"),
    "noche": ("#0A2E4D", "#071D33", "#FAF8F2", "#FFC62B", "#0A2E4D"),
    "sol": ("#FFC62B", "#F5B400", "#0A2E4D", "#FAF8F2", "#FFC62B"),
    "cal": ("#FAF8F2", "#EEF5F7", "#0E6BA8", "#FFC62B", "#FAF8F2"),
}
ORDEN_FONDOS = ["mar", "bruma", "noche", "sol", "cal"]

# motivo: (palabras clave (regex sobre texto sin tildes), dibujo 100x100). {S}=trazo, {A}=acento, {B}=hueco del fondo
M = {}


def motivo(nombre, patron, svg):
    M[nombre] = (re.compile(patron), svg)


motivo("mantón", r"manton|manila|flamenca|abanico|sevillana", '<path d="M50 82L18 38a42 42 0 0 1 64 0z" fill="{A}"/><path d="M50 82L34 30M50 82V24M50 82L66 30"/><path d="M18 38q32-10 64 0"/>')
motivo("flamenco", r"flamenc|guitarr|cante|tablao|tomatito|ruibal|vicente amigo|bulerias|soleares|cantaor|tocaor", '<g transform="rotate(32 50 52)"><rect x="46" y="4" width="8" height="40" rx="2"/><rect x="43" y="-2" width="14" height="9" rx="2"/><path d="M50 40c-16 0-18 10-11 17-7 7-7 24 11 24s18-17 11-24c7-7 5-17-11-17z" fill="{A}"/><circle cx="50" cy="62" r="5" fill="{B}"/></g>')
motivo("jazz", r"jazz|saxo|blues|swing|trompeta", '<path d="M34 8h12l8 10 12 42c3 10 14 12 20 4 4-6 3-14-3-20"/><ellipse cx="80" cy="42" rx="11" ry="6" transform="rotate(-35 80 42)" fill="{A}"/><circle cx="52" cy="26" r="2.6" fill="{S}"/><circle cx="58" cy="40" r="2.6" fill="{S}"/><circle cx="64" cy="54" r="2.6" fill="{S}"/><path d="M28 8h8"/>')
motivo("piano", r"piano|recital|perianes|sinfon|orquesta|camara|requiem|clasic|cuarteto|opera|lieder", '<rect x="10" y="38" width="80" height="42" rx="4"/><path d="M24 38v22M36 38v22M52 38v22M64 38v22M76 38v22" stroke-width="5"/><path d="M30 60v20M42 60v20M58 60v20M70 60v20"/><circle cx="26" cy="22" r="6" fill="{A}"/><path d="M32 22V8l16-4"/>')
motivo("micrófono", r"microfon|monolog|humor|stand ?up|comedia|conferencia|charla|coloquio|pregon|presentacion|debate|tertulia", '<rect x="38" y="10" width="24" height="38" rx="12" fill="{A}"/><path d="M28 40c0 16 10 24 22 24s22-8 22-24M50 64v18M36 84h28"/><path d="M38 28h24"/>')
motivo("rock", r"\brock\b|\bpop\b|indie|\bbandas?\b|\brap\b|hip ?hop|\bdj\b|electronic|punk|\bmetal\b|reggae|\btrap\b|tributo", '<ellipse cx="50" cy="52" rx="28" ry="11" fill="{A}"/><path d="M22 52v22c0 6 12 11 28 11s28-5 28-11V52"/><path d="M28 12l18 30M72 12L54 42"/>')
motivo("violín", r"violin|cuerda|viola|violonc|chelo", '<path d="M50 4v24"/><path d="M40 30c-8 2-10 10-4 16-8 6-8 18 2 26 6 5 18 5 24 0 10-8 10-20 2-26 6-6 4-14-4-16-4-1-8 0-10 4-2-4-6-5-10-4z" fill="{A}"/><path d="M50 44v32M42 58q-4 4 0 8M58 58q4 4 0 8"/><path d="M84 28L76 90"/>')
motivo("baile", r"danza|baile|ballet|bailaora|zumba|coreograf|salsa|bachata|tango", '<circle cx="50" cy="18" r="8" fill="{A}"/><path d="M50 27c-4 10-2 20 5 28"/><path d="M50 34c-12-8-20-8-26 0M50 34c10-10 18-14 26-8"/><path d="M57 55c14 2 26 12 27 26-20-5-40-5-62 0 2-14 14-24 35-26z" fill="{A}"/>')
motivo("máscaras", r"teatro|obra|funcion|dramatur|tragicomedia|musical|actor|actriz|escena|verborrea|compania|lectura dramatizada", '<path d="M16 24h38v24a19 19 0 0 1-38 0z" fill="{A}"/><path d="M46 40h38v24a19 19 0 0 1-38 0z"/><path d="M26 38q4 5 10 0M24 50q8 7 16 0M56 56q4 5 10 0M58 70q8-7 16 0"/>')
motivo("títere", r"titere|marioneta|tia norica|guinol|bichitos|retablo", '<path d="M26 10h48M38 10l8 24M62 10l-8 24M50 10v14"/><circle cx="50" cy="42" r="10" fill="{A}"/><path d="M50 52v22M50 58l-16 10M50 58l16 10M50 74l-9 16M50 74l9 16"/>')
motivo("cine", r"cine|pelicula|filmo|documental|proyeccion|cortometraje|audiovisual|largometraje|festival de cine|muestra cinematografica", '<rect x="14" y="40" width="72" height="44" rx="4"/><path d="M14 40l8-20h68l-8 20M30 40l8-20M52 40l8-20M74 40l8-20"/><path d="M44 54l16 10-16 10z" fill="{A}"/>')
motivo("libro", r"libro|lectura|poesia|poeta|biblioteca|literar|club de lectura|narrativa|novela|autor|escritor|cuento", '<path d="M50 26c-10-8-26-8-38-4v54c12-4 28-4 38 4 10-8 26-8 38-4V22c-12-4-28-4-38 4zM50 26v54" fill="none"/><path d="M62 38h16M62 48h16M22 38h16M22 48h16"/><path d="M70 8l3 7 7 1-5 5 1 8-6-4-6 4 1-8-5-5 7-1z" fill="{A}"/>')
motivo("escultura", r"escultur|busto|zitman|vassallo|piedra|bronce|estatua", '<circle cx="50" cy="26" r="13" fill="{A}"/><path d="M24 74c0-18 10-28 26-28s26 10 26 28z"/><rect x="18" y="74" width="64" height="12" rx="2"/>')
motivo("marco", r"exposicion|muestra|pintura|fotograf|galeria|coleccion|pintor|dibujo|grabado|instalacion|arte contempor|artista", '<rect x="12" y="22" width="76" height="56" rx="4"/><rect x="20" y="30" width="60" height="40" rx="2" fill="{A}" fill-opacity=".35"/><path d="M24 64l16-18 12 12 10-10 14 16"/><circle cx="68" cy="40" r="6" fill="{A}"/>')
motivo("globos", r"infantil|ninos|ninas|familia|peques|cuentacuentos|taller infantil|juegos|ludoteca|fiesta infantil|los mas pequenos", '<ellipse cx="32" cy="38" rx="15" ry="19" fill="{A}"/><ellipse cx="64" cy="30" rx="15" ry="19"/><ellipse cx="52" cy="62" rx="15" ry="19" fill="{A}" fill-opacity=".6"/><path d="M32 57q-6 14 6 30M64 49q4 14-10 38M52 81q-2 6 0 8"/>')
motivo("calabaza", r"halloween|terror|brujas|tosantos|difuntos|monstruo|miedo", '<path d="M50 30c-26-8-40 10-36 26 4 16 20 26 36 26s32-10 36-26c4-16-10-34-36-26z" fill="{A}"/><path d="M48 30c0-8 4-14 12-16"/><path d="M34 52l8 10h-16zM66 52l8 10H58zM38 72q12 8 24 0"/>')
motivo("navidad", r"navidad|villancic|zambomba|belen|reyes magos|cortejo real|nochebuena|nochevieja|gala de navidad|autos de navidad", '<path d="M50 20l-22 26h12L24 68h16L22 88h56L60 68h16L60 46h12z" fill="none"/><path d="M50 4l4 9 10 1-7 7 2 10-9-5-9 5 2-10-7-7 10-1z" fill="{A}"/><circle cx="40" cy="62" r="3" fill="{A}"/><circle cx="60" cy="74" r="3" fill="{A}"/>')
motivo("antifaz", r"carnaval|chirigota|comparsa|cuarteto de carnaval|coro de carnaval|antifaz|cabalgata|disfraz", '<path d="M10 40c12-9 26-9 40 0 14-9 28-9 40 0-2 18-13 28-28 22-6-3-9-8-12-8s-6 5-12 8C23 68 12 58 10 40z" fill="{A}"/><circle cx="32" cy="48" r="6" fill="{B}"/><circle cx="68" cy="48" r="6" fill="{B}"/><path d="M80 20l8-10M20 20L12 10M50 18V6"/>')
motivo("barco", r"\bmar\b|galeon|naval|vela|regata|nautic|marin|barco|navegacion|ruta del galeon|crucero|embarcacion", '<path d="M50 10v52"/><path d="M52 14l26 42H52z" fill="{A}"/><path d="M48 24L26 56h22"/><path d="M14 66h72l-10 16H24z"/><path d="M8 92q10-6 21 0t21 0 21 0 21 0"/>')
motivo("ancla", r"ancla|faro|caleta|playa|litoral|costa|baluarte|atlantic", '<circle cx="50" cy="18" r="8" fill="{A}"/><path d="M50 26v56M34 40h32M16 62c4 18 20 24 34 24s30-6 34-24M16 62l-6 8M84 62l6 8"/>')
motivo("balón", r"futbol|cadiz cf|partido de liga|liga hypermotion|nuevo mirandilla|jornada|copa del rey", '<circle cx="50" cy="50" r="34"/><path d="M50 33l15 11-6 17H41l-6-17z" fill="{A}"/><path d="M50 33V16M65 44l17-6M59 61l10 15M41 61L31 76M35 44l-17-6"/>')
motivo("baloncesto", r"baloncesto|basket|canasta|nba|acb", '<circle cx="50" cy="50" r="34" fill="{A}" fill-opacity=".45"/><circle cx="50" cy="50" r="34"/><path d="M50 16v68M16 50h68M27 26c12 14 12 34 0 48M73 26c-12 14-12 34 0 48"/>')
motivo("corredor", r"\bcarrera|running|atletismo|maraton|senderismo|ruta saludable|\bmarcha\b|\btrail\b|\bcross\b|criterium|san silvestre|\b10k\b|\b5k\b", '<circle cx="60" cy="16" r="8" fill="{A}"/><path d="M56 26l-12 22 16 12 4 22M44 48l-18 8M56 26l20 10 8-8M62 62l20 8"/><path d="M12 84h76"/>')
motivo("ola", r"natacion|surf|kayak|buceo|piragu|snorkel|paddle|windsurf|kitesurf|waterpolo|bano", '<circle cx="62" cy="30" r="8" fill="{A}"/><path d="M38 44l18-4 16 10"/><path d="M8 62q11-14 21 0t21 0 21 0 21 0M8 80q11-14 21 0t21 0 21 0 21 0"/>')
motivo("bici", r"ciclis|bicicleta|\bbici\b|\bbtt\b|pedalada", '<circle cx="24" cy="64" r="17"/><circle cx="76" cy="64" r="17"/><path d="M24 64l17-30h27l8 30M41 34l15 30H24M60 28h14M34 28h14"/><circle cx="56" cy="64" r="4" fill="{A}"/>')
motivo("copa", r"vino|cata|degustacion|bodega|jerez|sherry|cerveza|coctel|brindis|maridaje|vermut|manzanilla", '<path d="M32 12h36c0 28-5 44-18 44S32 40 32 12z"/><path d="M34 28h32c-1 16-6 28-16 28S35 44 34 28z" fill="{A}"/><path d="M50 56v28M34 88h32"/>')
motivo("plato", r"tapas|gastronom|cocina|menu|ruta gastronomica|atun|ronqueo|pescaito|mercado gastronomico|restaurante|chef|show cooking|comida|tabanco|tortillitas", '<circle cx="50" cy="52" r="30"/><circle cx="50" cy="52" r="20" fill="{A}" fill-opacity=".5"/><path d="M14 18v20a5 5 0 0 0 10 0V18M19 18v64M86 18c-8 8-8 26 0 30v34"/>')
motivo("mercadillo", r"mercadillo|feria de|mercado|artesan|rastro|puestos|bazar|vintage|segunda mano", '<path d="M10 40l8-22h64l8 22c0 9-10 9-14 0-4 9-12 9-16 0-4 9-12 9-16 0-4 9-12 9-16 0-4 9-14 9-14 0z" fill="{A}"/><path d="M18 50v34M82 50v34M18 84h64"/><rect x="36" y="62" width="28" height="14" rx="2"/>')
motivo("mapa", r"ruta|visita|tour|paseo|itinerario|guiada|descubre|recorrido|yacimiento|catacumbas|gymkana|orientacion", '<path d="M12 26l25-9 26 9 25-9v57l-25 9-26-9-25 9z"/><path d="M37 17v57M63 26v57"/><path d="M50 32c-9 0-13 7-13 13 0 9 13 22 13 22s13-13 13-22c0-6-4-13-13-13z" fill="{A}"/><circle cx="50" cy="45" r="4" fill="{B}"/>')
motivo("castillo", r"castillo|baluarte|torre|muralla|fortaleza|santa catalina|san sebastian|puertas de tierra|tavira", '<path d="M14 86V42h12v-9h8v9h8V30h16v12h8v-9h8v9h12v44z"/><path d="M42 86V66a8 8 0 0 1 16 0v20" fill="{A}"/><path d="M26 56v6M74 56v6"/>')
motivo("cúpula", r"catedral|iglesia|semana santa|procesion|cofradia|misa|parroquia|oratorio|ermita|santuario|virgen|cristo|romeria", '<path d="M22 84V58a28 28 0 0 1 56 0v26z"/><path d="M50 30V12M43 19h14"/><path d="M34 84V62M50 84V58M66 84V62" /><path d="M50 30a28 28 0 0 0-28 28h56A28 28 0 0 0 50 30z" fill="{A}" fill-opacity=".5"/>')
motivo("bombilla", r"taller|curso|formacion|jornada|congreso|simposio|foro|seminario|mesa redonda|encuentro|innovacion|emprend|empresa|tecnolog", '<path d="M50 12c-15 0-24 10-24 23 0 10 7 15 9 24h30c2-9 9-14 9-24 0-13-9-23-24-23z" fill="{A}"/><path d="M38 66h24M42 76h16M44 86h12"/><path d="M50 2v4M14 20l4 3M86 20l-4 3"/>')
motivo("ajedrez", r"ajedrez|torneo de|juegos de mesa|\bdamas\b", '<path d="M50 8v10M44 13h12"/><path d="M40 28h20l-5 18c9 4 12 14 12 22H33c0-8 3-18 12-22z" fill="{A}"/><rect x="26" y="76" width="48" height="10" rx="2"/>')
motivo("yoga", r"yoga|pilates|meditacion|mindfulness|bienestar|salud|zen|relajacion", '<circle cx="50" cy="20" r="8" fill="{A}"/><path d="M50 29v24M50 36L30 52M50 36l20 16M28 74c12-8 32-8 44 0M34 64l16-12 16 12"/>')
motivo("confeti", r"fiesta|verbena|celebracion|aniversario|gala|cumple|bienvenida|inauguracion|fin de ano|despedida|baile de|noche de", '<path d="M18 86l16-46 32 30z" fill="{A}"/><path d="M50 30l5-12M68 40l12-5M64 58l15 2"/><circle cx="80" cy="16" r="3" fill="{S}"/><circle cx="88" cy="46" r="3" fill="{A}"/><circle cx="40" cy="14" r="3" fill="{S}"/>')
motivo("noche", r"noche|nocturn|luna|astronom|estrellas|observacion|planetario|eclipse", '<path d="M62 14a34 34 0 1 0 22 56A28 28 0 0 1 62 14z" fill="{A}"/><path d="M24 24l2 5 5 2-5 2-2 5-2-5-5-2 5-2zM80 66l2 4 4 2-4 2-2 4-2-4-4-2 4-2z"/>')
motivo("atardecer", r"atardecer|amanecer|puesta de sol|sunset|paseando hacia", '<path d="M18 62a32 32 0 0 1 64 0z" fill="{A}"/><path d="M8 62h84M16 74h68M26 86h48"/><path d="M50 8v10M20 22l7 7M80 22l-7 7"/>')
motivo("estrella", r"$^", '<path d="M50 10l11 25 27 3-20 18 6 27-24-14-24 14 6-27L12 38l27-3z" fill="{A}"/>')

CATEGORIA_DEFECTO = {"música": "piano", "teatro": "máscaras", "infantil": "globos", "exposición": "marco", "deporte": "balón", "gastronomía": "plato", "fiesta": "confeti", "otros": "estrella"}
# Prioridad cuando varios motivos puntúan igual (de más específico a más genérico)
PRIORIDAD = list(M)
GENERICOS = {"globos", "marco", "mapa", "bombilla", "micrófono", "confeti", "plato", "piano", "libro", "noche", "estrella"}  # a igualdad de puntos, gana lo específico


def norm(t):
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def elegir_motivos(ev, n=3):
    manual = (ev.get("ilustracion") or {}).get("motivos")
    if manual:
        return [m for m in manual if m in M][:n]
    nombre, resto = norm(ev.get("nombre")), norm(f"{ev.get('descripcion', '')} {ev.get('categoria_fuente', '')} {ev.get('lugar', '')}")
    puntos = []
    for i, (k, (rx, _)) in enumerate(M.items()):
        s = 3 * len(rx.findall(nombre)) + len(rx.findall(resto))
        if s:
            puntos.append((-s, 1 if k in GENERICOS else 0, i, k))
    puntos.sort()
    elegidos = [p[-1] for p in puntos][:n]
    cat = CATEGORIA_DEFECTO.get(ev.get("categoria"), "estrella")
    if not elegidos:
        elegidos = [cat]
    elif len(elegidos) < 2 and cat not in elegidos:
        elegidos.append(cat)
    return elegidos


def componer_svg(ev, motivos=None):
    clave = (ev.get("ilustracion") or {}).get("fondo")
    h = int(hashlib.md5(str(ev.get("id") or ev.get("nombre")).encode()).hexdigest(), 16)
    fondo = clave if clave in FONDOS else ORDEN_FONDOS[h % len(ORDEN_FONDOS)]
    b1, b2, S, A, B = FONDOS[fondo]
    motivos = motivos or elegir_motivos(ev)

    def dibujo(k, sw):
        return f'<g fill="none" stroke="{S}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{M[k][1].format(S=S, A=A, B=B)}</g>'
    sol = f'<circle cx="101" cy="17" r="25" fill="{A}" opacity="{0.55 if fondo == "sol" else 0.95}"/>'
    olas = "".join(f'<path d="M-4 {y}q10-7 20 0t20 0 20 0 20 0 20 0 20 0 20 0" fill="none" stroke="{S}" stroke-opacity=".28" stroke-width="1.2"/>' for y in (103, 109, 115))
    sec = ""
    pos = [(3, 78), (88, 78)]
    for (x, y), k in zip(pos, motivos[1:3]):
        sec += f'<g transform="translate({x} {y}) scale(.29)" opacity=".95">{dibujo(k, 8)}</g>'
    principal = f'<g transform="translate(14 6) scale(.92)">{dibujo(motivos[0], 3.6)}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="1200" height="1200"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{b1}"/><stop offset="1" stop-color="{b2}"/></linearGradient></defs><rect width="120" height="120" fill="url(#g)"/>{sol}{olas}{principal}{sec}</svg>')


def generar(ev, carpeta_img):
    """Crea posts/F/img/<id>.svg y devuelve el bloque `imagen` de eventos.json (generada: true)."""
    carpeta_img = Path(carpeta_img)
    carpeta_img.mkdir(parents=True, exist_ok=True)
    motivos = elegir_motivos(ev)
    id_ = re.sub(r"[^a-z0-9]+", "-", norm(ev.get("id") or ev.get("nombre"))).strip("-")[:60] or "evento"
    ruta = carpeta_img / f"{id_}-ilustracion.svg"
    ruta.write_text(componer_svg(ev, motivos), encoding="utf-8")
    descr = ", ".join(motivos)
    return {"archivo": str(ruta.relative_to(ag.RAIZ)) if ag.RAIZ in ruta.parents else str(ruta), "generada": True, "motivos": motivos,
            "fuente": "Ilustración propia de Planes en Cádiz", "alt_text": f"Ilustración de «{ev.get('nombre', 'evento')}»: composición con {descr} en azul mar, blanco y amarillo"}


def catalogo(salida):
    import tempfile
    import render as rd
    tmp = Path(tempfile.mkdtemp())
    celdas = ""
    for k in M:
        f = tmp / f"{re.sub(r'[^a-z0-9]+', '-', norm(k))}.svg"
        f.write_text(componer_svg({"id": k, "nombre": k, "ilustracion": {"motivos": [k]}}), encoding="utf-8")
        celdas += f"<div style='position:relative;width:220px;height:220px'><img src='{f.as_uri()}' width=220 height=220><span style='position:absolute;left:6px;bottom:4px;font:700 15px sans-serif;color:#fff;text-shadow:0 0 3px #000'>{k}</span></div>"
    filas = (len(M) + 7) // 8
    (tmp / "c.html").write_text(f"<body style='margin:0;background:#888'><div style='display:grid;grid-template-columns:repeat(8,220px);gap:6px;padding:6px'>{celdas}</div></body>", encoding="utf-8")
    with rd.Renderer() as r:
        pg = r.browser.new_page(viewport={"width": 1800, "height": 232 * filas + 12})
        pg.goto((tmp / "c.html").as_uri()); pg.wait_for_timeout(600)
        pg.screenshot(path=str(salida))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nombre"); ap.add_argument("--categoria", default="otros"); ap.add_argument("--descripcion", default="")
    ap.add_argument("--catalogo", action="store_true")
    a = ap.parse_args()
    out = ag.RAIZ / "ejemplos" / "ilustraciones"; out.mkdir(parents=True, exist_ok=True)
    if a.catalogo:
        catalogo(out / "catalogo-motivos.png"); print("ok")
    elif a.nombre:
        ev = {"id": a.nombre, "nombre": a.nombre, "categoria": a.categoria, "descripcion": a.descripcion}
        print(generar(ev, out))
