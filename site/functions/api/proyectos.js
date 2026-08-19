// Endpoint: POST /api/proyectos
// Permite al panel (admin.html) crear proyectos SIN exponer la llave secreta
// de Supabase al navegador. Esta funcion corre en el servidor de Cloudflare.
//
// Requiere las variables de entorno (Cloudflare Pages > Settings > Environment
// variables), ademas de SITE_PASSWORD que ya configuraste:
//   SUPABASE_URL
//   SUPABASE_SERVICE_KEY

export async function onRequestPost(context) {
  const { request, env } = context;

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

  // "automatizacion, rpa" -> ["automatizacion","rpa"]
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
    body: JSON.stringify({
      nombre,
      codigo,
      categorias,
      estado: "activo",
    }),
  });

  const data = await resp.json();

  if (!resp.ok) {
    return json({ error: data.message || "Error al crear el proyecto en Supabase" }, 500);
  }

  return json({ ok: true, proyecto: data[0] });
}

// GET /api/proyectos -> lista los proyectos existentes (para mostrarlos en el panel)
export async function onRequestGet(context) {
  const { env } = context;
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

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
