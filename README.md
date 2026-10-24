# Agenda Cádiz — agente autónomo de Instagram y Facebook

Recopila **todas** las actividades de **Cádiz capital** (solo el término municipal; ver `CLAUDE.md`, regla 1), las publica en Instagram con la Graph API de Meta, las replica en la página de Facebook y hace crecer ambos perfiles de forma 100 % orgánica. Funciona con tareas programadas de Claude Code en la nube (Europe/Madrid).

**Reparto de trabajo:** los scripts hacen la mecánica (recopilar, renderizar, vídeo, publicar, métricas, avisos); el agente (Claude) hace el juicio: verificar Cádiz capital evento a evento, contrastar fuentes, redactar con palabras propias y decidir qué responder. Instrucciones permanentes: [`CLAUDE.md`](CLAUDE.md). Prompts de las tareas: [`tareas.md`](tareas.md).

## Estructura
```
CLAUDE.md  marca.md  fuentes.md  fuentes.json  tareas.md  setup.sh  requirements.txt
agenda.py (utilidades, reparto, validación)   recopilar.py   render.py   reel.py
publicar.py   interaccion.py   metricas.py   notificar.py   patrocinios.py
plantilla/ (portada, eventos, story, story-noche, story-patrocinio, estilos.css, sin-foto/)
musica/ (5 pistas CC0 + licencias.md)   patrocinadores/ (desactivado)
posts/AAAA-MM-DD/ (eventos.json, caption.txt, estado.json, carrusel/, stories/, noche/, reel/, finde/, mensual/)
registros/ (fuentes.log, mejoras.md, metricas.jsonl, pendientes.json…)   ejemplos/ (pruebas de render y reel)
```

## Qué tienes que configurar tú

### 1. Cuenta y página
1. Instagram **profesional** (Empresa o Creador) vinculada a tu **página de Facebook** (Instagram → Ajustes → Cuenta → Cuentas vinculadas / o desde la página: Configuración → Cuentas vinculadas). Para la respuesta por mensajes: Instagram → Ajustes → Mensajes y respuestas a historias → *Permitir acceso a los mensajes*.
2. Tú debes ser **administrador de la página** (con control total).

### 2. App de Meta (developers.facebook.com)
1. *Mis apps → Crear app* → caso de uso **Otro / Empresa**, tipo **Empresa**. Añade los productos **Facebook Login for Business** (o Facebook Login) e **Instagram** (API de Instagram con inicio de sesión de Facebook).
2. Mantén la app en **modo Desarrollo** y con tu usuario como administrador: **para usar tu propia cuenta no hace falta revisión de la app**; todos los permisos funcionan con *acceso estándar* para quien tiene rol en la app. Solo necesitarías *App Review* (acceso avanzado) + verificación de empresa si pasas a modo Live o gestionas cuentas de terceros.
3. Permisos (todos se piden al generar el token):

| Permiso | Para qué | ¿Revisión de Meta? |
|---|---|---|
| `instagram_basic` | leer la cuenta y sus medios | Solo si modo Live / cuentas ajenas |
| `instagram_content_publish` | publicar carruseles, stories y reels | Solo si modo Live / cuentas ajenas |
| `instagram_manage_comments` | leer y responder comentarios | Solo si modo Live / cuentas ajenas |
| `instagram_manage_insights` | métricas de IG | Solo si modo Live / cuentas ajenas |
| `instagram_manage_messages` | mensajes privados y respuestas privadas a comentarios | Solo si modo Live / cuentas ajenas |
| `pages_show_list` | listar tus páginas y obtener el token de página | Solo si modo Live |
| `pages_read_engagement` | leer posts y comentarios de la página | Solo si modo Live |
| `pages_manage_posts` | publicar fotos, carruseles, stories y reels en la página | Solo si modo Live |
| `pages_manage_engagement` | responder comentarios de la página | Solo si modo Live |
| `pages_messaging` | mensajes de la página (Messenger) | Solo si modo Live |
| `read_insights` | métricas de la página | Solo si modo Live |
| `business_management` | solo si cambias a usuario de sistema del Business Manager | Sí, al pasar a Live |

*Resumen:* en modo Desarrollo con tu cuenta, **ninguno requiere revisión**; en modo Live, **todos los anteriores** pasan por App Review (los de mensajería e Instagram suelen ser los más exigentes). Meta renombra y retira permisos/métricas con frecuencia: comprueba la lista en el Explorador de la Graph API.

### 3. Obtener `META_TOKEN` (token de página) paso a paso
1. *Herramientas → Explorador de la Graph API*. Elige tu app y **Obtener token de acceso de usuario**; marca los permisos de la tabla y autoriza (selecciona tu página y tu cuenta de Instagram).
2. Pásalo a **larga duración** (≈ 60 días) en el navegador o con curl (en tu ordenador, no en el chat):
   `GET https://graph.facebook.com/v23.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=TOKEN_CORTO`
