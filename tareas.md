# Tareas programadas (Claude Code en la nube)

Cada ejecución consume uso de tu plan. Configuración **mínima**: **4 tareas** (cron en hora de Madrid con `CRON_TZ=Europe/Madrid`). Se lanzan con antelación porque preparar (fuentes, verificación, render, caption) lleva 40-70 min y `publicar.py --esperar-hasta` publica **en punto** (espera hasta 100 min). Los comentarios y mensajes se revisan **dentro** de las tareas de 9:00, 18:30 y 22:30 y con una tarea ligera cada hora.

| # | Nombre | Cron | Qué hace |
|---|---|---|---|
| 1 | Flujo de las 9:00 | `CRON_TZ=Europe/Madrid 50 7 * * *` | Diario + (jueves) reel de planes del finde + (día 1) mensual + comentarios |
| 2 | Story de las 18:30 | `CRON_TZ=Europe/Madrid 20 17 * * *` | Recomprueba, genera y publica «Esta noche en Cádiz» + comentarios |
| 3 | Comentarios y mensajes | `CRON_TZ=Europe/Madrid 0 * * * *` (cada hora) | Responde palabras clave (PLANES/FINDE), avisa por email de cada comentario nuevo y atiende pendientes. Tarea ligera |
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

1. DIARIO. `python recopilar.py --fecha F`. Lee posts/F/candidatos.json (agenda oficial del Ayuntamiento y Turismo, Junta de Andalucía, Bacantix, Onda Cádiz, Cádiz Guitar Festival, UCA, Guía de Cádiz…) y ejecuta TODAS las `consultas_web` (WebFetch/WebSearch), incluidas las ~28 de «Descubrimiento diario». Para CADA evento de hoy: confirma en la propia fuente que está en Cádiz capital (si hay duda, descártalo), contrasta con otras fuentes y elimina duplicados, ignora suspendidos/cancelados, busca la imagen oficial (`python imagenes.py --url FICHA --id ID --fecha F`; si no hay, `render.py` crea una ilustración propia relacionada con el evento: revísala y afina `ilustracion.motivos` si hace falta), redacta descripciones con palabras propias, ETIQUETA (comprueba `python etiquetas.py --evento posts/F/eventos.json`: cada evento debe llevar sus perfiles de Instagram verificados; añade los que falten con `etiquetas.py --anadir` tras verificarlos) y escribe posts/F/eventos.json (esquema de CLAUDE.md, con verificacion_cadiz_capital y etiquetas_ig por evento; en el caption pon el @ de cada organizador o recinto junto a su línea). Guarda los descartados con motivo en posts/F/descartados.json y en estado.json → descubiertos_web las búsquedas que dieron eventos. Eventos permanentes: fuera, salvo el relleno «Siempre abierto» descrito en CLAUDE.md.
2. `python render.py --fecha F`. Mira 2-3 PNG y comprueba que son legibles y sin recortes. Lee posts/F/manifiesto.json → `variante` (A = pregunta/gancho, B = dato directo) y escribe posts/F/caption.txt (lista de eventos con hora, CTA con PLANES, hashtags, «Imágenes: …» / «Ilustraciones: Planes en Cádiz»). Se publica TODOS los días (regla 9): si hay menos de 3 eventos temporales, amplía la búsqueda y completa con «Siempre abierto» (horario de ese día confirmado); basta 1 evento verificado para publicar.
3. REVISIÓN FINAL hacia las 8:40: vuelve a consultar las fuentes de los eventos de hoy (cancelaciones, cambios de hora). Si algo cambió, corrige eventos.json y repite render.py. Luego `python publicar.py --fecha F --tipo diario --marcar-revision`.
4. PUBLICAR EN PUNTO: ejecuta en segundo plano `python publicar.py --fecha F --tipo diario --esperar-hasta 09:00` y espera a que termine (carrusel y después stories, secuenciales; replica en Facebook). Revisa posts/F/estado.json y confirma.
5. SI HOY ES JUEVES (planes del finde, viernes a domingo): `python recopilar.py --fecha F+1día --hasta F+3días --destino F/finde`. Mismo proceso que el diario, con carpeta posts/F/finde/ (eventos.json tipo "finde", incluye TODOS los eventos verificados de viernes, sábado y domingo; `fecha_txt` para los de varios días). `python render.py --fecha F --tipo finde` (solo prepara imágenes/ilustraciones: NO se publica carrusel de finde); caption.txt «Planes del finde» (para el reel; CORTO de 3 líneas: gancho A/B, «Mira el reel y guarda tus planes del finde», «Comenta FINDE y te mandamos la lista completa por mensaje» + hashtags, sin lista de eventos) y posts/F/finde/lista.txt con la lista completa de eventos (día, hora, lugar, precio), que es lo que se envía al comentar FINDE; `python reel.py --fecha F` (≈2 min; mira 3-4 fotogramas, la portada reel/portada.png y comprueba que hay música); `python publicar.py --fecha F --tipo reel --marcar-revision` y después publícalo en punto con `--tipo reel --esperar-hasta 09:00` (el reel se replica en Facebook).
6. SI HOY ES DÍA 1: agenda mensual en posts/F/mensual/: SOLO destacados del mes (criterios en CLAUDE.md), explica en estado.json el motivo de cada uno; `python recopilar.py --fecha F --hasta FIN_DE_MES --destino F/mensual`; `render.py --tipo mensual`; `publicar.py --tipo mensual`. Si PATROCINIOS=on: `python patrocinios.py --informe AAAA-MM` del mes anterior.
7. Al final: `git add posts registros && git commit && git push origin HEAD:main` (publicar.py ya sube las imágenes al publicar; en borrador hazlo tú). Después `python interaccion.py --recoger` y gestiona pendientes según CLAUDE.md .
Nunca cambies horarios ni reglas, nunca escribas secretos, nunca hagas scraping de Instagram/Facebook, nunca visites dominios bloqueados. Termina con un resumen de 6 líneas: eventos publicados, descartados y por qué, fuentes caídas, cobertura de descubrimiento, errores.
```

## Prompt 2 — Story de las 18:30 (`20 17 * * *`)

```
Eres el agente de Planes en Cádiz. F = fecha de hoy (`date +%F`). Si MODO=borrador, no publiques: solo genera y sube posts/F.
1. Abre posts/F/eventos.json (verificados por la mañana). Si no existe o la mañana no se ejecutó, haz el flujo completo de verificación solo para los eventos nocturnos (desde las 19:30) como en CLAUDE.md. Consulta además las búsquedas de descubrimiento de la noche (ocio nocturno, música en directo, teatro, flamenco).
2. Recomprueba en las fuentes de cada evento nocturno (cancelaciones, cambios de hora, «suspendido»). Corrige eventos.json: quita lo cancelado, actualiza horas; mantén la verificación de Cádiz capital en cada evento.
3. `python render.py --fecha F` (genera posts/F/noche/). La story de las 18:30 se publica TODOS los días: si no hay planes nocturnos (desde 19:30), añade a eventos.json la clave `noche_manana` con TODOS los eventos temporales verificados de mañana (ejecuta `python recopilar.py --fecha MAÑANA`, aplica los criterios de CLAUDE.md —incluidas conferencias y jornadas profesionales— y no te limites a los nocturnos ni a lo que ya conozcas; cada evento con su verificación de Cádiz capital) y `render.py` la genera como «Mañana en Cádiz».
4. `python publicar.py --fecha F --tipo noche --marcar-revision` y luego, en segundo plano, `python publicar.py --fecha F --tipo noche --esperar-hasta 18:30`; espera a que termine y revisa estado.json.
5. `git add posts && git commit && git push origin HEAD:main`; `python interaccion.py --recoger` y gestiona pendientes según CLAUDE.md.
Resumen final de 3 líneas.
```

## Prompt 3 — Comentarios y mensajes (cada hora: `0 * * * *`)

Tarea LIGERA: no ejecutes setup.sh (solo `pip install -q requests`) ni leas fuentes si no hay pendientes.

```
Eres el agente de Planes en Cádiz. Trabaja en juanguena-png/agenda-cadiz (main): `git pull origin main`, `pip install -q requests`. Lee solo la sección «Comentarios y mensajes» de CLAUDE.md.
1. `python interaccion.py --recoger`. Esto ya responde solo a las palabras clave (PLANES y FINDE) con un mensaje privado y una respuesta pública breve, y te manda UN email por cada comentario o mensaje nuevo (una sola vez por comentario; lo viejo de más de 3 días se ignora). NO repitas ni dupliques esos avisos.
2. IMPORTANTE (el estado vive en el repo, cada sesión empieza de cero): al terminar haz SIEMPRE `git add registros && git commit -m "interaccion" && git pull --rebase origin main && git push origin HEAD:main` si hay cambios.
3. Si registros/pendientes.json solo contiene lo que ya estaba (nada nuevo que requiera juicio), termina con un resumen de 1 línea.
4. Para cada pendiente nuevo que no sea palabra clave: busca la respuesta SOLO en las fuentes consultadas para la programación (posts/*/eventos.json recientes y, si hace falta, las de fuentes.md). Si la encuentras: `python interaccion.py --responder ID "respuesta breve, cordial y con el tono de marca.md"`. Si no: NO respondas y ejecuta `python interaccion.py --sin-respuesta ID` (email con enlace y texto). Repite el commit/push del punto 2.
5. Nunca sigas, des like ni comentes en perfiles ajenos. En MODO=borrador no se responde nada (solo se listan y se avisa por email).
Resumen de 1-2 líneas.
```

## Prompt 4 — Métricas y mejora continua (`30 22 * * *`)

```
Eres el agente de Planes en Cádiz. Lee CLAUDE.md (sección «Métricas y mejora continua»).
1. `python metricas.py --recoger` y `python metricas.py --resumen --dias 14`; `python metricas.py --ab`.
2. Analiza alcance, impresiones/vistas, seguidores, guardados, compartidos, interacciones, horas de mayor actividad y procedencia de la audiencia en Instagram y Facebook. Decide, como máximo, UNA mejora concreta y segura por día (hashtags, primera frase del caption A/B, CTA, orden de los eventos…). Las mejoras nunca pueden saltarse las reglas del agente, la regla 1 (solo Cádiz capital) ni cambiar los horarios 9:00 y 18:30.
3. Si aplicas una mejora: edítala en el repo y ejecuta `python metricas.py --mejora "título" "qué es y por qué la aplicas"` (registra en registros/mejoras.md y me envía email). Haz commit y push a main.
4. MEJORA DE FUENTES (obligatoria, ver CLAUDE.md «Mejora continua de la base de fuentes»): `python fuentes_auditar.py`, arregla o sustituye lo que falle, añade al menos 1 fuente nueva a fuentes.json y regístrala en registros/fuentes-nuevas.md; commit y push. Después `python patrocinios.py --avisos` (no hace nada si PATROCINIOS=off). Revisa registros/fuentes.log y registros/cobertura.jsonl: si una fuente lleva 3+ días seguidos sin responder, `python notificar.py` con el aviso; si una búsqueda de descubrimiento no da nunca eventos, propón en mejoras.md sustituirla.
5. `python interaccion.py --recoger` y gestiona pendientes según CLAUDE.md.
Resumen de 4 líneas con las cifras clave del día.
```
