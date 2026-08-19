// Netlify Function: /api/proyectos
// GET  -> lista los proyectos
// POST -> crea un proyecto nuevo (desde el panel admin.html)
//
// Variables de entorno necesarias (Netlify > Environment variables):
//   SUPABASE_URL
//   SUPABASE_SERVICE_KEY

export default async (request) => {
  const SUPABASE_URL = Netlify.env.get("SUPABASE_URL");
  const SUPABASE_SERVICE_KEY = Netlify.env.get("SUPABASE_SERVICE_KEY");

  const headers = {
    apikey: SUPABASE_SERVICE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
  };

  if (request.method === "GET") {
    const resp = await fetch(
      `${SUPABASE_URL}/rest/v1/proyectos?select=*&order=creado_en.desc`,
      { headers }
    );
    const data = await resp.json();
    return json(data, resp.status);
  }

  if (request.method === "POST") {
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

    const resp = await fetch(`${SUPABASE_URL}/rest/v1/proyectos`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json", Prefer: "return=representation" },
      body: JSON.stringify({ nombre, codigo, categorias, estado: "activo" }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      return json({ error: data.message || "Error al crear el proyecto en Supabase" }, 500);
    }
    return json({ ok: true, proyecto: data[0] });
  }

  return json({ error: "Metodo no permitido" }, 405);
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export const config = { path: "/api/proyectos" };
