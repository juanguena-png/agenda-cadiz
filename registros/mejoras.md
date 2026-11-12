# Mejoras aplicadas

Historial de mejoras basadas en métricas (fecha · mejora · motivo). Lo escribe `metricas.py --mejora`.

## 2026-10-25 · Métricas Facebook sin métrica inválida

page_impressions_unique daba error 100 en cada recogida; se retira para que las métricas de FB se guarden sin errores

## 2026-10-29 · Auditoría semanal (jueves)

Categorías de la semana (25-29 oct): otros 7, exposición 4, música 4, infantil 1, fiesta 1, deporte 1; sin teatro, humor ni flamenco. Recintos más repetidos: Fundación Cajasol, Ateneo, Palacio de Congresos. Propuesta: reforzar peñas flamencas, teatro de pequeño formato (Ancha 16, El Bidón) y agenda infantil. Búsquedas de descubrimiento sin rendimiento: no hay `descubiertos_web` registrado, no se puede medir todavía.

## 2026-11-02 · Propuesta (no aplicada): favorecer la variante B de primera frase

A/B con 5 muestras por variante: alcance medio A 41,0 y B 90,2 (B incluye el carrusel de Tosantos, 244). Los días de A y B tuvieron contenido distinto, así que no se puede atribuir la diferencia a la frase. Se mantiene la alternancia hasta 8-10 muestras por variante; si B sigue por encima sin el valor atípico, pasar a 2 de cada 3 días en B.

## 2026-11-07 · Publicación robusta del carrusel (tope de etiquetas)

Instagram invalida el carrusel si suma más de ~28 etiquetas entre diapositivas (devuelve id 0): publicar.py recorta a 25 (portada primero) y reintenta recreando las diapositivas sin colaboradores/ubicación si Meta lo rechaza. Incidente del 7 nov: carrusel y stories salieron ~30 min tarde.

## 2026-11-12 · Auditoría semanal (jueves)

Semana 6-12 nov: 27 planes (6, 6, 3, 3, 3, 2, 4 por día). Categorías: otros 12, música 8, exposición 3, teatro 1, infantil 1, deporte 1, fiesta 1; sin humor, cine ni gastronomía. Recintos: Fundación Unicaja y Cajasol (4 cada uno), Casa de Iberoamérica y Ateneo (3). Los carruseles de entre semana (2-4 planes) alcanzan 15-30 frente a 100-180 los fines de semana. Propuesta: reforzar fuentes de teatro/humor, infantil y gastronomía, y buscar planes de entre semana (talleres puntuales, presentaciones, charlas) para subir la media de planes diarios.
