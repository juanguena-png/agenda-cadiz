"""Parsers adicionales de fuentes con contenido vivo (Onda Cádiz, Casa de Iberoamérica, Palacio de Congresos, La Ganzúa).
Cada parser devuelve (candidatos, fichas_con_error) con el mismo formato que los de recopilar.py."""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept-Language": "es-ES,es;q=0.9"}
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
MES_RE = "|".join(MESES)


def _get(url, **kw):
    r = requests.get(url, headers=UA, timeout=30, **kw)
    r.raise_for_status()
    r.encoding = r.apparent_encoding if not r.encoding or r.encoding.lower() == "iso-8859-1" else r.encoding
    return r


def _texto(html):
    return re.sub(r"\s+", " ", BeautifulSoup(html, "lxml").get_text(" ")).strip()


def _pista(*t):
    import recopilar
    return recopilar.pista_capital(*t)


def _cand(nombre, f0, f1, ventana, url, **extra):
    """Un candidato por cada día de la ventana comprendido entre f0 y f1."""
    ini, fin = ventana
    out = []
    for i in range((fin - ini).days + 1):
        dia = ini + timedelta(days=i)
        if f0 <= dia <= f1:
            out.append({"nombre": nombre, "fecha": dia.isoformat(), "fecha_inicio_evento": f0.isoformat(), "fecha_fin_evento": f1.isoformat(),
                        "url": url, "multidia": f0 != f1, "permanente": (f1 - f0).days > 180, **extra})
    return out


# ----------------------------------------------------------------------------- Onda Cádiz (agenda municipal con fichas)
def parser_onda(fuente, ventana):
    """ondacadiz.es/agenda-de-eventos: «actuales» y «próximos». Cada ficha trae fecha, hora y dirección (incluye lo que el Ayuntamiento anuncia en notas de prensa)."""
    errores, items = 0, {}
    for u in ("https://ondacadiz.es/agenda-de-eventos", "https://ondacadiz.es/agenda-de-eventos/proximos"):
        try:
            s = BeautifulSoup(_get(u).text, "lxml")
        except Exception:
            errores += 1
            continue
        for a in s.select("article.eventos"):
            h = a.select_one("h2 a")
            fechas = [datetime.fromisoformat(t["datetime"].replace("Z", "")).date() for t in a.select("time[datetime]")]
            if not (h and fechas):
                continue
            f0, f1 = min(fechas), max(fechas)
            if f1 < ventana[0] or f0 > ventana[1]:
                continue
            cat = a.select_one(".field--name-field-evento-categoria")
            items[urljoin(u, h["href"])] = (h.get_text(" ", strip=True), f0, f1, cat.get_text(" ", strip=True) if cat else None)

    def ficha(url):
        try:
            r = _get(url)
            sp = BeautifulSoup(r.text, "lxml")
            campo = lambda n: next((re.sub(r"\s+", " ", f.get_text(" ", strip=True)) for f in sp.select(f".field--name-{n}")), None)
            hora_t = campo("field-evento-hora")
            dir_t = campo("field-evento-direccion")
            hm = re.search(r"(\d{1,2})[:.](\d{2})", hora_t or "")
            og = re.search(r'property="og:image"[^>]*content="([^"]+)"', r.text)
            return {"hora": f"{int(hm.group(1)):02d}:{hm.group(2)}" if hm else None, "dir": re.sub(r"^Direcci[oó]n\s*", "", dir_t or "") or None,
                    "desc": (campo("body") or "")[:400] or None, "img": og.group(1) if og else None, "horario": re.sub(r"^Hora\s*", "", hora_t or "") or None}
        except Exception:
            return None

    out = []
    with ThreadPoolExecutor(6) as ex:
        for (url, (nombre, f0, f1, cat)), d in zip(items.items(), ex.map(ficha, items)):
            if not d:
                errores += 1
                continue
            out += _cand(nombre.strip().capitalize() if nombre.islower() else nombre, f0, f1, ventana, url, categoria_fuente=cat, hora_inicio=d["hora"],
                         horario_texto=d["horario"], direccion=d["dir"], lugar=(d["dir"] or "").split("(")[0].strip() or None, descripcion_fuente=d["desc"],
                         pista_capital=_pista(d["dir"]), imagen_url_oficial=d["img"])
    return out, errores


