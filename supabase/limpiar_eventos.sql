-- ============================================================
-- Limpieza de eventos automaticos de baja calidad ya guardados.
-- Ejecutar en Supabase > SQL Editor cuando quieras "empezar limpio"
-- con la nueva estrategia de filtrado.
--
-- Esto borra SOLO los eventos automaticos (fuente_tipo = 'automatico').
-- Tus eventos manuales (los que agrego el equipo desde el panel) NO se tocan.
-- ============================================================

-- Opcion A (recomendada): borra TODOS los eventos automaticos, para que el
-- scraper los vuelva a poblar desde cero ya con el filtro nuevo.
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
