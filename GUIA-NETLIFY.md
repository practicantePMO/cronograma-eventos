# Guia de despliegue en Netlify — Cronograma PMO

Esta es la version del proyecto adaptada para **Netlify** (en vez de Cloudflare),
porque el filtro de tu red corporativa si permite abrir dominios `.netlify.app`.

Todo lo demas del sistema es identico: Supabase (base de datos), GitHub Actions
(scraper diario) y SearXNG en Render (busqueda automatica). Solo cambia la
plataforma que sirve el sitio web y el panel.

Si ya tenias configurados Supabase, SearXNG (Render) y los secrets de GitHub,
**NO hace falta rehacerlos** — sirven igual para esta version. Lo unico nuevo
es desplegar el sitio en Netlify.

---

## Estructura de esta version

```
pmo-cronograma-netlify/
  site/                      <- el sitio (index.html, admin.html, robots.txt)
  netlify/
    edge-functions/
      auth.js                <- protege todo con la contrasena compartida
    functions/
      proyectos.js           <- API: crear/listar proyectos
      eventos.js             <- API: crear eventos manuales
  netlify.toml               <- configuracion de Netlify
  scraper/                   <- igual que antes (no cambia)
  searxng/                   <- igual que antes (no cambia)
  supabase/                  <- igual que antes (no cambia)
  .github/                   <- igual que antes (no cambia)
```

---

## Paso 1 — Configurar Supabase en el sitio

Edita `site/index.html` y pon tu `SUPABASE_URL` y `SUPABASE_ANON_KEY`
(publishable key) reales, donde dice `CONFIGURA ESTO`. (Si ya lo tenias del
intento anterior, copia los mismos valores.)

---

## Paso 2 — Subir a GitHub

Puedes usar el mismo repositorio de antes (reemplazando los archivos) o crear
uno nuevo. Si es el mismo:

```
git add .
git commit -m "Version Netlify"
git push
```

---

## Paso 3 — Crear la cuenta y el sitio en Netlify

1. Ve a https://app.netlify.com y crea una cuenta (puedes entrar con tu cuenta
   de GitHub, o con correo — no requiere Google).
2. Click en **Add new site** → **Import an existing project**.
3. Conecta GitHub y selecciona tu repositorio.
4. En la configuracion de build, Netlify deberia leer el `netlify.toml` solo.
   Confirma que:
   - **Publish directory**: `site`
   - **Build command**: (vacio)
   - **Functions directory**: `netlify/functions` (lo toma del toml)
5. Dale **Deploy**. En 1-2 minutos te da una URL tipo `TU-SITIO.netlify.app`.

---

## Paso 4 — Configurar las variables de entorno en Netlify

Ve a tu sitio en Netlify → **Site configuration** → **Environment variables**
→ **Add a variable**, y crea estas tres:

- `SITE_PASSWORD` -> la contrasena compartida del equipo
- `SUPABASE_URL` -> tu Project URL de Supabase
- `SUPABASE_SERVICE_KEY` -> tu Secret key de Supabase

Despues de agregarlas, ve a **Deploys** → **Trigger deploy** →
**Deploy site** para que el sitio tome las variables nuevas (las variables
solo se aplican en despliegues hechos DESPUES de crearlas).

---

## Paso 5 — Probar

1. Abre tu URL `.netlify.app`.
2. Deberia pedirte la contrasena. Ponla.
3. Veras el calendario. Prueba el boton **"+ Agregar proyecto"** — te lleva al
   panel, donde puedes crear un proyecto o un evento manual.

---

## Recordatorio: el scraper y SearXNG no cambian

El `SEARXNG_URL`, `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` que configuraste como
**secrets en GitHub** siguen funcionando igual para el scraper automatico. Esta
migracion a Netlify solo afecta el sitio web y el panel, no la parte de
recoleccion de eventos.

## Si algo falla
- **Pide contrasena en bucle / no entra**: confirma que `SITE_PASSWORD` este
  bien escrita en las Environment variables de Netlify y que hiciste un nuevo
  Deploy despues de agregarla.
- **El panel da error al guardar**: revisa que `SUPABASE_URL` y
  `SUPABASE_SERVICE_KEY` esten en las Environment variables de Netlify (son
  necesarias para las funciones proyectos.js y eventos.js).
- **La pagina admin no carga**: recuerda abrir el sitio por su URL
  `.netlify.app`, nunca abriendo el archivo local con doble clic.
