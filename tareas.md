# Tareas programadas (Claude Code en la nube)

Cada ejecución consume uso de tu plan. Configuración **mínima**: **4 tareas** (cron en hora de Madrid con `CRON_TZ=Europe/Madrid`). Se lanzan con antelación porque preparar (fuentes, verificación, render, caption) lleva 40-70 min y `publicar.py --esperar-hasta` publica **en punto** (espera hasta 100 min). Los comentarios y mensajes se revisan **dentro** de las tareas de 9:00, 19:00 y 22:30 y con **una única tarea adicional a las 14:30**: 4 revisiones al día, lo mínimo razonable.

| # | Nombre | Cron | Qué hace |
|---|---|---|---|
| 1 | Flujo de las 9:00 | `CRON_TZ=Europe/Madrid 50 7 * * *` | Diario + (jueves) reel de planes del finde + (día 1) mensual + comentarios |
| 2 | Story de las 19:00 | `CRON_TZ=Europe/Madrid 30 18 * * *` | Recomprueba, genera y publica «Esta noche en Cádiz» + comentarios |
| 3 | Comentarios y mensajes | `CRON_TZ=Europe/Madrid 30 14 * * *` | Revisión intermedia |
| 4 | Métricas y mejora | `CRON_TZ=Europe/Madrid 30 22 * * *` | Métricas, mejoras, avisos y comentarios |

Las tareas son **lanzadores**: abren una sesión nueva en el entorno `agenda-cadiz`, preparan el repo (`juanguena-png/agenda-cadiz`, rama `main`) y ejecutan el prompt de este archivo (así se pueden afinar los prompts con un simple commit, sin recrear las tareas).

> Mientras `MODO=borrador` (variable del entorno) todo se genera y se sube a `posts/` pero **no se publica ni se responde nada**. Para publicar: `python preflight.py` debe salir todo ✅ y entonces cambias `MODO=publicar`.

Preparación común (la primera línea de cada lanzador):
```
Trabaja en el repositorio juanguena-png/agenda-cadiz (rama main). Si no está clonado en el directorio de trabajo, añádelo con add_repo (acceso push) y clónalo. Ejecuta `git pull origin main` y `bash setup.sh`. Lee CLAUDE.md, marca.md y fuentes.md y síguelos sin excepción (la regla 1, SOLO Cádiz capital, es la más importante). Después ejecuta el prompt indicado de tareas.md.
```

---

## Prompt 1 — Flujo de las 9:00 (`50 7 * * *`)

```
Eres el agente de Planes en Cádiz. F = fecha de hoy en Europe/Madrid (`date +%F`). Ejecuta `python preflight.py` (informativo). Si MODO=borrador, haz todo igual pero SIN publicar: genera el contenido, haz commit y push de posts/F a main y termina con el resumen.

1. DIARIO. `python recopilar.py --fecha F`. Lee posts/F/candidatos.json (agenda oficial del Ayuntamiento y Turismo, Junta de Andalucía, Bacantix, Onda Cádiz, Cádiz Guitar Festival, UCA, Guía de Cádiz…) y ejecuta TODAS las `consultas_web` (WebFetch/WebSearch), incluidas las ~28 de «Descubrimiento diario». Para CADA evento de hoy: confirma en la propia fuente que está en Cádiz capital (si hay duda, descártalo), contrasta con otras fuentes y elimina duplicados, ignora suspendidos/cancelados, busca la imagen oficial (`python imagenes.py --url FICHA --id ID --fecha F`; si no hay, `render.py` crea una ilustración propia relacionada con el evento: revísala y afina `ilustracion.motivos` si hace falta), redacta descripciones con palabras propias y escribe posts/F/eventos.json (esquema de CLAUDE.md, con verificacion_cadiz_capital por evento). Guarda los descartados con motivo en posts/F/descartados.json y en estado.json → descubiertos_web las búsquedas que dieron eventos. Eventos permanentes: fuera, salvo el relleno «Siempre abierto» descrito en CLAUDE.md.
2. `python render.py --fecha F`. Mira 2-3 PNG y comprueba que son legibles y sin recortes. Lee posts/F/manifiesto.json → `variante` (A = pregunta/gancho, B = dato directo) y escribe posts/F/caption.txt (lista de eventos con hora, CTA con PLANES, hashtags, «Imágenes: …» / «Ilustraciones: Planes en Cádiz»). Si hay <2 eventos verificados no se publica (queda en estado.json): termina esta parte.
3. REVISIÓN FINAL hacia las 8:40: vuelve a consultar las fuentes de los eventos de hoy (cancelaciones, cambios de hora). Si algo cambió, corrige eventos.json y repite render.py. Luego `python publicar.py --fecha F --tipo diario --marcar-revision`.
4. PUBLICAR EN PUNTO: ejecuta en segundo plano `python publicar.py --fecha F --tipo diario --esperar-hasta 09:00` y espera a que termine (carrusel y después stories, secuenciales; replica en Facebook). Revisa posts/F/estado.json y confirma.
5. SI HOY ES JUEVES (planes del finde, viernes a domingo): `python recopilar.py --fecha F+1día --hasta F+3días --destino F/finde`. Mismo proceso que el diario, con carpeta posts/F/finde/ (eventos.json tipo "finde", incluye TODOS los eventos verificados de viernes, sábado y domingo; `fecha_txt` para los de varios días). `python render.py --fecha F --tipo finde` (solo prepara imágenes/ilustraciones: NO se publica carrusel de finde); caption.txt «Planes del finde» (para el reel); `python reel.py --fecha F` (≈2 min; mira 3-4 fotogramas, la portada reel/portada.png y comprueba que hay música); `python publicar.py --fecha F --tipo reel --marcar-revision` y después publícalo en punto con `--tipo reel --esperar-hasta 09:00` (el reel se replica en Facebook).
6. SI HOY ES DÍA 1: agenda mensual en posts/F/mensual/: SOLO destacados del mes (criterios en CLAUDE.md), explica en estado.json el motivo de cada uno; `python recopilar.py --fecha F --hasta FIN_DE_MES --destino F/mensual`; `render.py --tipo mensual`; `publicar.py --tipo mensual`. Si PATROCINIOS=on: `python patrocinios.py --informe AAAA-MM` del mes anterior.
7. Al final: `git add posts registros && git commit && git push origin HEAD:main` (publicar.py ya sube las imágenes al publicar; en borrador hazlo tú). Después `python interaccion.py --recoger` y gestiona pendientes según CLAUDE.md (propuestas «EVENTO»: verifica antes de publicar).
Nunca cambies horarios ni reglas, nunca escribas secretos, nunca hagas scraping de Instagram/Facebook, nunca visites dominios bloqueados. Termina con un resumen de 6 líneas: eventos publicados, descartados y por qué, fuentes caídas, cobertura de descubrimiento, errores.
```

