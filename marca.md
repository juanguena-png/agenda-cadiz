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
| Portada: degradado mar | `#0A5A94` → `#083F6B` |
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
| Carrusel / portada / planes del finde / agenda mensual | 1080×1350 | contenido clave en el 90 % central (la cuadrícula del perfil recorta a 3:4) |
| Stories, story de tarde, reel, destacadas | 1080×1920 | **250 px libres arriba y abajo** (solo decorado, nunca texto) |
| Imágenes genéricas «sin foto» | 1200×1200 | `plantilla/sin-foto/<categoría>.png`, una por categoría, color propio sobre mar con sol |

- **Tamaños de letra mínimos (lienzo 1080 px):** nombre de evento ≥ 31 px (34 px con ≤ 6 eventos por diapositiva), hora/lugar/precio ≥ 28 px (30 px con ≤ 6), etiqueta de marca ≥ 26 px, chips de categoría 24 px (mayúsculas en negrita). Nunca por debajo.
- **Densidad de eventos.** 1: imagen grande + todos los datos; 2: imagen + datos completos; 3–4: imagen cuadrada + categoría, hora, lugar y precio; 5–6: imagen + nombre y una línea (hora · lugar · precio); 7+: imagen pequeña + nombre y hora · lugar.
- **Decorado:** sol amarillo (esquina superior derecha) + líneas de ola (inferior). Fotografía de evento con esquinas redondeadas (30 px). Nada de símbolos oficiales (escudo de Cádiz, Ayuntamiento, Cádiz CF…) ni material de terceros.
- **Portada:** logo grande arriba, etiqueta («Agenda diaria», «Viernes a domingo», «Agenda mensual»), título, fecha, nº de planes. Títulos: «Qué hacer hoy», «Planes del finde», «Lo más destacado de [mes]» (la ciudad la pone el logo; el alt_text dice «Planes en Cádiz»).
- **Story patrocinada:** misma línea gráfica y etiqueta «Publicidad» visible arriba (`story-patrocinio.html`).

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
**Descripción corta de Facebook (≤255):** «Agenda diaria de Cádiz capital: qué hacer hoy, esta noche y el finde. Todos los eventos comprobados, a las 9:00 y a las 19:00. Comenta PLANES y te la mandamos.»

**Acerca de (Facebook):**
> **Planes en Cádiz · Agenda diaria** — Todos los planes de Cádiz capital en un solo sitio. Cada día a las 9:00 publicamos qué hacer hoy: conciertos, teatro, exposiciones, deporte, actividades infantiles, gastronomía, fiestas y mucho plan gratis. Los jueves, los planes del finde; y el día 1 de cada mes, lo más destacado. 📍 Solo eventos celebrados en Cádiz capital, comprobados uno a uno en fuentes oficiales y en los propios recintos. Si un evento se cancela o cambia de hora, lo actualizamos. 🗓️ Agenda diaria a las 9:00 · «Esta noche en Cádiz» a las 19:00. 💬 Escribe «PLANES» en un comentario y te mandamos la agenda por mensaje. 📣 ¿Organizas algo en Cádiz? Cuéntanoslo por mensaje privado. También en Instagram: @planesencadiz

## Hashtags base (a ajustar con métricas)
#CádizCapital #QuéHacerEnCádiz #PlanesCádiz #AgendaCádiz #Cádiz #CulturaCádiz #CádizHoy

## Pruebas A/B
La identidad visual es única. Lo que se prueba es la **primera frase del caption**: variante A (pregunta/gancho) y B (dato directo), alternadas por día (`manifiesto.json` → `variante`), y se mide con `metricas.py --ab`.
