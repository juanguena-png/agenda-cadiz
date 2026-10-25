# Marca — Planes en Cádiz (DEFINITIVA · Dirección 1 «Mediterráneo luminoso»)

Fuente de verdad en código: `marca.json` (tema, prefijo, ciudad, usuario) + `plantilla/estilos.css` y `plantilla/temas/d1.css` (colores y tipografías). Las propuestas descartadas (D2, D3) quedan archivadas en `propuestas-marca/`. **No reinterpretar el diseño** (CLAUDE.md, regla 8).

## Naming
- Marca: **Planes en Cádiz** · usuario **@planesencadiz** (Instagram y página de Facebook).
- Campo «Nombre» del perfil: **Planes en Cádiz · Agenda diaria**.
- Sistema **modular**: pieza fija «Planes en» + ciudad variable (`marca.json`: `prefijo`, `ciudad`). Otras ciudades: «Planes en Sevilla», «Planes en Bogotá»; otros idiomas, traducido: «Plans in Lisbon». El nombre de la ciudad se reduce solo si es largo.

## Paleta (hex)
| Uso | Hex |
|---|---|
| Cal (fondo principal) | `#FAF8F2` |
| Bruma marina (fondo 2, degradado) | `#EEF5F7` |
| Mar profundo (texto principal, títulos) | `#0A2E4D` |
| Texto secundario | `#3B566D` |
| Mar (acento, chips, «PLANES EN») | `#0E6BA8` |
| Mar medio (horas y fechas sobre blanco) | `#0B5F95` |
| Portada: degradado mar (variante 0 de 7, ver «Portada con color rotatorio») | `#0A5A94` → `#083F6B` |
| Sol (relleno de acento; texto sobre él: `#0A2E4D`) | `#FFC62B` |
| Tarjeta | `#FFFFFF` (borde `#CFE0E8`, sombra `0 10px 28px rgba(10,46,77,.10)`) |
| Story de tarde (fondo noche) | `#071D33` → `#0A2E4D` (tarjeta `#0F3A5E`, texto `#FFFFFF`/`#D5E3EE`) |

**Contraste:** todo texto cumple WCAG AA (≥ 4,5:1); mínimo medido 4,60:1 (amarillo sobre mar de portada). Pares válidos: `#0A2E4D` sobre cal/blanco/sol; `#FFFFFF` sobre `#0E6BA8` y `#083F6B`; `#FFC62B` solo sobre `#083F6B`–`#0A5A94`/`#071D33`. **No** poner amarillo sobre blanco ni blanco sobre amarillo.

## Tipografías (SIL Open Font License 1.1, uso comercial libre; archivos y licencias en `plantilla/fuentes/`)
- Títulos y ciudad del logo: **Outfit** Bold (700).
- Texto, etiquetas y datos: **Inter** (400–800).
- Etiqueta «PLANES EN»: Inter ExtraBold, mayúsculas, interletraje +0,08 em, color `#0E6BA8` (sobre fondo oscuro, amarillo `#FFC62B`).

## Logo y avatar
- Logo = «PLANES EN» (pequeño, versalitas) sobre **Cádiz** (Outfit Bold grande); versión compacta en una línea para cabeceras (`logo mini`). Colores: ciudad en `#0A2E4D` (fondo claro), blanco (sobre mar) o `#FFC62B` (sobre `#0A2E4D`); sobre amarillo todo en `#0A2E4D`.
- Zona de respeto: ≥ la altura de la «P» alrededor. Tamaño mínimo de la versión compacta: 38 px en lienzos de 1080 px.
- **Foto de perfil** (320×320, círculo): «P» blanca sobre mar `#0E6BA8`, sol amarillo y líneas de ola. Archivo: `marca/foto-perfil-320.png`.
- **Destacadas** (portadas de historias destacadas, 1080×1920, icono + etiqueta dentro del círculo central): **Hoy, Finde, Este mes, Gratis** → `marca/destacada-*.png`.

