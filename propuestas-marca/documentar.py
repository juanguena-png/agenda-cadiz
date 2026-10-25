#!/usr/bin/env python3
"""Genera los README de cada dirección, el README general y las hojas resumen. Ejecutar tras generar.py."""
import json
from pathlib import Path
from PIL import Image

AQUI = Path(__file__).parent
A = json.load(open(AQUI / "auditoria.json"))
bios = {
 1: "☀️ Qué hacer hoy en Cádiz, cada día a las 9:00\n🌊 Gratis · Finde · Lo mejor del mes\n👇 Comenta PLANES y te la mandamos",
 2: "🎉 Todos los planes de Cádiz, cada día a las 9:00\n🎭 Gratis, finde y fiesta\n💬 Comenta PLANES y te la enviamos",
 3: "La agenda de Cádiz, cada día a las 9:00.\nCultura, música, teatro, deporte y plan gratis.\nComenta PLANES y la recibes en tu bandeja.",
}
D = {
 1: dict(nombre="Mediterráneo luminoso", paleta=[("Cal (fondo)", "#FAF8F2"), ("Bruma marina (fondo 2)", "#EEF5F7"), ("Mar profundo (texto)", "#0A2E4D"), ("Mar (acento/enlaces)", "#0E6BA8"), ("Mar medio (datos)", "#0B5F95"), ("Mar de portada", "#0A5A94 → #083F6B"), ("Sol (relleno de acento)", "#FFC62B"), ("Texto secundario", "#3B566D"), ("Noche (story de tarde)", "#071D33")],
   fuentes="**Outfit** (títulos, 700) + **Inter** (texto, 400–800)",
   tono="Fresco, claro y cercano, como un amigo que te cuenta qué hay hoy. Frases cortas y luminosas, sin gritar. Una sola llamada a la acción por texto.",
   porque="En el feed compiten mil colores: el fondo claro con azul mar y amarillo sol se reconoce al instante y transmite «salgo a la calle». Es la opción más versátil: en otra ciudad basta cambiar el azul por su color sin perder el sistema. El contraste alto en cada diapositiva favorece guardar y reenviar, las señales que más empujan el alcance de una agenda.",
   logo="«PLANES EN» en versalitas azules + ciudad en Outfit Bold grande; sol amarillo y olas como decorado constante. Avatar: «P» blanca sobre mar con sol y olas."),
 2: dict(nombre="Carnaval y alegría", paleta=[("Violeta noche (fondo)", "#2A0B4F"), ("Violeta 2 (fondo)", "#3F1273"), ("Amarillo confeti", "#FFD83D"), ("Rosa chirigota", "#FF4F93"), ("Turquesa", "#25D9C7"), ("Naranja", "#FF8A1F"), ("Rosa claro (tarjeta)", "#FF8FB8"), ("Texto sobre color", "#2A0B4F")],
   fuentes="**Bagel Fat One** (títulos, único peso) + **Rubik** (texto, 300–900)",
   tono="Desenfadado, con guiño y energía, sin caricatura ni tópicos. Exclamaciones con mesura y emojis festivos (0–3). Invita a «liarla» con alguien: etiquetar y compartir.",
   porque="Es la más memorable y la que mejor se distingue en una cuadrícula de fotos: cada tarjeta de color es una pieza «parable» al hacer scroll, y encaja con la identidad festiva de la ciudad y con fiesta, música y familias. Riesgo: más densidad visual; por eso las tarjetas llevan texto oscuro sobre fondos claros y el decorado queda fuera de las zonas de texto.",
   logo="«PLANES EN» en Rubik Black amarillo + ciudad en Bagel Fat One blanca; círculos y serpentinas de decorado. Avatar: «P» redondeada blanca sobre rosa con confeti."),
 3: dict(nombre="Editorial moderno", paleta=[("Blanco (fondo)", "#FFFFFF"), ("Tinta (texto/filetes)", "#111111"), ("Gris texto secundario", "#4A4A4A"), ("Bermellón (acento)", "#B72D19"), ("Papel (ilustraciones)", "#F1EEE8"), ("Salmón (story de tarde)", "#FF7A5C")],
   fuentes="**Fraunces** (títulos, serif con cursiva) + **Inter** (texto)",
   tono="Sobrio, preciso y cultural, como el suplemento de un periódico. Frases completas y datos exactos, cero exageración. La confianza del dato sustituye a la exclamación.",
   porque="Posiciona la cuenta como medio de referencia: atrae a público cultural, prensa, instituciones y patrocinadores serios. Mucho blanco = lectura rapidísima. Es la que mejor escala a más ciudades e idiomas porque el sistema es tipográfico y el único color es un acento. Riesgo: menos «parada de scroll» que la 2; se compensa con el número gigante en rojo de cada portada.",
   logo="«PLANES EN» en Inter espaciada bermellón + ciudad en Fraunces cursiva grande. Avatar: «P» cursiva blanca sobre negro con punto bermellón."),
}
FUENTES = """| Tipografía | Autor | Licencia | Uso | Texto de licencia |
|---|---|---|---|---|
| Outfit | The Outfit Project Authors | SIL Open Font License 1.1 | D1 títulos | `plantilla/fuentes/OFL-outfit.txt` |
| Inter | The Inter Project Authors | SIL OFL 1.1 | D1 y D3 texto | `plantilla/fuentes/OFL-inter.txt` |
| Bagel Fat One | The Bagel Fat Project Authors | SIL OFL 1.1 | D2 títulos | `plantilla/fuentes/OFL-bagelfatone.txt` |
| Rubik | The Rubik Project Authors | SIL OFL 1.1 | D2 texto | `plantilla/fuentes/OFL-rubik.txt` |
| Fraunces | The Fraunces Project Authors | SIL OFL 1.1 | D3 títulos | `plantilla/fuentes/OFL-fraunces.txt` |

Todas de Google Fonts (repositorio `google/fonts`, carpeta `ofl/`). La OFL permite uso comercial, embebido en imágenes/vídeo y redistribución con su texto de licencia; solo prohíbe vender la fuente por sí sola."""
FB = """**Planes en Cádiz · Agenda diaria**

Todos los planes de Cádiz capital en un solo sitio. Cada día a las 9:00 publicamos qué hacer hoy: conciertos, teatro, exposiciones, deporte, actividades infantiles, gastronomía, fiestas y mucho plan gratis. Los jueves, los planes del finde; y el día 1 de cada mes, lo más destacado.

📍 Solo eventos celebrados en Cádiz capital, comprobados uno a uno en fuentes oficiales y en los propios recintos. Si un evento se cancela o cambia de hora, lo actualizamos.
🗓️ Agenda diaria a las 9:00 · «Esta noche en Cádiz» a las 19:00.
💬 Escribe «PLANES» en un comentario y te mandamos la agenda por mensaje.
📣 ¿Organizas algo en Cádiz? Cuéntanoslo por mensaje privado.

También en Instagram: @planesencadiz"""
mn = {t: min(i["ratio"] for k in A[t].values() for i in k) for t in A}

