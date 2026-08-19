# Guia paso a paso: Cronograma automatizado PMO

Stack: **Supabase** (base de datos) + **GitHub Actions** (recoleccion automatica) +
**Cloudflare Pages** (sitio web + contrasena compartida). Todo gratis, solo se
necesita correo para cada cuenta (nada de Google/Microsoft).

Tienes: VS Code, Docker, Python. Docker no se usa en este proyecto (todo corre en
la nube gratis), pero Python si lo necesitas instalado localmente si quieres
probar el scraper antes de subirlo.

---

## Parte 0 — Que vas a instalar/crear

| Herramienta | Para que | Costo |
|---|---|---|
| Cuenta de GitHub | Guardar el codigo + correr el scraper automatico | Gratis |
| Cuenta de Supabase | Base de datos | Gratis |
| Cuenta de Cloudflare | Hospedar el sitio + contrasena | Gratis |
| Git (si no lo tienes) | Subir el codigo a GitHub | Gratis |
| Python 3.10+ (ya lo tienes) | Probar el scraper en tu maquina (opcional) | Gratis |

Verifica que tengas Git instalado abriendo una terminal en VS Code y corriendo:
```
git --version
```
Si no aparece nada, descarga Git desde https://git-scm.com/downloads e instalalo
(siguiente, siguiente, siguiente — no hay que configurar nada especial).

---

## Parte 1 — Crear el proyecto en Supabase (la base de datos)

1. Ve a https://supabase.com y crea una cuenta con tu correo (no hace falta Google).
2. Click en **New project**.
3. Ponle un nombre, ej. `pmo-cronograma`, y una contrasena de base de datos
   (guardala en algun lado, no la volveras a ver).
4. Espera 1-2 minutos a que se cree el proyecto.
5. En el menu izquierdo, entra a **SQL Editor** → **New query**.
6. Abre el archivo `supabase/schema.sql` de este proyecto, copia todo su
   contenido, pegalo en el editor de Supabase, y dale **Run**.
   Esto crea las tablas `proyectos`, `eventos`, `fuentes_verificadas` con la
   seguridad configurada (el sitio puede leer, pero no escribir).
7. Ve a **Project Settings** (icono de engranaje) → **API**. Ahi vas a ver:
   - **Project URL** → la vas a necesitar como `SUPABASE_URL`
   - **anon public key** → la vas a necesitar como `SUPABASE_ANON_KEY` (para el sitio)
   - **service_role key** → la vas a necesitar como `SUPABASE_SERVICE_KEY` (para el
     scraper — **esta es secreta, nunca la pongas en el sitio web ni la subas a
     GitHub en texto plano**)

---

## Parte 2 — Subir el proyecto a GitHub

1. Ve a https://github.com y crea una cuenta (si no tienes).
2. Click en **New repository**. Nombralo `pmo-cronograma`, marcalo como
   **Private** (asi solo tu equipo con acceso al repo lo ve), y creala.
3. En VS Code, abre una terminal dentro de la carpeta `pmo-cronograma` que te
   entregue y corre:
   ```
   git init
   git add .
   git commit -m "Primer commit"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/pmo-cronograma.git
   git push -u origin main
   ```
   (Te pedira iniciar sesion en GitHub la primera vez — sigue las instrucciones
   en pantalla, es automatico).

4. Ahora configura los "secrets" para que el scraper automatico funcione sin
   exponer tus llaves: en GitHub, entra a tu repo → **Settings** →
   **Secrets and variables** → **Actions** → **New repository secret**.
   Crea dos secrets:
   - `SUPABASE_URL` → pega tu Project URL de Supabase
   - `SUPABASE_SERVICE_KEY` → pega tu service_role key de Supabase

5. El archivo `.github/workflows/collect.yml` ya esta listo para correr todos
   los dias a las 8am (hora Colombia) automaticamente. Tambien puedes probarlo
   ya mismo manualmente: en tu repo, ve a la pestana **Actions** → selecciona
   "Recolectar eventos PMO" → **Run workflow**.

---

## Parte 3 — Agregar tus fuentes reales (RSS)

Por ahora el `schema.sql` trae 2 fuentes de ejemplo. Para agregar las tuyas:

1. En Supabase, ve a **Table Editor** → tabla `fuentes_verificadas`.
2. Click en **Insert row** y llena:
   - `nombre`: como quieres identificarla, ej. "Google Alerts - Automatizacion"
   - `tipo`: `rss`
   - `url`: la URL del feed RSS
   - `categorias`: ej. `{"automatizacion"}` (debe coincidir con las categorias
     que le pusiste a tus proyectos)
   - `activo`: `true`

