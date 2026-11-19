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

## 2026-11-16 · Vigilante de publicación

El proceso de espera de las 9:00 murió sin avisar el 16-nov y la publicación salió a las 10:15; vigilar_publicacion.py relanza publicar.py si muere o no completa

## 2026-11-16 · Primera frase fijada en la variante B (dato directo)

Tras 12 muestras por lado, B logra 74,3 de alcance medio y 1,08 seguidores nuevos por post frente a 47,2 y 0,33 de A. crecimiento.py fija la variante al superar 10 muestras y un 15 % de mejora.

## 2026-11-17 · Control de cuota de la API de Meta

Evita el error #4 (17/11): publicar con prioridad, lecturas de organizadores con caché 4 h y parada al 50 % de X-App-Usage

## 2026-11-18 · Comparativa de cobertura

`organizadores.py --comparar 2026-11-18`: nosotros 8 eventos frente a las 20 diapositivas de @gaditanisimamente (5 líneas suyas sin cubrir, entre ellas un plan «con aforo muy limitado» sin detallar en el texto). @agendadecadiz publicó una crónica del IV Foro Mujeres Líderes en Economía Azul (evento ya celebrado, sin plan futuro). @agendacadiz da «Invalid user id» (cuenta sin acceso por API). Pista: con el criterio 22 (≥ 12 planes temporales) y la inclusión de exposiciones temporales y eventos de varios días, la brecha de cobertura debería cerrarse en los próximos días.

## 2026-11-19 · Vigilante: comprobar stories

El vigilante daba por completa la publicación mirando solo el carrusel: el 19-nov dos stories de IG fallaron (9007) y se reintentaron a mano; ahora exige que todas las publicaciones estén en estado publicado