# ----------------------------------------------------------------------------- Casa de Iberoamérica (agenda propia)
def _rango_es(txt, anio_defecto=None):
    """«23 septiembre 2026 -30 octubre 2026» → (f0, f1) o None."""
    m = re.findall(rf"(\d{{1,2}})\s+({MES_RE})\s+(\d{{4}})", txt.lower())
    try:
        ds = [date(int(y), MESES[mes], int(d)) for d, mes, y in m]
    except ValueError:
        return None
    return (min(ds), max(ds)) if ds else None


def parser_casaibero(fuente, ventana):
    """casadeiberoamerica.es/agenda: exposiciones y actividades con rango de fechas y horario general del recinto (Calle Concepción Arenal s/n, 11006 Cádiz)."""
    s = BeautifulSoup(_get("https://www.casadeiberoamerica.es/agenda").text, "lxml")
    out, vistos = [], set()
    for ev in s.select(".event"):
        a = ev.select_one("h3 a")
        ps = [p.get_text(" ", strip=True) for p in ev.select("p")]
        if not (a and ps) or a["href"] in vistos:
            continue
        vistos.add(a["href"])
        cabecera = ps[0]
        rango = _rango_es(cabecera.split("//")[0], ventana[0].year)
        if not rango:
            continue
        horario = cabecera.split("//", 1)[1].strip() if "//" in cabecera else None
        lugar = next((p.split(":", 1)[1].strip() for p in ps if p.lower().startswith("lugar")), None)
        out += _cand(a.get_text(" ", strip=True), rango[0], rango[1], ventana, a["href"], hora_inicio=None, horario_texto=horario,
                     direccion="Casa de Iberoamérica, Calle Concepción Arenal s/n, 11006 Cádiz", lugar=f"Casa de Iberoamérica · {lugar}" if lugar else "Casa de Iberoamérica",
                     descripcion_fuente=" ".join(ps[1:3])[:300], pista_capital=True)
    return out, 0


