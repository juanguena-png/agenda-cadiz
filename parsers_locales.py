"""Parsers de organizadores locales y prensa (Unicaja Cádiz, Ateneo, IFEF/Depósitos de Tabaco y feeds RSS de prensa y Ayuntamiento).
Mismo contrato que parsers_extra.py: parser(fuente, ventana) -> (candidatos, fichas_con_error). El agente sigue verificando cada candidato (regla 1)."""
import re
import unicodedata
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from parsers_extra import MES_RE, MESES, _cand, _get, _pista, _texto

DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MES_NOMBRE = {v: k for k, v in MESES.items() if k != "setiembre"}
PALABRAS_EVENTO = re.compile(r"concierto|conferencia|presentaci[oó]n|exposici[oó]n|taller|charla|teatro|festival|jornadas|proyecci[oó]n|inauguraci[oó]n|recital|actuaci[oó]n|"
                             r"visita|ruta|mercadillo|feria|cine|espect[aá]culo|homenaje|curso|ciclo|tertulia|entradas?|gratuit|entrada libre|premios?|gala|desfile|carrera|"
                             r"torneo|partido|cuentacuentos|mesa redonda|coloquio|muestra|musical|danza|flamenco|libro|recogida|campa[ñn]a|solidari", re.I)


def _sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def fragmentos_dia(texto, dia, pub=None, ancho=230):
    """Trozos del texto que hablan de ese día: «27 de octubre», «martes 27», «27/10» y, si se conoce la fecha de publicación, «hoy», «esta noche» o «mañana»."""
    t = re.sub(r"\s+", " ", texto or "")
    nt = _sin_acentos(t)
    d, mes, wd = dia.day, MES_NOMBRE[dia.month], _sin_acentos(DIAS_ES[dia.weekday()])
    pats = [rf"\b0?{d}\s+de\s+{mes}\b", rf"\b{wd}\s+(?:dia\s+)?0?{d}\b", rf"\b0?{d}[/-]0?{dia.month}\b"]
    if pub == dia:
        pats += [r"\bhoy\b", r"\besta\s+(?:tarde|noche)\b", r"\beste\s+" + wd + r"\b"]
    if pub == dia - timedelta(days=1):
        pats += [r"\bmanana\b"]
    out, ult = [], -10**6
    for m in sorted((m for p in pats for m in re.finditer(p, nt)), key=lambda m: m.start()):
        if m.start() - ult < ancho:
            continue
        ult = m.start()
        out.append(t[max(0, m.start() - ancho // 2): m.end() + ancho].strip())
    return out


def _hora(frag):
    m = re.search(r"(?:a las|desde las|de|sobre las)\s+(\d{1,2})(?:[:.h](\d{2}))?\s*(?:h\b|horas)?", frag, re.I)
    if m and 0 <= int(m.group(1)) <= 24 and (m.group(2) or re.search(r"h\b|horas", m.group(0), re.I)):
        return f"{int(m.group(1)):02d}:{m.group(2) or '00'}"
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\s*h", frag)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None


# ----------------------------------------------------------------------------- RSS de prensa y organizadores
def parser_rss(fuente, ventana):
    """Feeds RSS (CádizNoticias, Cádiz Directo, Diario de Cádiz, Europa Sur, La Voz del Sur, notas de prensa del Ayuntamiento, Cádiz CF…).
    Devuelve, por cada día de la ventana, los artículos de los últimos 14 días que mencionan ese día y parecen un acto (candidato «pista de prensa»:
    el agente debe localizar la ficha oficial o confirmar con otro medio, criterio 17)."""
    out, errores = [], 0
    ini, fin = ventana
    for url in fuente["urls"]:
        try:
            s = BeautifulSoup(_get(url).text, "xml")
        except Exception:
            errores += 1
            continue
        for it in s.find_all("item"):
            try:
                pub = parsedate_to_datetime(it.find("pubDate").get_text()).date()
            except Exception:
                continue
            if pub < ini - timedelta(days=14) or pub > fin:
                continue
            titulo = it.find("title").get_text(" ", strip=True) if it.find("title") else ""
            link = it.find("link").get_text(strip=True) if it.find("link") else url
            cuerpo = " ".join(_texto(x.get_text()) for x in (it.find("content:encoded"), it.find("description")) if x)
            for i in range((fin - ini).days + 1):
                dia = ini + timedelta(days=i)
                frs = fragmentos_dia(titulo + ". " + cuerpo, dia, pub)
                frs = [f for f in frs if PALABRAS_EVENTO.search(f) or PALABRAS_EVENTO.search(titulo)]
                if not frs:
                    continue
                txt = " ".join(frs)
                out.append({"nombre": titulo, "fecha": dia.isoformat(), "fecha_inicio_evento": dia.isoformat(), "fecha_fin_evento": dia.isoformat(), "url": link,
                            "multidia": False, "permanente": False, "categoria_fuente": "noticia de prensa (pista)", "hora_inicio": _hora(txt), "pista_prensa": True,
                            "descripcion_fuente": txt[:500], "publicado": pub.isoformat(), "pista_capital": _pista(titulo, txt)})
    return out, errores


# ----------------------------------------------------------------------------- Fundación Unicaja (centro de Cádiz, agenda por día)
def parser_unicaja(fuente, ventana):
    """fundacionunicaja.com/agenda/?ciudad=cadiz&dia=AAAA-MM-DD: actos del Centro Fundación Unicaja Cádiz (Calle San Francisco 26, 11004 Cádiz)."""
    out, errores = [], 0
    ini, fin = ventana
    for i in range((fin - ini).days + 1):
        dia = ini + timedelta(days=i)
        try:
            s = BeautifulSoup(_get(f"https://www.fundacionunicaja.com/agenda/?ciudad=cadiz&dia={dia.isoformat()}&mes={dia.strftime('%Y-%m')}").text, "lxml")
        except Exception:
            errores += 1
            continue
        for li in s.select("li.fu-day__item"):
            a = li.select_one("a.fu-day__link")
            t = li.select_one(".fu-day__event-title")
            if not (a and t):
                continue
            hora_t = (li.select_one(".fu-day__time").get_text(" ", strip=True) if li.select_one(".fu-day__time") else "")
            sede = li.select_one(".fu-day__venue-texto").get_text(" ", strip=True) if li.select_one(".fu-day__venue-texto") else ""
            if "cádiz" not in sede.lower():
                continue
            hm = re.search(r"(\d{1,2})[:.](\d{2})", hora_t)
            nombre = t.get_text(" ", strip=True)
            expo = bool(re.match(r"exposici[oó]n|taller|aula|curso", nombre, re.I)) and not hm
            out.append({"nombre": nombre, "fecha": dia.isoformat(), "fecha_inicio_evento": dia.isoformat(), "fecha_fin_evento": dia.isoformat(), "url": a["href"],
                        "multidia": expo, "permanente": False, "categoria_fuente": "exposición larga (relleno)" if expo else "acto del Centro Fundación Unicaja",
                        "hora_inicio": f"{int(hm.group(1)):02d}:{hm.group(2)}" if hm else None, "horario_texto": hora_t or None,
                        "direccion": "Centro Fundación Unicaja Cádiz, Calle San Francisco 26, 11004 Cádiz", "lugar": "Centro Fundación Unicaja Cádiz",
                        "pista_capital": True})
    return out, errores


# ----------------------------------------------------------------------------- Ateneo de Cádiz (programa mensual)
def parser_ateneo(fuente, ventana):
    """ateneocadiz.es/<mes>-de-<año>/: «MARTES 27, 19:00h Presentación…» (sede: calle Ancha 20/1º, 11001 Cádiz, salvo que se indique otro lugar entre corchetes)."""
    out, errores, vistos = [], 0, set()
    ini, fin = ventana
    for i in range((fin - ini).days + 1):
        dia = ini + timedelta(days=i)
        clave = (dia.year, dia.month)
        if clave in vistos:
            continue
        vistos.add(clave)
        url = f"https://ateneocadiz.es/{MES_NOMBRE[dia.month]}-de-{dia.year}/"
        try:
            t = _texto(_get(url).text)
        except Exception:
            errores += 1
            continue
        for m in re.finditer(rf"(LUNES|MARTES|MI[EÉ]RCOLES|JUEVES|VIERNES|S[AÁ]BADO|DOMINGO)\s+(\d{{1,2}})\s*(?:\[([^\]]+)\])?\s*,\s*(?:Hora por determinar|(\d{{1,2}})[:.](\d{{2}})\s*h)(.*?)(?=(?:LUNES|MARTES|MI[EÉ]RCOLES|JUEVES|VIERNES|S[AÁ]BADO|DOMINGO)\s+\d{{1,2}}\s*(?:\[[^\]]+\])?\s*,|$)", t, re.S):
            try:
                d = date(dia.year, dia.month, int(m.group(2)))
            except ValueError:
                continue
            if not (ini <= d <= fin):
                continue
            resto = m.group(6).strip()
            lug_extra = m.group(3)
            nombre = re.split(r"(?<!\bDr)(?<!\bD)(?<!\bDª)(?<!\bSr)(?<!\bSra)(?<!\bExcmo)\.\s|\s+a cargo de\s+|\s+Presenta:|\s+Coordina:|\s+Preside:", resto)[0][:160].strip(" ,.-")
            hora = f"{int(m.group(4)):02d}:{m.group(5)}" if m.group(4) else None
            out.append({"nombre": nombre or "Acto del Ateneo", "fecha": d.isoformat(), "fecha_inicio_evento": d.isoformat(), "fecha_fin_evento": d.isoformat(), "url": url,
                        "multidia": False, "permanente": False, "categoria_fuente": "acto del Ateneo", "hora_inicio": hora,
                        "direccion": (lug_extra + " (Cádiz)") if lug_extra else "Ateneo de Cádiz, Calle Ancha 20, 1.º, 11001 Cádiz",
                        "lugar": lug_extra or "Ateneo de Cádiz", "descripcion_fuente": resto[:400], "pista_capital": True if not lug_extra else _pista(lug_extra, resto)})
    return out, errores


# ----------------------------------------------------------------------------- IFEF – Los Martes del Empleo (Depósitos de Tabaco)
def parser_ifef(fuente, ventana):
    """ifef.es: talleres «Los Martes del Empleo» (martes, 11:00-12:30, Depósitos de Tabaco, Av. Marconi 34, Cádiz; inscripción previa)."""
    try:
        t = _texto(_get("https://www.ifef.es/es/empleo/talleres-los-martes-del-empleo").text)
    except Exception:
        return [], 1
    out = []
    horario = re.search(r"talleres se celebrar[aá]n de (\d{1,2}[:.]\d{2}) a (\d{1,2}[:.]\d{2})", t)
    h0 = horario.group(1).replace(".", ":") if horario else None
    for m in re.finditer(rf"(\d{{1,2}}) de ({MES_RE}) de (\d{{4}}):\s*[\"“]([^\"”]+)[\"”]\s*:?(.*?)(?=\d{{1,2}} de (?:{MES_RE}) de \d{{4}}:|Programaci[oó]n de|$)", t, re.S | re.I):
        try:
            d = date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))
        except (ValueError, KeyError):
            continue
        if ventana[0] <= d <= ventana[1]:
            out.append({"nombre": f"Los Martes del Empleo: «{m.group(4).strip()}»", "fecha": d.isoformat(), "fecha_inicio_evento": d.isoformat(), "fecha_fin_evento": d.isoformat(),
                        "url": "https://www.ifef.es/es/empleo/talleres-los-martes-del-empleo", "multidia": False, "permanente": False, "categoria_fuente": "taller de empleo (inscripción previa)",
                        "hora_inicio": h0, "horario_texto": f"{h0} a {horario.group(2)}" if horario else None, "direccion": "Antiguos Depósitos de Tabaco, Avenida Marconi 34, Cádiz",
                        "lugar": "Antiguos Depósitos de Tabaco", "descripcion_fuente": re.sub(r"\s+", " ", m.group(5))[:300], "pista_capital": True})
    return out, 0


def fragmentos_ventana(texto, ventana, max_por_dia=6):
    """{fecha_iso: [fragmentos]} del texto de una página para cada día de la ventana (el agente lee solo estos trozos, no la página entera)."""
    ini, fin = ventana
    out = {}
    for i in range((fin - ini).days + 1):
        dia = ini + timedelta(days=i)
        fr = fragmentos_dia(texto, dia)[:max_por_dia]
        if fr:
            out[dia.isoformat()] = fr
    return out
