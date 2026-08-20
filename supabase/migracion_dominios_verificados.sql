-- ============================================================
-- Migracion: filtrado por dominios verificados + marca de "gratuito"
-- Ejecutar en Supabase > SQL Editor > New query > Run
--
-- Por que este cambio:
-- El filtro anterior descartaba resultados buscando frases tipicas de
-- landing pages de empresas ("nuestros servicios", "about us", etc.).
-- Eso es fragil: cualquier pagina que NO use esas frases exactas se cuela,
-- que es justo el problema que reportaste (paginas de empresas ofreciendo
-- servicios en vez de eventos/cursos/bootcamps reales).
--
-- El cambio de fondo es invertir la logica: en vez de "lista negra de
-- frases", usamos "lista blanca de dominios verificados". El scraper YA
-- SOLO acepta resultados que vengan de un dominio en esta tabla (o de un
-- TLD institucional .edu/.gob/.gov/.org), sin importar que tan bien
-- redactada este la pagina. Tu controlas exactamente que sitios entran,
-- igual que ya controlas "fuentes_verificadas" para RSS.
-- ============================================================

create table if not exists dominios_verificados (
  id uuid primary key default gen_random_uuid(),
  dominio text not null unique,      -- ej. "eventbrite.com" (sin http:// ni www.)
  nombre text not null,              -- ej. "Eventbrite"
  tipo text not null default 'plataforma_eventos', -- plataforma_eventos, universidad, gobierno, comunidad_tech
  activo boolean not null default true
);

create index if not exists idx_dominios_verificados_activo on dominios_verificados (activo);

alter table dominios_verificados enable row level security;

create policy "lectura publica dominios verificados" on dominios_verificados
  for select using (true);

-- Marca si el evento parece gratuito (para resaltarlo en el sitio, NO para
-- descartar los que son pagos: tu preferencia es "de preferencia gratis",
-- no "solo gratis").
alter table eventos add column if not exists es_gratuito boolean not null default false;
create index if not exists idx_eventos_gratuito on eventos (es_gratuito);

-- ============================================================
-- Semilla inicial de dominios verificados.
-- Puedes agregar/quitar los que quieras desde el Table Editor de Supabase
-- o desde una version futura del panel admin.html.
-- ============================================================

insert into dominios_verificados (dominio, nombre, tipo) values
  -- Plataformas de eventos/formacion reconocidas
  ('eventbrite.com', 'Eventbrite', 'plataforma_eventos'),
  ('meetup.com', 'Meetup', 'plataforma_eventos'),
  ('platzi.com', 'Platzi', 'plataforma_eventos'),
  ('coursera.org', 'Coursera', 'plataforma_eventos'),
  ('edx.org', 'edX', 'plataforma_eventos'),
  ('freecodecamp.org', 'freeCodeCamp', 'comunidad_tech'),
  ('devtalles.com', 'DevTalles', 'comunidad_tech'),
  ('talently.tech', 'Talently', 'plataforma_eventos'),
  ('hackathon.com', 'Hackathon.com', 'plataforma_eventos'),
  ('devpost.com', 'Devpost', 'plataforma_eventos'),
  -- Big tech: programas de eventos/capacitacion gratuitos oficiales
  ('cloud.google.com', 'Google Cloud (eventos)', 'plataforma_eventos'),
  ('developers.google.com', 'Google Developers', 'plataforma_eventos'),
  ('reactor.microsoft.com', 'Microsoft Reactor', 'plataforma_eventos'),
  ('aws.amazon.com', 'AWS Events', 'plataforma_eventos'),
  ('ibm.com', 'IBM Events/SkillsBuild', 'plataforma_eventos'),
  -- Colombia / LatAm: gobierno y formacion oficial
  ('sena.edu.co', 'SENA', 'gobierno'),
  ('mintic.gov.co', 'MinTIC', 'gobierno'),
  ('colombiafintech.co', 'Colombia Fintech', 'comunidad_tech')
on conflict (dominio) do nothing;

-- NOTA: ademas de esta lista, el scraper acepta automaticamente cualquier
-- dominio que termine en .edu, .edu.co (u otro pais), .gob, .gob.co, .gov,
-- .gov.co u .org, porque ese tipo de sitios institucionales rara vez
-- publican paginas de venta de servicios.
