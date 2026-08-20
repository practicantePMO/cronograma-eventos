-- ============================================================
-- Limpieza de eventos automaticos de baja calidad ya guardados.
-- Ejecutar en Supabase > SQL Editor cuando quieras "empezar limpio"
-- con la nueva estrategia de filtrado.
--
-- Esto borra SOLO los eventos automaticos (fuente_tipo = 'automatico').
-- Tus eventos manuales (los que agrego el equipo desde el panel) NO se tocan.
-- ============================================================

-- Opcion A (recomendada la primera vez): borra TODOS los eventos automaticos,
-- para que el scraper los vuelva a poblar desde cero ya con el filtro nuevo.
delete from eventos where fuente_tipo = 'automatico';

-- Opcion B (mas quirurgica): si prefieres borrar solo los que vienen de
-- dominios que no son eventos (github, hacker news, etc.), comenta la linea
-- de arriba y descomenta estas:
-- delete from eventos
--  where fuente_tipo = 'automatico'
--    and (
--      url ilike '%github.com%'
--      or url ilike '%ycombinator.com%'
--      or url ilike '%reddit.com%'
--      or url ilike '%stackoverflow.com%'
--      or url ilike '%medium.com%'
--      or url ilike '%youtube.com%'
--    );

-- Opcion C (para el problema de "trae eventos que ya pasaron"): borra SOLO
-- los eventos automaticos cuya fecha_inicio ya paso. Usa esta si quieres
-- conservar los automaticos que SI son futuros y limpiar unicamente la
-- basura que quedo de un bug ya corregido (el scraper antes podia guardar la
-- fecha de publicacion del articulo del feed, que casi siempre es vieja, en
-- vez de descartarla). Comenta la Opcion A de arriba si usas esta.
-- delete from eventos
--  where fuente_tipo = 'automatico'
--    and fecha_inicio < now();