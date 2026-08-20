"""
Recolector automatizado de eventos para el cronograma del PMO.

Que hace (dos metodos, ambos corren en cada ejecucion):

METODO 1 - RSS (opcional, para fuentes que tu ya conoces y quieres seguir fijas):
  Lee la tabla fuentes_verificadas y procesa cada feed RSS.

METODO 2 - Busqueda automatica por categoria (el que resuelve "cero trabajo manual"):
  1. Lee las categorias de TODOS los proyectos activos en la tabla "proyectos".
  2. Por cada categoria, busca en tu propia instancia de SearXNG (motor de
     busqueda open source, auto-hospedado por ti en Render, sin cuentas de
     terceros ni limites diarios de cuota) eventos/bootcamps/webinars sobre ese tema.
  3. Filtra los resultados que realmente parecen eventos (por palabras clave).
  4. Evita duplicados usando un hash de titulo+url.
  5. Inserta las entradas nuevas en la tabla "eventos" de Supabase.

Asi, cuando alguien del equipo PMO agrega un proyecto con una categoria nueva desde
el panel (admin.html), NO hace falta que nadie configure una fuente RSS a mano ni
crear ninguna cuenta: el scraper la detecta solo en su siguiente corrida.

Requiere estas variables de entorno (se configuran como "Secrets" en GitHub
Actions, NUNCA se escriben directo en este archivo):
  SUPABASE_URL          -> ej. https://xxxxx.supabase.co
  SUPABASE_SERVICE_KEY  -> la llave secreta (antes llamada "service_role")
  SEARXNG_URL           -> ej. https://tu-searxng.onrender.com (tu instancia propia)
"""

import os
import hashlib
import sys
from datetime import datetime, timezone

import re

import feedparser
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SEARXNG_URL = (os.environ.get("SEARXNG_URL") or "").rstrip("/")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: faltan las variables de entorno SUPABASE_URL o SUPABASE_SERVICE_KEY")
    sys.exit(1)

if not SEARXNG_URL:
    print("AVISO: falta SEARXNG_URL -> se omite la busqueda automatica por categoria")

# Palabras que deben aparecer en el titulo o descripcion para considerar que
# un resultado de busqueda SI es un evento/formacion real (y no un articulo
# generico ni una landing de venta de servicios).
PALABRAS_EVENTO = [
    "webinar", "webinars", "conferencia", "conference", "congreso",
    "seminario", "seminar", "summit", "simposio", "symposium",
    "jornada", "foro", "forum", "workshop", "taller online", "taller virtual",
    "taller presencial", "evento virtual", "evento online", "evento presencial",
    "sesion online", "sesión online", "live session", "online event",
    "virtual event", "masterclass",
    # Formacion (lo que mas te interesa: cursos y bootcamps organizados)
    "bootcamp", "curso online", "curso virtual", "curso gratuito",
    "curso gratis", "capacitacion", "capacitación", "certificacion",
    "certificación", "diplomado", "programa de formacion",
    "programa de formación", "hackathon", "meetup",
]

# Palabras que, si aparecen, suben la prioridad del evento por ser gratuito
# (no se usan para descartar, solo para etiquetar "es_gratuito").
PALABRAS_GRATIS = [
    "gratis", "gratuito", "gratuita", "free", "sin costo", "sin costo alguno",
    "no cost", "cupo gratuito", "acceso gratuito",
]

# Dominios que casi nunca son eventos reales (repos de codigo, agregadores de
# noticias, tiendas, etc.). Si un resultado viene de aqui, se descarta antes
# de mirar nada mas.
DOMINIOS_EXCLUIDOS = [
    "github.com", "gitlab.com", "news.ycombinator.com", "reddit.com",
    "stackoverflow.com", "medium.com", "youtube.com", "amazon.",
    "wikipedia.org", "facebook.com", "twitter.com", "x.com",
    "linkedin.com/pulse", "pinterest.", "instagram.com",
]

# Sufijos de dominio institucionales que se aceptan aunque el dominio exacto
# no este en la tabla "dominios_verificados" (universidades, gobierno, ONGs).
SUFIJOS_INSTITUCIONALES = (
    ".edu", ".edu.co", ".edu.mx", ".edu.ar", ".edu.pe", ".edu.cl",
    ".gob.co", ".gob.mx", ".gob.pe", ".gob.ar", ".gov.co", ".gov", ".gob",
    ".org",
)

# Para que un resultado de busqueda cuente como evento, ademas de traer una
# palabra-evento, exigimos que tenga alguna senal de fecha o de accion tipica
# de evento (registrarse, agendar, etc.). Esto sube mucho la calidad.
SENALES_FECHA = [
    "2026", "2027", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    "register", "registro", "regístrate", "regis", "agenda", "agéndate",
    "inscrib", "proximamente", "próximamente", "en vivo", "live",
]

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