**Como conseguir URLs de RSS:**
- **Google Alerts** (sin necesitar cuenta de Google — cualquiera puede crear
  una alerta): ve a https://www.google.com/alerts, escribe tu termino de
  busqueda, en "Mostrar opciones" cambia "Entregar en" a **Feed RSS**, y copia
  la URL que te da.
- **Sitios de noticias/blogs**: casi siempre es `sitio.com/feed` o
  `sitio.com/rss`.
- **Buscadores de RSS por tema**: https://hnrss.org (Hacker News filtrado por
  palabra) es un buen ejemplo ya incluido.

---

## Parte 4 — Publicar el sitio en Cloudflare Pages

1. Ve a https://dash.cloudflare.com y crea una cuenta con tu correo.
2. En el menu, busca **Workers & Pages** → **Create** → **Pages** →
   **Connect to Git**.
3. Conecta tu cuenta de GitHub y selecciona el repo `pmo-cronograma`.
4. En la configuracion de build:
   - **Build command**: dejalo vacio
   - **Build output directory**: `site`
5. Dale **Save and Deploy**. En 1-2 minutos te da una URL tipo
   `pmo-cronograma.pages.dev`.

6. Antes de que el calendario muestre datos, edita `site/index.html` (linea
   marcada `CONFIGURA ESTO`) y pon tu `SUPABASE_URL` y `SUPABASE_ANON_KEY`
   reales (la llave **anon**, nunca la service_role). Guarda, sube el cambio:
   ```
   git add .
   git commit -m "Configurar Supabase en el sitio"
   git push
   ```
   Cloudflare Pages vuelve a publicar automaticamente en cuanto detecta el push.

---

## Parte 5 — Poner la contrasena compartida

1. En Cloudflare, ve a tu proyecto de Pages → **Settings** →
   **Environment variables**.
2. Agrega una variable: `SITE_PASSWORD` con el valor que quieras como
   contrasena del equipo (ej. `PMO2026seguro`).
3. Marca que aplique para **Production**.
4. Vuelve a desplegar (Cloudflare te da un boton **Retry deployment**, o basta
   con hacer otro `git push`).

El archivo `site/functions/_middleware.js` ya esta incluido en el proyecto y se
activa automaticamente — Cloudflare Pages detecta cualquier archivo dentro de
`functions/` y lo ejecuta antes de mostrar el sitio. No tienes que instalar
nada mas para que esto funcione.

Ahora, cuando alguien entre a tu URL, vera primero una pantalla pidiendo la
contrasena. Si la escribe bien, entra al calendario y el navegador lo recuerda
por 30 dias (no la vuelve a pedir en ese tiempo desde el mismo dispositivo).

---

## Parte 6 — Agregar eventos manualmente

Lo mas simple: entra a Supabase → **Table Editor** → tabla `eventos` →
**Insert row**, y llena los campos (`titulo`, `fecha_inicio`, `proyecto_id`,
`fuente_tipo` = `manual`, etc). Aparece en el calendario del sitio de
inmediato, sin tener que tocar codigo.

Si mas adelante quieres un formulario bonito dentro del propio sitio para que
cualquiera del equipo agregue eventos sin entrar a Supabase, dimelo y lo
armamos como siguiente paso — es una pagina HTML adicional con un formulario
que llama a la API de Supabase.

---

## Resumen de lo que queda corriendo solo

- Todos los dias, GitHub Actions ejecuta el scraper → revisa tus fuentes RSS →
  guarda eventos nuevos en Supabase (sin duplicar).
- El sitio en Cloudflare Pages lee esos datos en tiempo real y los muestra en
  el calendario.
- Nadie externo puede ver el sitio sin la contrasena, y no aparece en buscadores.
- Todo esto sin pagar nada, mientras el uso se mantenga dentro de los limites
  gratuitos generosos de cada servicio (para 200 personas viendo un
  calendario, estas muy lejos de esos limites).

## Si algo falla
- **El calendario no muestra nada**: revisa que `SUPABASE_URL` y
  `SUPABASE_ANON_KEY` en `index.html` sean correctos, y que la tabla `eventos`
  tenga datos.
- **El scraper no guarda nada**: ve a GitHub → Actions → abre la ultima
  ejecucion y lee los logs, ahi dice exactamente que fuente fallo o si hay un
  problema con las llaves.
- **La contrasena no funciona**: confirma que la variable `SITE_PASSWORD` este
  guardada en Cloudflare Pages y que hiciste un nuevo deploy despues de
  agregarla.
