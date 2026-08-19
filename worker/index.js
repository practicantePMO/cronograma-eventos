// Worker unico para el sitio del cronograma PMO.
//
// Cloudflare unifico Pages y Workers en un solo producto. Los proyectos
// nuevos ya no detectan una carpeta /functions automaticamente -- en su
// lugar, necesitan un Worker explicito como este, que:
//   1. Protege TODO el sitio con la contrasena compartida (SITE_PASSWORD).
//   2. Atiende las rutas /api/proyectos y /api/eventos (el panel PMO).
//   3. Deja pasar todo lo demas a los archivos estaticos (env.ASSETS).
//
// Variables/Secrets que debes configurar en Cloudflare (Settings > Variables
// and Secrets de este Worker):
//   SITE_PASSWORD          (Secret) -> contrasena compartida del equipo
//   SUPABASE_URL            (Variable)
//   SUPABASE_SERVICE_KEY   (Secret)

const COOKIE_NAME = "pmo_session";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Login
    if (request.method === "POST" && url.pathname === "/__login") {
      return handleLogin(request, env);
    }

    // Todo lo demas requiere sesion valida
    const autenticado = await estaAutenticado(request, env);
    if (!autenticado) {
      return paginaLogin();
    }

    // API del panel PMO
    if (url.pathname === "/api/proyectos") {
      if (request.method === "GET") return getProyectos(env);
      if (request.method === "POST") return postProyecto(request, env);
    }
    if (url.pathname === "/api/eventos" && request.method === "POST") {
      return postEvento(request, env);
    }

    // Cualquier otra ruta -> archivos estaticos (index.html, admin.html, etc.)
    return env.ASSETS.fetch(request);
  },
};

// ---------- Autenticacion ----------

async function handleLogin(request, env) {
  const formData = await request.formData();
  const intento = formData.get("password") || "";

  if (intento === env.SITE_PASSWORD) {
    const token = await sha256(env.SITE_PASSWORD);
    const headers = new Headers({ Location: "/" });
    headers.append(
      "Set-Cookie",
      `${COOKIE_NAME}=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000`
    );
    return new Response(null, { status: 302, headers });
  }
  return paginaLogin("Contrasena incorrecta, intenta de nuevo.");
}

async function estaAutenticado(request, env) {
  const cookie = request.headers.get("Cookie") || "";
  const match = cookie.match(new RegExp(`${COOKIE_NAME}=([a-f0-9]+)`));
  if (!match) return false;
  const esperado = await sha256(env.SITE_PASSWORD);
  return match[1] === esperado;
}

async function sha256(texto) {
  const data = new TextEncoder().encode(texto);
  const buffer = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(buffer)].map(b => b.toString(16).padStart(2, "0")).join("");
}

function paginaLogin(mensajeError) {
  const html = `<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Acceso - Cronograma PMO</title>
<style>
  body { font-family: -apple-system, sans-serif; background:#f6f5f2; display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }
  .caja { background:white; padding:32px; border-radius:12px; border:1px solid #d8d6cd; width:100%; max-width:340px; }
  h1 { font-size:18px; margin:0 0 16px; }
  input { width:100%; padding:10px; margin-bottom:12px; border:1px solid #d8d6cd; border-radius:8px; box-sizing:border-box; }
  button { width:100%; padding:10px; background:#185fa5; color:white; border:none; border-radius:8px; cursor:pointer; }
  .error { color:#993c1d; font-size:13px; margin-bottom:12px; }
</style></head>
<body>
  <form class="caja" method="POST" action="/__login">
    <h1>Cronograma PMO</h1>
    ${mensajeError ? `<div class="error">${mensajeError}</div>` : ""}
    <input type="password" name="password" placeholder="Contrasena del equipo" required autofocus />
    <button type="submit">Entrar</button>
  </form>
</body></html>`;
  return new Response(html, { headers: { "Content-Type": "text/html; charset=UTF-8" } });
}

// ---------- API: proyectos ----------

async function getProyectos(env) {
  const resp = await fetch(
    `${env.SUPABASE_URL}/rest/v1/proyectos?select=*&order=creado_en.desc`,
    {
      headers: {
        apikey: env.SUPABASE_SERVICE_KEY,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}`,
      },
    }
  );
  const data = await resp.json();
  return json(data, resp.status);
}

async function postProyecto(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "JSON invalido" }, 400);
  }

  const nombre = (body.nombre || "").trim();
  const codigo = (body.codigo || "").trim();
  const categoriasTexto = (body.categorias || "").trim();

  if (!nombre || !codigo || !categoriasTexto) {
    return json({ error: "Faltan campos: nombre, codigo y categorias son obligatorios" }, 400);
  }

  const categorias = categoriasTexto
    .split(",")
    .map(c => c.trim().toLowerCase())
    .filter(Boolean);

  const resp = await fetch(`${env.SUPABASE_URL}/rest/v1/proyectos`, {
    method: "POST",
    headers: {
      apikey: env.SUPABASE_SERVICE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify({ nombre, codigo, categorias, estado: "activo" }),
  });

  const data = await resp.json();
  if (!resp.ok) {
    return json({ error: data.message || "Error al crear el proyecto en Supabase" }, 500);
  }
  return json({ ok: true, proyecto: data[0] });
}

// ---------- API: eventos manuales ----------

async function postEvento(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "JSON invalido" }, 400);
  }

  const titulo = (body.titulo || "").trim();
  const fecha_inicio = body.fecha_inicio;
  const proyecto_id = body.proyecto_id || null;
  const categoria = (body.categoria || "").trim() || null;
  const descripcion = (body.descripcion || "").trim() || null;
  const url = (body.url || "").trim() || null;

  if (!titulo || !fecha_inicio) {
    return json({ error: "Faltan campos: titulo y fecha_inicio son obligatorios" }, 400);
  }

  const hash_unico = await sha256(`${titulo.toLowerCase()}|${(url || "").toLowerCase()}|${fecha_inicio}`);

  const resp = await fetch(`${env.SUPABASE_URL}/rest/v1/eventos`, {
    method: "POST",
    headers: {
      apikey: env.SUPABASE_SERVICE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation,resolution=ignore-duplicates",
    },
    body: JSON.stringify({
      titulo, descripcion, fecha_inicio, categoria, url, proyecto_id,
      fuente_tipo: "manual",
      fuente_nombre: "Agregado por el equipo PMO",
      hash_unico,
    }),
  });

  const data = await resp.json();
  if (!resp.ok) {
    return json({ error: data.message || "Error al crear el evento" }, 500);
  }
  return json({ ok: true, evento: data[0] });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