def obtener_dominios_verificados():
    """
    Trae la lista blanca de dominios verificados (tabla dominios_verificados).
    Si la tabla no existe todavia (no se ha corrido la migracion), devuelve
    una lista vacia y avisa, en vez de reventar el scraper.
    """
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/dominios_verificados",
            headers=HEADERS,
            params={"activo": "eq.true", "select": "dominio"},
            timeout=30,
        )
        resp.raise_for_status()
        return [d["dominio"].lower() for d in resp.json()]
    except Exception as exc:
        print(f"AVISO: no se pudo leer dominios_verificados ({exc}). "
              f"Corre supabase/migracion_dominios_verificados.sql y vuelve a intentar.")
        return []


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

        # Descartar si el texto menciona una fecha explicita que ya paso.
        if fecha_ya_paso(f"{titulo} {resumen}".lower()):
            continue

        # Fecha para el calendario: preferimos una fecha detectada en el texto;
        # si no hay, usamos la fecha de publicacion del feed; si tampoco, hoy.
        fecha_detectada = extraer_fecha_del_texto(f"{titulo} {resumen}".lower())
        if fecha_detectada:
            fecha = fecha_detectada
        elif getattr(entry, "published_parsed", None):
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
            "es_gratuito": es_gratuito(titulo, resumen),
        }
        insertar_evento(evento)


# Meses en espanol e ingles para detectar fechas escritas en el texto.
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "jun": 6, "jul": 7, "ago": 8,
    "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

# Frases tipicas de una landing page de empresa (no de un evento puntual).
# Se mantienen como señal EXTRA de descarte, pero ya NO son la defensa
# principal (ver DOMINIOS_EXCLUIDOS y el filtro de dominio verificado en
# parece_evento): una empresa puede vender sus servicios sin usar ninguna
# de estas frases exactas, por eso ahora el filtro fuerte es por dominio.
SENALES_PAGINA_EMPRESA = [
    "nuestros servicios", "nuestros productos", "quienes somos",
    "sobre nosotros", "about us", "our services", "our products",
    "solicita una demo", "request a demo", "contactanos", "contact us",
    "planes y precios", "pricing", "solucion empresarial",
    "plataforma lider", "leading platform", "software de",
    "agencia de", "consultoria en", "consultora especializada en",
]


def dominio_de_url(url):
    m = re.search(r"https?://([^/]+)", url.lower())
    if not m:
        return ""
    return m.group(1).replace("www.", "")


def dominio_verificado(url, dominios_permitidos):
    """
    True si el dominio del resultado esta en la lista blanca de
    dominios_verificados, o si termina en un sufijo institucional
    (.edu, .gob, .gov, .org). Este es el filtro fuerte contra paginas
    de empresas: si el sitio no esta aprobado por ti, no entra, sin
    importar que tan "de evento" suene el texto.
    """
    dominio = dominio_de_url(url)
    if not dominio:
        return False
    if dominio.endswith(SUFIJOS_INSTITUCIONALES):
        return True
    return any(dominio == d or dominio.endswith("." + d) for d in dominios_permitidos)


def es_gratuito(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    return any(palabra in texto for palabra in PALABRAS_GRATIS)


def extraer_fecha_del_texto(texto):
    """
    Intenta encontrar una fecha en el texto (ej. "15 de marzo de 2026" o
    "March 15, 2026"). Devuelve un datetime con dia 1 si solo encuentra
    mes+ano, o None si no encuentra nada confiable.
    """
    t = texto.lower()

    # Patron: "15 de marzo de 2026" / "15 de marzo 2026"
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:de\s+)?(\d{4})", t)
    if m and m.group(2) in MESES:
        try:
            return datetime(int(m.group(3)), MESES[m.group(2)], int(m.group(1)), tzinfo=timezone.utc)
        except ValueError:
            pass

    # Patron: "march 15, 2026" / "march 2026"
    m = re.search(r"([a-z]+)\s+(\d{1,2})?,?\s*(\d{4})", t)
    if m and m.group(1) in MESES:
        try:
            dia = int(m.group(2)) if m.group(2) else 1
            return datetime(int(m.group(3)), MESES[m.group(1)], dia, tzinfo=timezone.utc)
        except ValueError:
            pass

    return None  # no se encontro fecha confiable


def fecha_ya_paso(texto):
    """True solo si detectamos una fecha y esa fecha ya paso."""
    fecha = extraer_fecha_del_texto(texto)
    if fecha is None:
        return False  # sin fecha detectable -> NO lo descartamos (segun tu eleccion)
    # Damos un margen de 1 dia por zonas horarias.
    return fecha.date() < datetime.now(timezone.utc).date()


def parece_pagina_de_empresa(titulo, descripcion):
    texto = f"{titulo} {descripcion}".lower()
    return any(frase in texto for frase in SENALES_PAGINA_EMPRESA)


