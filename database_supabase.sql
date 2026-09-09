-- ============================================================
-- Script para SUPABASE (PostgreSQL)
-- Proyecto: deteccion-placas (modo demo de portafolio)
--
-- Flujo: sin registro ni login. Cada visitante se identifica
-- automáticamente con un session_id generado por el navegador;
-- solo ve las placas e imágenes que él mismo subió.
--
-- Cómo ejecutarlo:
--   Dashboard de Supabase -> SQL Editor -> pegar todo -> Run
-- ============================================================

-- ------------------------------------------------------------
-- ⚠️ Si ya habías ejecutado la versión anterior del script
-- (con username/password), descomenta estas dos líneas para
-- eliminar las tablas viejas antes de crear las nuevas.
-- Esto BORRA todos los datos existentes.
-- ------------------------------------------------------------
-- DROP TABLE IF EXISTS detecciones CASCADE;
-- DROP TABLE IF EXISTS usuarios CASCADE;

-- ------------------------------------------------------------
-- Tabla de usuarios (sesiones de invitado)
-- Sin username ni password: el navegador del visitante genera
-- un UUID (p. ej. con crypto.randomUUID()) y la app lo registra
-- aquí la primera vez que lo ve. UNIQUE ya crea el índice de
-- búsqueda por session_id.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    creado_en TIMESTAMPTZ DEFAULT now(),
    ultima_actividad TIMESTAMPTZ DEFAULT now()
);

-- ------------------------------------------------------------
-- Tabla de detecciones (capturas de placas)
-- usuario_id enlaza cada detección con la sesión que la creó.
-- ON DELETE CASCADE: al borrar una sesión vieja de "usuarios",
-- sus detecciones se eliminan solas.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detecciones (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    placa VARCHAR(20) NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    imagen VARCHAR(255) NOT NULL,
    confianza REAL DEFAULT NULL,
    track_id INT DEFAULT NULL,
    tiempo_observacion REAL DEFAULT NULL
);

-- ------------------------------------------------------------
-- Índices de rendimiento
-- idx_detecciones_usuario es clave: todas las consultas de la
-- demo filtran por sesión, y además acelera el ON DELETE CASCADE.
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_detecciones_placa ON detecciones (placa);
CREATE INDEX IF NOT EXISTS idx_detecciones_fecha ON detecciones (fecha);
CREATE INDEX IF NOT EXISTS idx_detecciones_usuario ON detecciones (usuario_id);

-- ------------------------------------------------------------
-- Tabla de visitas (para el contador del portafolio)
-- Registro PERMANENTE: sin FK a usuarios, así la limpieza de
-- sesiones viejas NO borra el historial de visitas.
-- Tu app Flask inserta una fila cada vez que llega una sesión
-- nueva (o cada vez que un visitante regresa, como prefieras).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS visitas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id UUID NOT NULL,
    visitado_en TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_visitas_fecha ON visitas (visitado_en);

-- ------------------------------------------------------------
-- Seguridad: activar RLS para que las tablas NO queden expuestas
-- a través de la API pública automática de Supabase (anon key).
-- Tu app Flask no se ve afectada: se conecta como dueño de las
-- tablas (rol postgres) y el RLS no le aplica.
-- ------------------------------------------------------------
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE detecciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE visitas ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- Función pública para el cuadrito del portafolio.
-- Tu portafolio Next.js (en Vercel) la llama con la anon key y
-- recibe SOLO los números — nunca acceso a las tablas.
--
-- Desde Next.js:
--   const { data } = await supabase.rpc('estadisticas_demo')
--   // data = { "total_visitas": 42, "visitantes_unicos": 17 }
--
-- O con fetch directo:
--   POST https://TU_PROYECTO.supabase.co/rest/v1/rpc/estadisticas_demo
--   headers: { apikey: ANON_KEY, Authorization: 'Bearer ' + ANON_KEY }
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION estadisticas_demo()
RETURNS JSON
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT json_build_object(
        'total_visitas',     (SELECT COUNT(*) FROM visitas),
        'visitantes_unicos', (SELECT COUNT(DISTINCT session_id) FROM visitas)
    );
$$;

GRANT EXECUTE ON FUNCTION estadisticas_demo() TO anon;

-- ------------------------------------------------------------
-- Limpieza de sesiones antiguas (opcional pero recomendado).
-- Gracias al CASCADE, borrar la sesión borra sus detecciones.
-- Puedes ejecutarlo a mano de vez en cuando:
--
--   DELETE FROM usuarios WHERE ultima_actividad < now() - INTERVAL '24 hours';
--
-- O automatizarlo con pg_cron (Dashboard -> Database -> Extensions
-- -> habilitar pg_cron) y luego ejecutar una sola vez:
--
--   SELECT cron.schedule(
--       'limpiar-sesiones-demo',
--       '0 3 * * *',  -- todos los días a las 3:00 AM
--       $$DELETE FROM usuarios WHERE ultima_actividad < now() - INTERVAL '24 hours'$$
--   );
-- ------------------------------------------------------------
