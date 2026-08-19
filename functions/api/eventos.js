// Endpoint: POST /api/eventos
// Permite crear eventos manuales desde admin.html sin exponer la llave secreta.

export async function onRequestPost(context) {
  const { request, env } = context;

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
      titulo,
      descripcion,
      fecha_inicio,
      categoria,
      url,
      proyecto_id,
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

async function sha256(texto) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
