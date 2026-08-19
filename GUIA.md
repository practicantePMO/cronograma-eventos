# Guia paso a paso: Cronograma automatizado PMO (version SearXNG)

Stack final, 100% gratuito y sin depender de Google/Microsoft en ninguna parte:

| Pieza | Herramienta | Por que |
|---|---|---|
| Base de datos | **Supabase** (Postgres) | Gratis, estable, cuenta con solo un correo |
| Sitio + panel + contrasena | **Cloudflare Pages** + Functions | Gratis, sin limite de usuarios, sin cuenta de terceros para el equipo |
| Automatizacion diaria | **GitHub Actions** | Gratis, corre el scraper solo |
| Busqueda automatica de eventos por categoria | **SearXNG** (auto-hospedado en Render) | Open source, sin cuenta de terceros, sin limite diario, no depende de ninguna API que se pueda cerrar |

Si ya tenias el proyecto anterior armado (con RSS/Google), **puedes borrar
todo y empezar de cero con esta guia** sin ningun problema — no hay nada que
migrar, la base de datos se recrea con el mismo `schema.sql`.

---

## Parte 0 — Cuentas que vas a necesitar (todas gratis, solo con correo)

1. **GitHub** — https://github.com (ya la tienes)
2. **Supabase** — https://supabase.com (ya la tienes)
3. **Cloudflare** — https://dash.cloudflare.com (ya la tienes)
4. **Render** — https://render.com — **nueva**, la vamos a usar solo para
   alojar SearXNG. Se crea con correo, sin tarjeta de credito.

---

## Parte 1 — Supabase (si empiezas de cero)

1. Crea un proyecto nuevo en Supabase.
2. Entra a **SQL Editor** → **New query**, pega el contenido de
   `supabase/schema.sql`, dale **Run**.
3. Ve a **Settings** → **Data API** para copiar tu **Project URL**, y a
   **Settings** → **API Keys** para copiar tu **Publishable key** (antes
   `anon`) y tu **Secret key** (antes `service_role`).

Si ya tenias esto del intento anterior, no hace falta repetirlo — sigue igual.

---

## Parte 2 — Desplegar SearXNG en Render (la pieza nueva)

Esto reemplaza por completo lo que intentamos con Google. Vamos paso a paso.

1. **Antes de subir nada**, abre `searxng/settings.yml` en VS Code y cambia
   la linea:
   ```
   secret_key: "REEMPLAZA_ESTO_POR_TU_PROPIA_CLAVE_ALEATORIA"
   ```
   Genera una clave propia corriendo esto en tu terminal (tienes Python
   instalado, asi que funciona directo):
   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copia el resultado y pegalo en el archivo, reemplazando el texto de
   ejemplo (dejando las comillas).

2. Sube el proyecto completo a GitHub (si ya tienes el repo, solo agrega los
   archivos nuevos):
   ```
   git add .
   git commit -m "Agregar SearXNG"
   git push
   ```

3. Ve a https://dashboard.render.com → **New +** → **Web Service**.
4. Conecta tu cuenta de GitHub y selecciona tu repositorio
   `cronograma-eventos`.
5. En la configuracion:
   - **Root Directory**: `searxng`
   - **Runtime**: Docker (Render lo detecta solo al ver el `Dockerfile`)
   - **Instance Type**: Free
6. Dale **Deploy Web Service**. La primera construccion tarda unos minutos.
7. Cuando termine, Render te da una URL parecida a
   `https://cronograma-searxng.onrender.com` — **copiala**, la vas a usar
   como `SEARXNG_URL`.

8. Pruebala abriendo en el navegador:
   ```
   https://TU-URL-DE-RENDER.onrender.com/search?q=test&format=json
   ```
   Si ves un JSON con resultados (no un error), esta funcionando.

**Nota sobre el plan gratis de Render**: el servicio "se duerme" tras
aproximadamente 15 minutos sin uso, y la siguiente vez que alguien lo llama
tarda unos 30-50 segundos en "despertar". Para nuestro caso no es un
problema — el scraper solo lo llama una vez al dia, y esos segundos de espera
no afectan nada mas.

---

## Parte 3 — GitHub: subir el codigo y configurar los secrets

1. Si no tienes el repo creado todavia, crealo en GitHub (privado) y sube el
   proyecto:
   ```
   git init
   git add .
   git commit -m "Primer commit"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
   git push -u origin main
   ```

2. Ve a tu repo → **Settings** → **Secrets and variables** → **Actions** →
   **New repository secret**, y crea estos tres:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `SEARXNG_URL` → la URL de Render que copiaste en la Parte 2

3. Prueba el workflow manualmente: pestana **Actions** → "Recolectar eventos
   PMO" → **Run workflow**. Revisa los logs — deberia decir cuantas
   categorias encontro y si guardo eventos nuevos.

---

## Parte 4 — Cloudflare Pages: el sitio, el panel y la contrasena

1. Edita `site/index.html` y pon tu `SUPABASE_URL` y `SUPABASE_ANON_KEY`
   (publishable key) reales, donde dice `CONFIGURA ESTO`.

2. En Cloudflare → **Workers & Pages** → **Create** → **Pages** →
   **Connect to Git** → selecciona tu repo.
   - **Build command**: vacio
   - **Build output directory**: `site`
   - Dale **Save and Deploy**.

3. Ve a **Settings** → **Environment variables** del proyecto de Pages, y
   agrega:
   - `SITE_PASSWORD` → la contrasena compartida del equipo
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   (Estas ultimas dos las necesitan `functions/api/proyectos.js` y
   `functions/api/eventos.js` para que el panel funcione.)

4. Vuelve a desplegar (Retry deployment, o haz otro `git push`).

5. Sube todo con git:
   ```
   git add .
   git commit -m "Configurar Supabase y contrasena"
   git push
   ```

---

## Como queda funcionando todo, de punta a punta

1. El equipo PMO entra a la URL de Cloudflare Pages, pone la contrasena
   compartida, y ve el calendario.
2. Desde el boton **"+ Agregar proyecto"** cualquiera crea un proyecto nuevo
   con sus categorias, sin tocar Supabase ni saber programar.
3. Todos los dias, GitHub Actions corre el scraper:
   - Lee RSS que hayas configurado a mano (opcional).
   - Busca automaticamente en tu SearXNG por cada categoria de cada
     proyecto activo.
   - Guarda los eventos nuevos en Supabase, sin duplicar.
4. El sitio muestra todo en tiempo real.
5. Nada de esto depende de una cuenta de Google, Microsoft, ni de una API
   con fecha de cierre — cada pieza es o bien tuya (SearXNG, corriendo en tu
   propio servicio de Render) o de proveedores con planes gratuitos estables
   (Supabase, Cloudflare, GitHub).

## Si algo falla

- **SearXNG no responde / tarda mucho**: es normal la primera vez tras estar
  dormido (plan gratis de Render). Si sigue sin responder despues de 1
  minuto, entra al dashboard de Render y revisa los logs del servicio.
- **El scraper no encuentra eventos**: prueba la URL de busqueda de SearXNG
  manualmente en el navegador (ver Parte 2, paso 8) para confirmar que trae
  resultados para tu categoria.
- **El panel da error al guardar un proyecto**: revisa que
  `SUPABASE_SERVICE_KEY` este bien configurada en Cloudflare Pages (no en
  GitHub — son configuraciones separadas, cada plataforma necesita la suya).