for n in (1, 2, 3):
    d, t = D[n], f"d{n}"
    pal = "\n".join(f"| {a} | `{b}` |" for a, b in d["paleta"])
    (AQUI / f"direccion-{n}" / "README.md").write_text(f"""# Dirección {n} · {d['nombre']}

![perfil](12-mosaico-perfil.png)

## Sistema
- **Logo modular:** pieza fija «Planes en» + ciudad variable (se reduce sola si el nombre es largo). {d['logo']}
- **Tipografías:** {d['fuentes']} (SIL OFL 1.1, uso comercial libre).
- **Tema en código:** `plantilla/temas/{t}.css` (variables + decorado), aplicado con `tema: "{t}"`.

## Paleta
| Uso | Hex |
|---|---|
{pal}

## Tono de voz (3 frases)
{d['tono']}

## Por qué funciona para crecer en Instagram
{d['porque']}

## Bio propuesta ({len(bios[n])}/150 caracteres)
```
{bios[n]}
```
Nombre: `Planes en Cádiz · Agenda diaria` · usuario `@planesencadiz`.

## Comprobaciones (automáticas, `auditoria.json`)
- **Contraste WCAG AA:** cada texto renderizado se mide contra su fondo real: **mínimo {mn[t]:.2f}:1** en todas las plantillas (AA exige 4,5:1).
- **Tamaños en la diapositiva de 6 eventos (lienzo 1080 px):** nombre 34 px, hora/lugar/precio 30 px, etiqueta de marca 26,6 px. Con 7+ eventos por diapositiva: nombre 31 px y datos 28 px (mínimos fijados). Las etiquetas de categoría (mayúsculas en negrita) usan 24 px.
- **Story:** todo el texto está en la zona segura (250 px libres arriba y abajo); el decorado queda fuera de ella o detrás.

## Piezas
`01-logo-modular` (Cádiz, Valladolid, Plans in Lisbon) · `01b-logo-nombres-extremos` · `02-foto-perfil-320` y `02b-…-prueba-circulo` · `03-portada-diaria` · `04-eventos-1/3/6` · `05-story-evento` · `06-story-esta-noche` · `07-sin-foto-música/infantil` · `08-destacada-hoy/finde/mes/gratis` · `09-portada-finde` · `10-portada-mensual` · `11-story-patrocinada` · `12-mosaico-perfil`. Ilustraciones de ejemplo (sin material de terceros) en `ilustraciones/`.
""", encoding="utf-8")

