# Simulación en borrador · miércoles 18/11/2026 (ejecutada el 17/11 por la tarde)

`MODO=borrador` en todos los comandos. **No se ha publicado ni respondido nada.** Se han ejecutado los pasos 1-3 del Prompt 1 de tareas.md, hasta `publicar.py --marcar-revision`. Los pasos 4-7 no se han ejecutado.

## Resultado

**11 planes temporales verificados**, todos en Cádiz capital y con `verificacion_cadiz_capital`. No ha hecho falta relleno «Siempre abierto». El objetivo del criterio 22 es ≥ 12, así que se queda **1 por debajo**.

| Hora | Evento | Lugar | Fuente |
|---|---|---|---|
| 09:00–14:00 | Espacio Empleo Cádiz · feria de empleo (último día) | Antiguos Depósitos de Tabaco, Avda. Marconi 34 | empleo.cadiz.es + nota del Ayuntamiento (oficial) |
| 09:00–21:00 | Exposición «Divergencia cognitiva», de Santiago Pina (hasta el 15/1) | Casa de Iberoamérica · Sala Blas de Lezo | casadeiberoamerica.es (recinto) |
| 09:00–21:00 | Exposición «Nexos. Del lienzo al objeto» (hasta el 10/1) | Museo de Cádiz, Plaza de Mina | Agenda Cultural de Andalucía + ficha de espacio de la Junta (oficial) |
| 09:00–21:00 | Exposición «¿Dónde vas con mantón de Manila?» (hasta el 9/1) | Casa de Iberoamérica · Sala Zitman | casadeiberoamerica.es (recinto) |
| 10:00–19:00 | Exposición «Guillermo Pérez Villalta. El Laboratorio infinito» (hasta el 21/2) | Centro Fundación Unicaja, C/ San Francisco 26 | fundacionunicaja.com (organizador) |
| 11:00–15:00 | Jornada sobre economía social y cooperativas (acceso restringido) | Facultad de Ciencias del Trabajo UCA, C/ Enrique Villegas Vélez 1 | cctrabajo.uca.es + emprende.uca.es (oficial UCA) |
| 18:00 | Patricia Rijnhout y Julio Alexis Muñoz · «Ojillos negros» | Centro Cultural Fundación Unicaja | Junta (agenda y programa del Festival de Cádiz 2026) |
| 19:00 | Trío Ipse · Mozart, Turina y Shostakovich | Conservatorio Manuel de Falla, Avda. las Cortes de Cádiz 3 | Junta (agenda y programa del Festival de Cádiz 2026) |
| 19:00 | Presentación de la Revista del Ateneo dedicada a Falla | Salón de Plenos del Ayuntamiento | ateneocadiz.es (organizador) |
| 19:30 | Tertulia «Puerto de Cádiz. El futuro ya está en marcha» (Teófila Martínez) | Fundación Cajasol, Plaza de San Antonio 14 | fundacioncajasol.com (organizador) |
| 19:30–20:30 | «El Éxito del Fracaso» · Semana Global del Emprendimiento UCA (inscripción previa) | Café Teatro Pay-Pay, C/ Silencio 1 | emprende.uca.es (oficial UCA) |

**Organizadores en Instagram: 0 eventos.** No se pudo leer ninguna cuenta (ver Problemas).

**Generado:**
- Carrusel de 10 imágenes: portada, 8 diapositivas (las 3 primeras con 2 eventos) y cierre.
- 12 stories: 11 de eventos y 1 de cierre.
- `noche/01.png`.
- `caption.txt`, con experimentos frase B, CTA B (compartir) y 5 hashtags.

He revisado todas las imágenes del carrusel y de las stories: se leen bien y no hay recortes. La ilustración de «Divergencia cognitiva» (no tiene imagen oficial) se ha afinado a los motivos marco, bombilla y escultura.

## Descartados (25, detalle en descartados.json)

