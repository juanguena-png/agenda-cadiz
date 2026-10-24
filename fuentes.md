# Fuentes

Se scrapean todas en cada ejecución (`recopilar.py`, definidas en `fuentes.json`) y `registros/fuentes.log` guarda cuáles respondieron y cuáles fallaron. **Prohibido** hacer scraping de Instagram o Facebook. Prioridad para contrastar: oficiales > recintos > venta de entradas > prensa > agregadores. Ninguna fuente exime de la **comprobación de Cádiz capital** (CLAUDE.md, regla 1).

Estado de verificación comprobado el 2026-10-25 desde el entorno cloud (HTTP + contenido):

| # | Fuente | Tipo | URL de trabajo | Estado |
|---|---|---|---|---|
| 1 | Ayuntamiento de Cádiz – Programación cultural | oficial | http://laciudad.cadiz.es/programacion-teatros-de-cadiz.asp (índice de recintos municipales) · https://cadiz.es/ | ✅ responde. `www.cadiz.es/agenda` no existe; la programación vive en laciudad.cadiz.es |
| 2 | Turismo de Cádiz – Agenda | oficial | https://turismo.cadiz.es/ | ⚠️ web del Ayuntamiento responde; no se ha localizado URL estable de agenda (`/agenda` da 404). Ojo: **turismodecadiz.com es de la Diputación/Sierra de Grazalema, NO usar** |
| 3 | Onda Cádiz – Agenda | oficial | https://www.ondacadiz.es/ | ❌ responde 400 a clientes automáticos; probar con otra cabecera o descartar |
| 4 | Diputación de Cádiz – Agenda cultural | oficial (PROVINCIAL, filtrar) | https://www.dipucadiz.es/cultura/ | ✅ responde |
| 5 | Universidad de Cádiz – cultura/extensión | oficial (campus en varios municipios, filtrar) | https://www.uca.es/ | ⚠️ responde la portada; `cultura.uca.es` no resuelve; localizar agenda |
| 6 | Deportes Ayuntamiento | oficial | — | ❌ `deportes.cadiz.es` no resuelve; por localizar |
| 7 | Bibliotecas municipales / Provincial | oficial | — | ❌ por localizar (`cadiz.es/bibliotecas` da 404) |
| 8 | Gran Teatro Falla | recinto | http://laciudad.cadiz.es/programacion-gran-teatro-falla.asp | ✅ parser estructurado (fecha, hora, categoría, detalle). `teatrofalla.com` redirige a laciudad |
| 9 | Teatro del Títere La Tía Norica | recinto | http://laciudad.cadiz.es/programacion-teatro-del-titere.asp | ✅ responde (texto) |
| 10 | Sala Central Lechera | recinto | http://laciudad.cadiz.es/programacion-central-lechera.asp | ✅ parser estructurado |
| 11 | Baluarte de la Candelaria | recinto | http://laciudad.cadiz.es/programacion-baluarte-de-la-candelaria.asp | ✅ responde (texto) |
| 12 | Castillo de Santa Catalina | recinto | http://laciudad.cadiz.es/programacion-castillo-santa-catalina.asp | ✅ responde (texto). También: Noches Clásicas, Festival Patrimonio Flamenco, Festival del Títere, Teatro Pemán en el mismo índice |
| 13 | Museo de Cádiz | recinto | — | ❌ `museosdeandalucia.es` no resuelve desde el entorno; por localizar |
| 14 | Casa de Iberoamérica | recinto | https://www.casadeiberoamerica.es/ | ✅ responde |
| 15 | Palacio de Congresos de Cádiz | recinto | — | ❌ por localizar |
| 16 | Cádiz CF – partidos en casa | recinto | https://www.cadizcf.com/partidos | ✅ responde (solo partidos como local en el Nuevo Mirandilla) |
| 17 | VivaCádiz | agregador | https://www.vivacadiz.es/ → andaluciainformacion.es/cadiz | ⚠️ `/eventos` ya no existe (redirige a página 404); portada da 403 al bot |
| 18 | Hoy Cádiz | agregador | — | ❌ `hoycadiz.com` no resuelve; por localizar |
| 19 | Guía de Cádiz – Agenda | agregador (PROVINCIAL) | https://www.guiadecadiz.com/es/ | ⚠️ `/agenda` da 404; portada 403 al bot |
| 20 | Eventbrite – Cádiz | agregador (mezcla de fuera) | https://www.eventbrite.es/d/spain--c%C3%A1diz/events/ | ✅ responde con JSON-LD, pero **devuelve eventos online/extranjeros** (se vio en la prueba): filtrar siempre |
| 21 | En buena edad – agenda Ayuntamiento | agregador (solo contraste) | https://www.enbuenaedad.es/ | ❌ redirige a "inhabilitación temporal" de la Junta |
| 22-24 | Diario de Cádiz · La Voz de Cádiz · Cádiz Directo | prensa | https://www.diariodecadiz.es/ · https://www.lavozdigital.es/cadiz/ · https://www.cadizdirecto.com/ | ✅ responden (portadas; localizar secciones de agenda) |
| 25 | Ticketmaster · Entradium · Giglon | entradas | https://entradium.com/ | ✅ Entradium · ❌ Ticketmaster y Giglon (403 a bots) |

Las marcadas ❌/⚠️ se reintentan en cada ejecución; el agente puede buscar la URL correcta (WebSearch/WebFetch) y proponerla actualizando `fuentes.json`. Una fuente que falla varios días seguidos genera aviso por email.

## Lista de exclusión de imágenes
Imágenes que NO se pueden usar (el evento usa la genérica de su categoría). Formato: `AAAA-MM-DD · organizador/evento · motivo · quién lo pidió`.

_(vacía)_