3. Obtén el **token de página** con ese token largo: `GET https://graph.facebook.com/v23.0/me/accounts?access_token=TOKEN_LARGO`. Copia el `access_token` de **tu página**: ese es `META_TOKEN`. No caduca por tiempo, pero deja de valer si cambias la contraseña de Facebook o pierdes el rol de administrador.
4. Obtén los IDs: `FB_PAGE_ID` = el `id` de esa misma respuesta. `IG_USER_ID`: `GET /{FB_PAGE_ID}?fields=instagram_business_account&access_token=TOKEN_DE_PAGINA` → `instagram_business_account.id`.
5. Comprueba el token en `developers.facebook.com/tools/debug/accesstoken` (debe mostrar *Nunca caduca* y los permisos).
6. **Cambio futuro a token de usuario del sistema** (Business Manager): solo hay que sustituir el valor de `META_TOKEN`; el código no cambia (usa siempre `Authorization: Bearer`, y `debug_token`).

### 4. Resend (avisos por email)
1. Crea cuenta gratis en resend.com → *API Keys → Create* (permiso *Sending access*) = `RESEND_API_KEY`.
2. Sin dominio propio el remitente es `onboarding@resend.dev` y **solo puedes enviar a tu propio email** (el de la cuenta de Resend) = `EMAIL_DESTINO`. Con dominio verificado, define también `EMAIL_REMITENTE` ("Agenda Cádiz <avisos@tudominio.es>").

### 5. Entorno cloud "agenda-cadiz"
- **Red**: acceso completo (ya lo tiene): necesita las fuentes, `graph.facebook.com`, `api.resend.com`, `raw.githubusercontent.com` y `github.com`.
- **Variables normales**: `MODO=borrador`, `PATROCINIOS=off`, `TZ=Europe/Madrid` (ya puestas), más `IG_USER_ID`, `FB_PAGE_ID`, `EMAIL_DESTINO` (no son secretos).
- **Secretos de red** (el proxy los inyecta; la sesión no ve el valor): `META_TOKEN` para `graph.facebook.com` y `graph.instagram.com`; `RESEND_API_KEY` para `api.resend.com`. El código **no necesita ver el valor**: si la variable no existe envía la petición igualmente y deja que el proxy la complete; si existe como variable normal, la usa en la cabecera `Authorization: Bearer`. ⚠️ No he podido comprobar de qué forma concreta (cabecera, parámetro) inyecta el proxy: lanza `python publicar.py --diagnostico` en una sesión del entorno; debe decir *Token: OK*. Si falla con "An active access token must be used", ajusta la configuración del secreto (cabecera `Authorization`) o ponlo como variable normal.
- **Script de configuración**: `bash setup.sh`.
- **Repo público y push a `main`**: las imágenes/vídeos se sirven desde `raw.githubusercontent.com/<usuario>/agenda-cadiz/main/...`; el repo debe ser **público** y las sesiones deben poder hacer push a `main` (permitir push a ramas no `claude/…` en la configuración del entorno/GitHub). Todo lo que se publica en `posts/` es público.
- **Tareas programadas**: ver [`tareas.md`](tareas.md) (4 tareas + prompts exactos).

### Variables
`META_TOKEN, IG_USER_ID, FB_PAGE_ID, RESEND_API_KEY, EMAIL_DESTINO, MODO (borrador|publicar), PATROCINIOS (off|on)` · opcionales: `EMAIL_REMITENTE, GITHUB_REPO, GRAPH_VERSION` (por defecto v23.0; si Meta la retira, súbela).

## Puesta en marcha recomendada
1. Configura todo lo anterior y ejecuta `python publicar.py --diagnostico`.
2. Deja `MODO=borrador` unos días: revisa `posts/*/` (imágenes, captions, descartados).
3. Prueba una publicación real con una sola story o un carrusel de prueba en una cuenta de pruebas antes de cambiar a `MODO=publicar`.

## Pruebas incluidas
`python render.py --demo 5 14 22 33 50` → `ejemplos/demo-N/carrusel/*.png` · `python reel.py --demo` → `ejemplos/reel-demo.mp4`.

## Limitaciones conocidas (honestas)
- Solo `laciudad.cadiz.es` (Falla, Central Lechera…) tiene parser estructurado; el resto de fuentes se leen como texto por el agente. Varias fuentes de `fuentes.md` están marcadas ❌/⚠️ (URL por localizar o bloquean a bots).
- La API de Meta y los nombres de las métricas cambian: cada métrica se pide por separado y los fallos se registran sin detener el proceso. Nada de lo que habla con Meta (`publicar.py`, `interaccion.py`, `metricas.py`) se ha podido probar contra la API real sin credenciales; pruébalo en `borrador`/con una cuenta de pruebas.
- Respuesta por palabra clave por mensaje privado: Meta solo permite una respuesta privada por comentario, dentro de 7 días y con la mensajería activada.
- Los reels se limitan a 30 s: con muchos eventos el reel muestra los primeros (cronológicos) y el resto va en el carrusel.