## Formatos y reglas de diseño
| Formato | Tamaño | Notas |
|---|---|---|
| Carrusel / portada / agenda mensual (planes del finde: solo reel) | 1080×1350 | contenido clave en el 90 % central (la cuadrícula del perfil recorta a 3:4) |
| Stories, story de tarde, reel, destacadas | 1080×1920 | **250 px libres arriba y abajo** (solo decorado, nunca texto) |
| Imágenes genéricas «sin foto» | 1200×1200 | `plantilla/sin-foto/<categoría>.png`, una por categoría, color propio sobre mar con sol |

- **Tamaños de letra mínimos (lienzo 1080 px):** nombre de evento ≥ 31 px (34 px con ≤ 6 eventos por diapositiva), hora/lugar/precio ≥ 28 px (30 px con ≤ 6), etiqueta de marca ≥ 26 px, chips de categoría 24 px (mayúsculas en negrita). Nunca por debajo.
- **Densidad de eventos.** 1: imagen grande + todos los datos; 2: imagen + datos completos; 3–4: imagen cuadrada + categoría, hora, lugar y precio; 5–6: imagen + nombre y una línea (hora · lugar · precio); 7+: imagen pequeña + nombre y hora · lugar.
- **Decorado:** sol amarillo (esquina superior derecha) + líneas de ola (inferior). Fotografía de evento con esquinas redondeadas (30 px). Nada de símbolos oficiales (escudo de Cádiz, Ayuntamiento, Cádiz CF…) ni material de terceros.
- **Portada con color rotatorio** (para que el feed no se repita): 6 variantes que cambian **cada día** y usan **solo la paleta D1** (mar, noche, cal y sol). **El fondo celeste («bruma») queda descartado para siempre como fondo de portada**. Misma estructura en todas (logo, sol arriba a la derecha, olas abajo). Orden fijo en `render.py` (`ORDEN_PALETAS`), elegido por búsqueda para que ni el día siguiente ni la fila de arriba/abajo de la cuadrícula (3 columnas) compartan familia de color: **0 Mar** `#0A5A94→#083F6B` (sol amarillo) · **2 Cal** `#FAF8F2→#EEF5F7` (texto `#0A2E4D`, sol amarillo) · **1 Noche** `#0A2E4D→#071D33` (sol amarillo)  · **3 Sol** `#FFC62B→#F5B400` (texto `#0A2E4D`, sol cal) · **5 Mar con sol cal** (olas amarillas) · **6 Sol con sol azul** `#0E6BA8`. Contraste medido ≥ 4,6:1 en las 6 (`propuestas-marca/auditar_portadas.py`, hoja en `propuestas-marca/paletas-portada/`). No se añaden colores fuera de la paleta. Las diapositivas de eventos y stories mantienen siempre el fondo cal.
- **Portada:** logo grande arriba, etiqueta («Agenda diaria», «Viernes a domingo», «Agenda mensual»), título, fecha, nº de planes. Títulos: «Qué hacer hoy», «Planes del finde», «Lo más destacado de [mes]» (la ciudad la pone el logo; el alt_text dice «Planes en Cádiz»).
- **Story patrocinada:** misma línea gráfica y etiqueta «Publicidad» visible arriba (`story-patrocinio.html`).

## Reel (formato propio, `plantilla/reel.html`)
- **Portada propia**, distinta a todas las demás publicaciones para reconocer el reel de un vistazo en el feed: fondo intenso (noche, sol o mar), texto gigante apilado «PLANES / DEL / FINDE» con la última palabra resaltada, fotos de los eventos en **tarjetas inclinadas, arcos mediterráneos o burbujas** (3 composiciones que rotan por fecha, combinadas con 3 fondos), botón de sol-play y sello «N planes», chips de día (VIE 30 · SÁB 31 · DOM 1). Se exporta como `reel/portada.png` (1080×1920) y se usa de `cover_url`.
- **Márgenes de la portada** (para que no se recorte en el feed 4:5 ni en la cuadrícula 3:4): todo el contenido dentro de **x 70–1010 e y 300–1620**; solo los anillos decorativos y el fondo pueden salir. Comprobado con guías en `ejemplos/`.
- **Estructura única del vídeo:** intro = portada animada (3 s) → una escena por evento (4,2 s, tiempo de lectura cómodo: barras de progreso, pestañas de día, foto con zoom lento, categoría, título palabra a palabra, hora · lugar · precio con iconos) → cierre con «Guarda, comparte y elige tu plan · Comenta PLANES · @planesencadiz». Transición: el sol de la marca crece y cubre la pantalla. Todos los elementos animados (entradas escalonadas, olas en bucle, sol que respira, contador). 15–45 s: máx. 9 eventos (el resto queda solo en el carrusel).
- **Música:** pistas CC0 de `musica/` (ver `pistas.json`), normalizadas a ~-15 dB con fundido de entrada y salida; se descartan las pistas demasiado suaves.