def parece_evento(titulo, descripcion, url, dominios_permitidos):
    texto = f"{titulo} {descripcion}".lower()
    url_lower = url.lower()

    # 1. Descartar dominios que casi nunca son eventos.
    if any(dom in url_lower for dom in DOMINIOS_EXCLUIDOS):
        return False

    # 2. FILTRO FUERTE: el dominio debe estar verificado por ti (tabla
    #    dominios_verificados) o ser institucional (.edu/.gob/.gov/.org).
    #    Esto es lo que evita que se cuelen paginas de empresas que venden
    #    cursos/servicios: si el sitio no esta en tu lista aprobada, no pasa,
    #    sin importar como este redactado el texto.
    if not dominio_verificado(url, dominios_permitidos):
        return False

    # 3. Debe traer al menos una palabra clara de evento/curso/bootcamp.
    if not any(palabra in texto for palabra in PALABRAS_EVENTO):
        return False

    # 4. Ademas debe traer alguna senal de fecha o de accion de evento.
    #    Esto filtra paginas genericas que solo mencionan la palabra "webinar"
    #    de pasada.
    if not any(senal in texto for senal in SENALES_FECHA):
        return False

    # 5. Descartar si ademas parece una landing page de empresa (senal extra,
    #    por si un sitio verificado tiene tambien paginas de venta mezcladas).
    if parece_pagina_de_empresa(titulo, descripcion):
        return False

    # 6. Descartar si detectamos una fecha y esa fecha YA paso.
    #    (Si no hay fecha detectable, se deja pasar, segun tu preferencia.)
    if fecha_ya_paso(texto):
        return False

    return True


def buscar_por_categoria(categoria, proyecto_id, dominios_permitidos):
    """
    Busca eventos, cursos y bootcamps sobre una categoria usando tu propia
    instancia de SearXNG (auto-hospedada, JSON, sin cuenta ni limite diario
    de cuota).

    Estrategia con calidad sobre cantidad: consultas dirigidas a cursos y
    bootcamps (con enfasis en gratuitos), organizadas por sitio via "site:"
    cuando hay dominios verificados, + filtro estricto (parece_evento), que
    exige que el dominio este en tu lista blanca.
    """
    if not SEARXNG_URL:
        return

    consultas_base = [
        f"bootcamp {categoria} 2026 gratuito inscripcion",
        f"curso online {categoria} 2026 gratis registro",
        f"webinar {categoria} 2026 registro",
        f"conferencia online {categoria} 2026",
    ]

    # Si ya tenemos dominios verificados, dirigimos las busquedas a esos
    # sitios especificos con "site:" -> resultados de mucha mas calidad,
    # porque le pedimos al buscador que solo mire sitios que tu aprobaste.
    consultas = list(consultas_base)
    for dominio in dominios_permitidos[:6]:  # limite de seguridad por corrida
        consultas.append(f"site:{dominio} {categoria} bootcamp OR curso OR webinar 2026")

    for consulta in consultas:
        try:
            resp = requests.get(
                f"{SEARXNG_URL}/search",
                params={"q": consulta, "format": "json"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  ! Error buscando '{consulta}': {exc}")
            continue

        for item in data.get("results", [])[:8]:  # limite por consulta
            titulo = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            descripcion = (item.get("content") or "")[:500]

            if not titulo or not url:
                continue
            if not parece_evento(titulo, descripcion, url, dominios_permitidos):
                continue  # descarta lo que no parece un evento/curso real de un sitio verificado

            # Si detectamos una fecha real en el texto, la usamos; si no,
            # usamos "hoy" para que al menos aparezca en el calendario.
            fecha_detectada = extraer_fecha_del_texto(f"{titulo} {descripcion}".lower())
            fecha_evento = (fecha_detectada or datetime.now(timezone.utc)).isoformat()

            evento = {
                "titulo": titulo,
                "descripcion": descripcion,
                "fecha_inicio": fecha_evento,
                "categoria": categoria,
                "fuente_tipo": "automatico",
                "fuente_nombre": "Busqueda automatica (SearXNG)",
                "url": url,
                "proyecto_id": proyecto_id,
                "hash_unico": calcular_hash(titulo, url),
                "es_gratuito": es_gratuito(titulo, descripcion),
            }
            insertar_evento(evento)


def procesar_categorias_automaticas(proyectos, dominios_permitidos):
    categorias_vistas = set()
    for p in proyectos:
        if p.get("estado") != "activo":
            continue
        for categoria in p.get("categorias", []):
            clave = categoria.lower()
            if clave in categorias_vistas:
                continue  # ya se busco esta categoria en esta corrida
            categorias_vistas.add(clave)
            print(f"Buscando automaticamente eventos para categoria: {categoria}")
            try:
                buscar_por_categoria(categoria, p["id"], dominios_permitidos)
            except Exception as exc:
                print(f"  ! Error en categoria '{categoria}': {exc}")


def main():
    fuentes = obtener_fuentes()
    proyectos = obtener_proyectos()
    dominios_permitidos = obtener_dominios_verificados()
    print(f"{len(fuentes)} fuente(s) RSS activa(s), {len(proyectos)} proyecto(s) cargado(s), "
          f"{len(dominios_permitidos)} dominio(s) verificado(s).\n")

    for fuente in fuentes:
        try:
            procesar_fuente(fuente, proyectos)
        except Exception as exc:
            print(f"  ! Error procesando {fuente['nombre']}: {exc}")

    print()
    procesar_categorias_automaticas(proyectos, dominios_permitidos)

    print("\nListo.")


if __name__ == "__main__":
    main()
