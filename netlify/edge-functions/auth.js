// Edge Function de Netlify: protege TODO el sitio con la contrasena compartida.
// Corre antes de servir cualquier pagina (configurado en netlify.toml para
// aplicar a la ruta "/*").
//
// Variable de entorno necesaria (Netlify > Site settings > Environment variables):
//   SITE_PASSWORD  -> contrasena compartida del equipo

const COOKIE_NAME = "pmo_session";

export default async (request, context) => {
  const url = new URL(request.url);
  const password = Netlify.env.get("SITE_PASSWORD");

  // Login: recibe la contrasena por POST a /__login
  if (request.method === "POST" && url.pathname === "/__login") {
    const formData = await request.formData();
    const intento = formData.get("password") || "";

    if (intento === password) {
      const token = await sha256(password);
      return new Response(null, {
        status: 302,
        headers: {
          Location: "/",
          "Set-Cookie": `${COOKIE_NAME}=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000`,
        },
      });
    }
    return paginaLogin("Contrasena incorrecta, intenta de nuevo.");
  }

  // Deja pasar las llamadas a la API (esas se protegen por si mismas al estar
  // detras de esta misma edge function en las demas rutas; el usuario ya tuvo
  // que autenticarse para cargar la pagina que las llama).
  // Verifica cookie de sesion para el resto de rutas.
  const cookie = request.headers.get("Cookie") || "";
  const match = cookie.match(new RegExp(`${COOKIE_NAME}=([a-f0-9]+)`));
  const esperado = await sha256(password);

  if (match && match[1] === esperado) {
    return context.next(); // sesion valida, sigue al sitio normal
  }

  return paginaLogin();
};

async function sha256(texto) {
  const data = new TextEncoder().encode(texto || "");
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
  return new Response(html, {
    status: 401,
    headers: { "Content-Type": "text/html; charset=UTF-8" },
  });
}

export const config = {
  // Aplica a todo el sitio EXCEPTO a los assets estaticos que no deben pedir
  // login por si mismos y a las funciones de API (que ya estan protegidas
  // porque el usuario tuvo que autenticarse para llegar a ellas).
  path: "/*",
  excludedPath: ["/robots.txt", "/.netlify/*"],
};