## Ilustraciones propias (cuando no hay imagen oficial)
Composición de línea gruesa y redondeada con **un motivo principal relacionado con el evento** (guitarra, barco, máscaras, calabaza, balón, mapa…) + hasta 2 motivos pequeños, sol amarillo arriba a la derecha y olas abajo. Fondos de la paleta D1 según el evento (mar, bruma, noche, sol, cal). **Decisión: el fondo celeste «bruma» se mantiene SOLO en las ilustraciones** (variedad); nunca en portadas ni en el reel, trazo cal o noche y acento amarillo. Sin texto. Catálogo de motivos: `ejemplos/ilustraciones/catalogo-motivos.png`. Caption: «Ilustraciones: Planes en Cádiz». Imagen genérica de categoría solo como último recurso.

## Tono de voz
Fresco, claro y cercano, como un amigo que te cuenta qué hay hoy en la ciudad. Frases cortas y luminosas; una sola llamada a la acción por texto (guardar, compartir, etiquetar, comentar «PLANES»). Tuteo; emojis con mesura (0–3, preferentes: ☀️ 🌊 📍 🗓️ 👇).

**Sí**
- «Hoy en Cádiz hay 12 planes. Guarda el post y elige el tuyo 👇»
- «Concierto en el Falla a las 20:00. Entradas desde 12 €.»
- «¿Con quién irías? Etiquétalo.»

**No**
- Mayúsculas gritadas, «¡¡¡IMPERDIBLE!!!», clickbait, falsa urgencia.
- Chistes sobre acento o tópicos («ozú», «quillo» forzado).
- Copiar la nota de prensa del organizador.
- Prometer algo no confirmado por la fuente (precio, hora, invitados).

## Bio y página de Facebook
**Bio de Instagram (116/150):**
```
☀️ Qué hacer hoy en Cádiz, cada día a las 9:00
🌊 Gratis · Finde · Lo mejor del mes
👇 Comenta PLANES y te la mandamos
```
**Descripción corta de Facebook (≤255):** «Agenda diaria de Cádiz capital: qué hacer hoy, esta noche y el finde. Comenta PLANES y te la mandamos.»

**Acerca de (Facebook):**
> **Planes en Cádiz · Agenda diaria** — Todos los planes de Cádiz capital en un solo sitio. Cada día a las 9:00 publicamos qué hacer hoy: conciertos, teatro, exposiciones, deporte, actividades infantiles, gastronomía, fiestas y mucho plan gratis. Los jueves, los planes del finde; y el día 1 de cada mes, lo más destacado. 📍 Solo eventos celebrados en Cádiz capital, comprobados uno a uno en fuentes oficiales y en los propios recintos. Si un evento se cancela o cambia de hora, lo actualizamos. 🗓️ Agenda diaria a las 9:00 · «Esta noche en Cádiz» a las 18:30. 💬 Escribe «PLANES» en un comentario y te mandamos la agenda por mensaje. 📣 ¿Organizas algo en Cádiz? Cuéntanoslo por mensaje privado. También en Instagram: @planesencadiz

## Hashtags base (a ajustar con métricas)
#CádizCapital #QuéHacerEnCádiz #PlanesCádiz #AgendaCádiz #Cádiz #CulturaCádiz #CádizHoy

## Pruebas A/B
La identidad visual es única. Lo que se prueba es la **primera frase del caption**: variante A (pregunta/gancho) y B (dato directo), alternadas por día (`manifiesto.json` → `variante`), y se mide con `metricas.py --ab`.
