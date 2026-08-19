-- ============================================================
-- Esquema de base de datos para el cronograma del PMO
-- Ejecutar esto en Supabase > SQL Editor > New query > Run
-- ============================================================

-- Tabla de proyectos
create table if not exists proyectos (
  id uuid primary key default gen_random_uuid(),
  codigo text not null unique,          -- ej. "AT-04" (nombre corto/codigo interno)
  nombre text not null,                 -- nombre completo del proyecto
  categorias text[] not null default '{}', -- ej. {"automatizacion","manufactura"}
  estado text not null default 'activo', -- activo, pausado, cerrado
  creado_en timestamptz not null default now()
);

-- Tabla de eventos (reuniones, conferencias, publicaciones encontradas)
create table if not exists eventos (
  id uuid primary key default gen_random_uuid(),
  proyecto_id uuid references proyectos(id) on delete set null,
  titulo text not null,
  descripcion text,
  fecha_inicio timestamptz not null,
  fecha_fin timestamptz,
  categoria text,                        -- tema principal detectado
  fuente_tipo text not null default 'automatico', -- 'automatico' o 'manual'
  fuente_nombre text,                    -- ej. "TechCrunch", "Reunion interna"
  url text,
  hash_unico text unique,                -- para evitar duplicados (titulo+fecha+url hasheado)
  creado_en timestamptz not null default now()
);

-- Tabla de fuentes verificadas que el scraper puede consultar
create table if not exists fuentes_verificadas (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  tipo text not null,                    -- 'rss'
  url text not null,
  categorias text[] not null default '{}', -- a que temas aplica esta fuente
  activo boolean not null default true
);

-- Indices utiles
create index if not exists idx_eventos_fecha on eventos (fecha_inicio);
create index if not exists idx_eventos_proyecto on eventos (proyecto_id);
create index if not exists idx_eventos_categoria on eventos (categoria);

-- ============================================================
-- Seguridad: Row Level Security (RLS)
-- Esto permite que el sitio LEA los datos con la llave publica (anon)
-- pero NADIE pueda escribir/borrar con esa misma llave.
-- Solo tu scraper (con la llave "service_role", secreta) podra escribir.
-- ============================================================

alter table proyectos enable row level security;
alter table eventos enable row level security;
alter table fuentes_verificadas enable row level security;

create policy "lectura publica proyectos" on proyectos
  for select using (true);

create policy "lectura publica eventos" on eventos
  for select using (true);

create policy "lectura publica fuentes" on fuentes_verificadas
  for select using (true);

-- No se crean policies de insert/update/delete para el rol "anon":
-- esto bloquea automaticamente cualquier escritura desde el sitio publico.

-- ============================================================
-- Datos de ejemplo (puedes borrarlos despues)
-- ============================================================

insert into proyectos (codigo, nombre, categorias) values
  ('AT-04', 'Automatizacion Planta Norte', array['automatizacion','manufactura','rpa']),
  ('TD-01', 'Transformacion Digital Comercial', array['transformacion digital','ia','crm'])
on conflict (codigo) do nothing;

insert into fuentes_verificadas (nombre, tipo, url, categorias) values
  ('Google Alerts - Automatizacion (ejemplo)', 'rss', 'https://www.google.com/alerts/feeds/TU_ID_AQUI/TU_FEED_AQUI', array['automatizacion']),
  ('Hacker News RSS (ejemplo)', 'rss', 'https://hnrss.org/newest?q=automation', array['automatizacion','ia'])
on conflict do nothing;