(AQUI / "README.md").write_text(f"""# Propuestas de identidad · Planes en Cádiz

Naming decidido: **Planes en Cádiz** · **@planesencadiz** · nombre del perfil **«Planes en Cádiz · Agenda diaria»**. Identidad **modular**: sistema fijo «Planes en» + ciudad variable (probado con *Planes en Valladolid*, *Plans in Lisbon*, *Planes en San Cristóbal de las Casas*, *Planes en Roma*). Nada procede de terceros ni usa símbolos oficiales: las imágenes son ilustraciones de ejemplo generadas aquí.

| | D1 · Mediterráneo luminoso | D2 · Carnaval y alegría | D3 · Editorial moderno |
|---|---|---|---|
| Sensación | limpio, fresco, de costa | festivo, memorable | sobrio, de referencia |
| Colores | cal · azul mar · amarillo sol | violeta · rosa · amarillo · turquesa | blanco · tinta · bermellón |
| Tipografías | Outfit + Inter | Bagel Fat One + Rubik | Fraunces + Inter |
| Contraste mínimo medido | {mn['d1']:.2f}:1 | {mn['d2']:.2f}:1 | {mn['d3']:.2f}:1 |
| Fortaleza | equilibrio y escalabilidad | destacar en la cuadrícula | credibilidad y patrocinio |
| Riesgo | menos distintiva | más recargada | menos «parada de scroll» |

Detalle (paleta, tono, razones, bio) en `direccion-N/README.md`.

## Tipografías y licencias
{FUENTES}

## Bio del perfil (máx. 150 caracteres)
1. D1 ({len(bios[1])}): `{bios[1]}`
2. D2 ({len(bios[2])}): `{bios[2]}`
3. D3 ({len(bios[3])}): `{bios[3]}`

## Texto de la página de Facebook («Acerca de»)
{FB}

*Descripción corta (≤ 255 caracteres):* «Agenda diaria de Cádiz capital: qué hacer hoy, esta noche y el finde. Todos los eventos comprobados, a las 9:00 y a las 19:00. Comenta PLANES y te la mandamos.»

## Regenerar
`python propuestas-marca/generar.py && python propuestas-marca/documentar.py`
""", encoding="utf-8")

for n in (1, 2, 3):
    d = AQUI / f"direccion-{n}"
    ims = []
    for f in ("03-portada-diaria.png", "04-eventos-6.png", "04-eventos-1.png", "05-story-evento.png", "06-story-esta-noche.png"):
        im = Image.open(d / f).convert("RGB"); ims.append(im.resize((int(im.width * 700 / im.height), 700)))
    S = Image.new("RGB", (sum(i.width for i in ims) + 48, 716), "#8A8A8A"); x = 8
    for i in ims:
        S.paste(i, (x, 8)); x += i.width + 8
    S.save(AQUI / f"resumen-direccion-{n}.png")