# ----------------------------------------------------------------------------- Palacio de Congresos de Cádiz
def parser_palacio(fuente, ventana):
    """palaciocongresos-cadiz.com/eventos: congresos, jornadas y otros actos (la mayoría profesionales: el agente aplica los criterios de filtrado)."""
    s = BeautifulSoup(_get("https://palaciocongresos-cadiz.com/eventos/").text, "lxml")
    out = []
    for c in s.select(".befresh-evento-card"):
        t, f, cat = c.select_one(".befresh-evento-card__title"), c.select_one(".befresh-evento-card__fecha"), c.select_one(".befresh-evento-card__cat")
        if not (t and f):
            continue
        txt = f.get_text(" ", strip=True).lower().replace("–", "-")
        m = re.match(rf"(\d{{1,2}})(?:\s+de\s+({MES_RE}))?\s*-\s*(\d{{1,2}})\s+de\s+({MES_RE})\s+de\s+(\d{{4}})", txt)
        try:
            if m:
                mes2 = MESES[m.group(4)]
                mes1 = MESES[m.group(2)] if m.group(2) else mes2
                f0, f1 = date(int(m.group(5)), mes1, int(m.group(1))), date(int(m.group(5)), mes2, int(m.group(3)))
            else:
                m = re.match(rf"(\d{{1,2}})\s+de\s+({MES_RE})\s+de\s+(\d{{4}})", txt)
                f0 = f1 = date(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
        except (AttributeError, ValueError, KeyError):
            continue
        a = c.select_one("a[href]")
        out += _cand(t.get_text(" ", strip=True), f0, f1, ventana, a["href"] if a else "https://palaciocongresos-cadiz.com/eventos/",
                     categoria_fuente=cat.get_text(" ", strip=True) if cat else None, lugar="Palacio de Congresos y Exposiciones de Cádiz",
                     direccion="Palacio de Congresos de Cádiz", pista_capital=True, descripcion_fuente="Acto en el Palacio de Congresos de Cádiz (suele ser profesional o con inscripción: revisar criterios de filtrado).")
    return out, 0


# ----------------------------------------------------------------------------- La Ganzúa (conciertos por ciudad)
def _artista(txt):
    """Quita el texto de cabecera que el regex arrastra («… Es gratis. Artista»)."""
    txt = re.split(r"Próximos Conciertos|Es gratis\.|Aviso:|entradas\.", txt)[-1]
    return txt.strip(" .|")


def parser_ganzua(fuente, ventana):
    """laganzua.net/conciertos/cadiz: «Artista D de mes de AAAA - Sala, Ciudad precio». Solo se conserva ciudad == Cádiz (la provincia se descarta)."""
    ini, fin = ventana
    urls = {"https://www.laganzua.net/conciertos/cadiz", "https://www.laganzua.net/conciertos/cadiz/2026", "https://www.laganzua.net/conciertos/cadiz/2027"}
    d = ini.replace(day=1)
    while d <= fin:
        urls.add(f"https://www.laganzua.net/conciertos/cadiz/{list(MESES)[d.month - 1]}-{d.year}")
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    rx = re.compile(rf"(?P<art>[^\d|]{{2,90}}?)\s+(?P<d>\d{{1,2}}) de (?P<m>{MES_RE}) de (?P<y>\d{{4}}) - (?P<sala>[^,]+?), (?P<ciudad>[^\d,]+?)(?:\s+(?P<precio>\d+(?:[.,]\d+)?))?(?=\s+[A-ZÁÉÍÓÚÑ0-9]|\s*$)")
    rx2 = re.compile(rf"(?P<art>[^|]{{2,80}}?) en (?P<c0>[^,|]+), Cádiz \|[^|]*?(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo) (?P<d>\d{{1,2}}) de (?P<m>{MES_RE}) de (?P<y>\d{{4}}) (?P<ciudad>[^,]+?) , Cádiz (?P<sala>.+?) ver entradas", re.I)
    out, errores, vistos = [], 0, set()
    for u in sorted(urls):
        try:
            t = _texto(_get(u).text)
        except Exception:
            continue  # meses sin página (404): no es un error
        t = t.split("CONCIERTOS EN CÁDIZ", 1)[-1]
        for m in rx2.finditer(t):  # páginas por mes: «Artista en Ciudad, Cádiz | géneros día 22 de noviembre de 2026 Ciudad , Cádiz Sala ver entradas»
            try:
                f = date(int(m["y"]), MESES[m["m"]], int(m["d"]))
            except ValueError:
                continue
            art = _artista(m["art"])
            k = (art, f)
            if ini <= f <= fin and k not in vistos and m["ciudad"].strip().lower() == "cádiz":
                vistos.add(k)
                out.append({"nombre": f"Concierto: {art}", "fecha": f.isoformat(), "lugar": m["sala"].strip().title(), "direccion": f"{m['sala'].strip().title()}, Cádiz", "url": u, "multidia": False,
                            "permanente": False, "categoria_fuente": "música", "pista_capital": True,
                            "descripcion_fuente": "Concierto anunciado en La Ganzúa (agregador): confirmar hora y recinto en la web de la sala o el promotor."})
        for m in rx.finditer(t):
            try:
                f = date(int(m["y"]), MESES[m["m"]], int(m["d"]))
            except ValueError:
                continue
            art = _artista(m["art"])
            k = (art, f)
            if not (ini <= f <= fin) or k in vistos or m["ciudad"].strip().lower() != "cádiz":
                continue
            vistos.add(k)
            out.append({"nombre": f"Concierto: {art}", "fecha": f.isoformat(), "lugar": m["sala"].strip(), "direccion": f"{m['sala'].strip()}, Cádiz", "precio_texto": (m["precio"] + " €") if m["precio"] else None,
                        "url": u, "multidia": False, "permanente": False, "categoria_fuente": "música", "pista_capital": True,
                        "descripcion_fuente": "Concierto anunciado en La Ganzúa (agregador): confirmar hora y recinto en la web de la sala o el promotor."})
    return out, errores


# ----------------------------------------------------------------------------- Fundación Cajasol (agenda en JavaScript: se lee con Chromium)
MES_ABR = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
_ABR = "|".join(MES_ABR)


def parser_cajasol(fuente, ventana):
    """fundacioncajasol.com/eventos: filas «FECHA(S) LUGAR TIPO TÍTULO». Solo sede de CÁDIZ (Casa Pemán, Plaza de San Antonio 14)."""
    import render as rd
    ini, fin = ventana
    with rd.Renderer() as r:
        ctx = r.browser.new_context(user_agent=UA["User-Agent"], locale="es-ES")
        pg = ctx.new_page()
        pg.goto("https://fundacioncajasol.com/eventos/", wait_until="networkidle", timeout=45000)
        texto = re.sub(r"\s+", " ", pg.inner_text("body"))
        enlaces = []
        for h in pg.evaluate("Array.from(document.querySelectorAll(\"a[href*='/evento/']\")).map(a=>a.href)"):
            if h not in enlaces:
                enlaces.append(h)
    texto = texto.split("FECHA LUGAR TITULO", 1)[-1]
    filas = re.split(rf"(?=\b\d{{1,2}} (?:{_ABR}) (?:\d{{1,2}} (?:{_ABR})|\d{{1,2}}:\d{{2}})\b)", texto)
    filas = [f.strip() for f in filas if re.match(rf"\d{{1,2}} (?:{_ABR}) ", f.strip())]
    rx = re.compile(rf"(?P<d0>\d{{1,2}}) (?P<m0>{_ABR}) (?:(?P<d1>\d{{1,2}}) (?P<m1>{_ABR})|(?P<h>\d{{1,2}}:\d{{2}})) (?P<ciudad>SEVILLA|CÁDIZ|CÓRDOBA|HUELVA|MÁLAGA|GRANADA|JAÉN|ALMERÍA|JEREZ|MADRID|BADAJOZ|CEUTA|MELILLA) (?P<tipo>EXPOSICIÓN|TALLER|CONCIERTO|CONFERENCIA|PROYECCIÓN CINEMATOGRÁFICA|JORNADAS|PRESENTACIÓN|ESPECTÁCULO|VISITA|CICLO|MESA REDONDA|CURSO|ACTUACIÓN|TEATRO|ENCUENTRO|[A-ZÁÉÍÓÚÑ]+) (?P<titulo>.+)$")
    out, hoy = [], ini
    for i, f in enumerate(filas):
        m = rx.match(f)
        if not m or m["ciudad"] != "CÁDIZ":
            continue
        anio = ini.year
        try:
            f0 = date(anio, MES_ABR[m["m0"]], int(m["d0"]))
            f1 = date(anio, MES_ABR[m["m1"]], int(m["d1"])) if m["d1"] else f0
        except ValueError:
            continue
        if f0 < ini - timedelta(days=200):
            f0 = f0.replace(year=anio + 1)
        if f1 < f0:
            f1 = f1.replace(year=f0.year + 1)
        url = enlaces[i] if len(enlaces) == len(filas) else "https://fundacioncajasol.com/eventos/"
        out += _cand(m["titulo"].strip().capitalize(), f0, f1, (ini, fin), url, hora_inicio=m["h"], categoria_fuente=m["tipo"].lower(), lugar="Fundación Cajasol (Casa Pemán)",
                     direccion="Fundación Cajasol, Plaza de San Antonio, 14, 11003 Cádiz", pista_capital=True,
                     descripcion_fuente=f"{m['tipo'].capitalize()} en la sede de Cádiz de la Fundación Cajasol.")
    return out, 0