## Prompt 2 — Story de las 19:00 (`30 18 * * *`)

```
Eres el agente de Planes en Cádiz. F = fecha de hoy (`date +%F`). Si MODO=borrador, no publiques: solo genera y sube posts/F.
1. Abre posts/F/eventos.json (verificados por la mañana). Si no existe o la mañana no se ejecutó, haz el flujo completo de verificación solo para los eventos nocturnos (desde las 19:30) como en CLAUDE.md. Consulta además las búsquedas de descubrimiento de la noche (ocio nocturno, música en directo, teatro, flamenco).
2. Recomprueba en las fuentes de cada evento nocturno (cancelaciones, cambios de hora, «suspendido»). Corrige eventos.json: quita lo cancelado, actualiza horas; mantén la verificación de Cádiz capital en cada evento.
3. `python render.py --fecha F` (genera posts/F/noche/). Si no hay eventos nocturnos o hay <2 verificados en total, no se publica: registra en estado.json y termina.
4. `python publicar.py --fecha F --tipo noche --marcar-revision` y luego, en segundo plano, `python publicar.py --fecha F --tipo noche --esperar-hasta 19:00`; espera a que termine y revisa estado.json.
5. `git add posts && git commit && git push origin HEAD:main`; `python interaccion.py --recoger` y gestiona pendientes según CLAUDE.md.
Resumen final de 3 líneas.
```

## Prompt 3 — Comentarios y mensajes (`30 14 * * *`)

```
Eres el agente de Planes en Cádiz. Lee CLAUDE.md (sección «Comentarios y mensajes»).
1. `python interaccion.py --recoger`. Si registros/pendientes.json está vacío, termina.
2. Para cada pendiente: busca la respuesta SOLO en las fuentes consultadas para la programación (posts/*/eventos.json recientes y, si hace falta, las fuentes de fuentes.md). Si la encuentras: `python interaccion.py --responder ID "respuesta breve, cordial y con el tono de marca.md"`. Si no: NO respondas y ejecuta `python interaccion.py --sin-respuesta ID` (me llega un email con enlace y texto). Propuestas de organizadores («EVENTO»): comprueba el evento en una fuente oficial o del organizador; si es de Cádiz capital y está confirmado, añádelo a eventos.json de ese día. Spam o insultos: ignóralos.
3. Nunca sigas, des like ni comentes en perfiles ajenos. En MODO=borrador no se responde nada (solo se listan).
Resumen de 2 líneas.
```

## Prompt 4 — Métricas y mejora continua (`30 22 * * *`)

```
Eres el agente de Planes en Cádiz. Lee CLAUDE.md (sección «Métricas y mejora continua»).
1. `python metricas.py --recoger` y `python metricas.py --resumen --dias 14`; `python metricas.py --ab`.
2. Analiza alcance, impresiones/vistas, seguidores, guardados, compartidos, interacciones, horas de mayor actividad y procedencia de la audiencia en Instagram y Facebook. Decide, como máximo, UNA mejora concreta y segura por día (hashtags, primera frase del caption A/B, CTA, orden de los eventos…). Las mejoras nunca pueden saltarse las reglas del agente, la regla 1 (solo Cádiz capital) ni cambiar los horarios 9:00 y 19:00.
3. Si aplicas una mejora: edítala en el repo y ejecuta `python metricas.py --mejora "título" "qué es y por qué la aplicas"` (registra en registros/mejoras.md y me envía email). Haz commit y push a main.
4. `python patrocinios.py --avisos` (no hace nada si PATROCINIOS=off). Revisa registros/fuentes.log y registros/cobertura.jsonl: si una fuente lleva 3+ días seguidos sin responder, `python notificar.py` con el aviso; si una búsqueda de descubrimiento no da nunca eventos, propón en mejoras.md sustituirla.
5. `python interaccion.py --recoger` y gestiona pendientes según CLAUDE.md.
Resumen de 4 líneas con las cifras clave del día.
```
