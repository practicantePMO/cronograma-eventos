"""
Recolector automatizado de eventos para el cronograma del PMO.

Que hace:
1. Lee la lista de fuentes verificadas desde Supabase (tabla fuentes_verificadas).
2. Descarga cada feed RSS.
3. Filtra las entradas segun las categorias de cada fuente.
4. Evita duplicados usando un hash de titulo+url.
5. Inserta las entradas nuevas en la tabla "eventos" de Supabase.

Requiere dos variables de entorno (se configuran como "Secrets" en GitHub Actions,
NUNCA se escriben directo en este archivo):
  SUPABASE_URL          -> ej. https://xxxxx.supabase.co
  SUPABASE_SERVICE_KEY  -> la llave "service_role" (secreta, con permiso de escritura)
"""

import os
import hashlib
import sys
from datetime import datetime, timezone

import feedparser
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: faltan las variables de entorno SUPABASE_URL o SUPABASE_SERVICE_KEY")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}


def obtener_fuentes():
    """Trae las fuentes verificadas activas desde Supabase."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/fuentes_verificadas",
        headers=HEADERS,
        params={"activo": "eq.true", "select": "*"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def obtener_proyectos():
    """Trae los proyectos para poder asociar eventos por categoria."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/proyectos",
        headers=HEADERS,
        params={"select": "id,categorias,estado"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def calcular_hash(titulo, url):
    base = f"{titulo.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def proyecto_para_categoria(categoria, proyectos):
    """Si alguna categoria de un proyecto coincide, devuelve su id."""
    if not categoria:
        return None
    for p in proyectos:
        if p.get("estado") == "activo" and categoria.lower() in [
            c.lower() for c in p.get("categorias", [])
        ]:
            return p["id"]
    return None


def insertar_evento(evento):
    """Inserta un evento; si el hash ya existe, Supabase lo ignora (on_conflict)."""
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/eventos",
        headers={**HEADERS, "Prefer": "resolution=ignore-duplicates"},
        params={"on_conflict": "hash_unico"},
        json=evento,
        timeout=30,
    )
    if resp.status_code not in (200, 201, 204):
        print(f"  ! Error insertando '{evento['titulo'][:50]}': {resp.status_code} {resp.text[:200]}")
    else:
        print(f"  + Guardado: {evento['titulo'][:70]}")


def procesar_fuente(fuente, proyectos):
    print(f"Leyendo fuente: {fuente['nombre']} ({fuente['url']})")
    feed = feedparser.parse(fuente["url"])

    if feed.bozo and not feed.entries:
        print(f"  ! No se pudo leer el feed (revisa la URL): {fuente['url']}")
        return

    for entry in feed.entries[:30]:  # limite de seguridad por corrida
        titulo = entry.get("title", "").strip()
        url = entry.get("link", "").strip()
        if not titulo or not url:
            continue

        resumen = entry.get("summary", "")[:500]

        # Fecha: usa published_parsed si existe, si no usa ahora mismo
        if getattr(entry, "published_parsed", None):
            fecha = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        else:
            fecha = datetime.now(timezone.utc)

        categoria = fuente["categorias"][0] if fuente.get("categorias") else None
        proyecto_id = proyecto_para_categoria(categoria, proyectos)

        evento = {
            "titulo": titulo,
            "descripcion": resumen,
            "fecha_inicio": fecha.isoformat(),
            "categoria": categoria,
            "fuente_tipo": "automatico",
            "fuente_nombre": fuente["nombre"],
            "url": url,
            "proyecto_id": proyecto_id,
            "hash_unico": calcular_hash(titulo, url),
        }
        insertar_evento(evento)


def main():
    fuentes = obtener_fuentes()
    proyectos = obtener_proyectos()
    print(f"{len(fuentes)} fuente(s) activa(s), {len(proyectos)} proyecto(s) cargado(s).\n")

    for fuente in fuentes:
        try:
            procesar_fuente(fuente, proyectos)
        except Exception as exc:
            print(f"  ! Error procesando {fuente['nombre']}: {exc}")

    print("\nListo.")


if __name__ == "__main__":
    main()
