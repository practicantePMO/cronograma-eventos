// Netlify Function: /api/eventos
// POST -> crea un evento manual (desde el panel admin.html)
//
// Variables de entorno necesarias:
//   SUPABASE_URL
//   SUPABASE_SERVICE_KEY

export default async (request) => {
  if (request.method !== "POST") {
    return json({ error: "Metodo no permitido" }, 405);
  }

  const SUPABASE_URL = Netlify.env.get("SUPABASE_URL");
  const SUPABASE_SERVICE_KEY = Netlify.env.get("SUPABASE_SERVICE_KEY");

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
  const es_gratuito = Boolean(body.es_gratuito);

  if (!titulo || !fecha_inicio) {
    return json({ error: "Faltan campos: titulo y fecha_inicio son obligatorios" }, 400);
  }

  const hash_unico = await sha256(`${titulo.toLowerCase()}|${(url || "").toLowerCase()}|${fecha_inicio}`);

  const resp = await fetch(`${SUPABASE_URL}/rest/v1/eventos`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_SERVICE_KEY,
      Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation,resolution=ignore-duplicates",
    },
    body: JSON.stringify({
      titulo, descripcion, fecha_inicio, categoria, url, proyecto_id, es_gratuito,
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
};

async function sha256(texto) {
  const buffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return [...new Uint8Array(buffer)].map(b => b.toString(16).padStart(2, "0")).join("");
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export const config = { path: "/api/eventos" };
