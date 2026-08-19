// Cloudflare Pages Function: protege TODO el sitio con una sola contraseña.
// No requiere cuentas individuales. Se ejecuta antes de servir cualquier pagina.
//
// Configura la variable de entorno SITE_PASSWORD en:
// Cloudflare Pages > tu proyecto > Settings > Environment variables

const COOKIE_NAME = "pmo_session";

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);

  // Login: si mandan la contraseña por POST a /__login
  if (request.method === "POST" && url.pathname === "/__login") {
    const formData = await request.formData();
    const intento = formData.get("password") || "";

    if (intento === env.SITE_PASSWORD) {
      const token = await hash(env.SITE_PASSWORD);
      const headers = new Headers({ Location: "/" });
      headers.append(
        "Set-Cookie",
        `${COOKIE_NAME}=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000`
      );
      return new Response(null, { status: 302, headers });
    }
    return paginaLogin("Contrasena incorrecta, intenta de nuevo.");
  }

  // Verifica cookie de sesion
  const cookie = request.headers.get("Cookie") || "";
  const match = cookie.match(new RegExp(`${COOKIE_NAME}=([a-f0-9]+)`));
  const esperado = await hash(env.SITE_PASSWORD);

  if (match && match[1] === esperado) {
    return next(); // sesion valida, deja pasar a la pagina pedida
  }

  return paginaLogin();
}

async function hash(texto) {
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