- **Otro municipio (regla 1):** Saurom (Villamarta, Jerez), Exaltación de la Bulería (Jerez), Día del Flamenco en San Fernando, Congreso de Política Criminal (Campus de Jerez), Congreso RH2Enovables (Algeciras), taller de marketing con IA de UCA Emprende (Jerez), espadrilles (Sevilla), SilverSneakers (Cadiz de EE. UU.).
- **No hay actividad el 18:**
  - Tía Norica: la próxima función es el 27/11.
  - Festival de Música Española: la ficha genérica sobra porque sus dos conciertos van por separado.
  - Programas provinciales de la Junta abiertos según el criterio 3: Circuito de Peñas, Jornadas Europeas de Patrimonio y Día del Flamenco.
  - Storytelling UCA: es el 19/11.
  - Visitas teatralizadas del Falla: 25 y 26/11.
  - Sala Rivadavia: la próxima exposición abre el 19/11.
  - Cádiz CF: no juega en casa.
- **Online (criterio 4):** Singing & Emotional Regulation; IA para Emprendedores y webinario de Canva.
- **No verificables:**
  - FAIA Cádiz: solo aparece en el resumen de un buscador.
  - Realidad Virtual de Puerto América: Fever y Oazis no coinciden.
  - Free tours y juegos de Fever: sin horario del día, y además no hace falta relleno.
- **No son eventos o son de otros años:** noticias de Cádiz Directo y CádizNoticias; artículos de 2015-2019 que mencionan un «18 de noviembre».

## Fuentes web consultadas: 62/62 (100 %)

**Control del 90 %: pasado.** `publicar.py --marcar-revision` → «Fuentes web consultadas: 62/62 · Revisión final registrada».

Hubo 12 consultas con la URL caída, y en todas se buscó con WebSearch como alternativa:
- **403:** Planomato, El Corte Inglés y cadizturismo.com.
- **503:** bibliotecasdeandalucia.es, museosdeandalucia.es y festivaldecadiz.es.
- **404:** PDF de noviembre de la Biblioteca Provincial y PDF de la agenda de extension.uca.es.
- **Dominio no resuelve:** coacadiz.com.
- **Filtro roto:** andalucia.org no aplica el filtro de Cádiz.
- **Sin URL útil:** Hoy Cádiz y «En buena edad».

Todas quedan anotadas en `estado.json` → `fuentes_fallidas_hoy`.

Fuentes de las que salieron eventos: UCA Emprende y eventos UCA, Empleo Cádiz, Museo de Cádiz (Junta), Descubrimiento · Universidad. Las 29 búsquedas restantes de «Descubrimiento diario» no dieron eventos nuevos verificables.

## Problemas

1. **El barrido de la tarde no estaba en main.** `posts/2026-11-17/eventos.json` no tiene `noche_manana` y no existía `posts/2026-11-18/estado.json`. La simulación ha hecho el barrido completo: las 62 consultas, como manda el Prompt 1 cuando «la tarde no se ejecutó».
2. **La API de Meta está al límite.** Responde `(#4) Application request limit reached`:
   - `organizadores.py` leyó 0 de 91 cuentas, así que hay 0 pistas de Instagram (criterio 18 sin cubrir).
   - La recopilación tardó unos 30 min por los reintentos.
   - `etiquetas.py --descubrir` no terminó en 500 s.
   - Si el límite sigue a las 6:50, el flujo real tendrá el mismo hueco y puede retrasarse.
3. **Etiquetas por debajo del mínimo.** Varios eventos tienen menos de 3 etiquetas verificadas. Hay entidades sin buscar (artistas, Pay-Pay, Conservatorio, FAECTA…) porque `--descubrir` no pudo ejecutarse. Quedan en `registros/etiquetas-pendientes.json`.
4. **Entorno.** `setup.sh` instala con `pip`, que apunta a Python 3.13, pero los scripts usan `python` 3.11. Hubo que ejecutar `python -m pip install -r requirements.txt` y reinstalar Pillow (`--ignore-installed`), porque se cargaba la versión de dist-packages y fallaba `_imaging`. En la nube real conviene que `setup.sh` use `python -m pip`.
5. **Cobertura.** 11 planes frente al objetivo de 12. Miércoles flojo: no hay conciertos en salas, teatro ni actividades infantiles verificables.
6. **Precio sin confirmar.** La exposición de Pérez Villalta sale como «Consultar» porque la ficha no da precio.
