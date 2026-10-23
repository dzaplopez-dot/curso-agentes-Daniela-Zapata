-- ============================================================================
-- Módulo 5 · Spa Manos y Pies · migración inicial
-- Archivo: supabase/migrations/202610020001_spa.sql
-- Ejecutar UNA SOLA VEZ en un proyecto nuevo (SQL Editor → New query → Run).
-- Sin DROP ni borrado de tablas. Precios y horarios ficticios. Sin datos reales.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- --------------------------------------------------------------------------
-- 1. TABLAS
-- --------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.spa_servicios (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre       text NOT NULL,
  precio_cop   integer NOT NULL CHECK (precio_cop > 0),
  duracion_min integer NOT NULL DEFAULT 60 CHECK (duracion_min > 0),
  activo       boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS public.spa_horarios (
  id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  inicio timestamptz NOT NULL UNIQUE,
  fin    timestamptz NOT NULL CHECK (fin > inicio)
);

CREATE TABLE IF NOT EXISTS public.spa_citas (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cliente_user_id bigint NOT NULL,
  cliente_chat_id bigint NOT NULL,
  cliente_nombre  text NOT NULL DEFAULT '' CHECK (char_length(cliente_nombre) <= 80),
  servicio_id     bigint NOT NULL REFERENCES public.spa_servicios (id),
  horario_id      bigint NOT NULL REFERENCES public.spa_horarios (id),
  estado          text NOT NULL DEFAULT 'pendiente'
                  CHECK (estado IN ('pendiente','confirmada','cancelada','rechazada','finalizada')),
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.spa_eventos (
  update_id  bigint PRIMARY KEY,
  tipo       text NOT NULL DEFAULT 'webhook',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.spa_notificaciones (
  id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  clave                text NOT NULL UNIQUE,
  cita_id              bigint NULL REFERENCES public.spa_citas (id),
  chat_id              bigint NOT NULL,
  payload              jsonb NOT NULL DEFAULT '{}'::jsonb,
  estado               text NOT NULL DEFAULT 'pendiente'
                       CHECK (estado IN ('pendiente','procesando','enviada','fallida','revision')),
  intentos             integer NOT NULL DEFAULT 0 CHECK (intentos >= 0),
  disponible_desde     timestamptz NOT NULL DEFAULT now(),
  lease_hasta          timestamptz NULL,
  lease_token          uuid NULL,
  telegram_message_id  bigint NULL,
  error_codigo         text NULL,
  created_at           timestamptz NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------------
-- 2. ÍNDICES
-- El índice único parcial protege el horario incluso con solicitudes
-- simultáneas: dos transacciones concurrentes no pueden dejar dos citas
-- activas sobre el mismo horario, aunque ambas hayan consultado "libre"
-- antes de insertar. Consultar-libre-y-luego-insertar NO basta; el índice
-- es la restricción real. Lo mismo para una cita activa por clienta.
-- --------------------------------------------------------------------------

CREATE UNIQUE INDEX IF NOT EXISTS ux_spa_citas_horario_activa
  ON public.spa_citas (horario_id)
  WHERE estado IN ('pendiente','confirmada');

CREATE UNIQUE INDEX IF NOT EXISTS ux_spa_citas_cliente_activa
  ON public.spa_citas (cliente_user_id)
  WHERE estado IN ('pendiente','confirmada');

CREATE INDEX IF NOT EXISTS ix_spa_citas_estado
  ON public.spa_citas (estado);

CREATE INDEX IF NOT EXISTS ix_spa_citas_horario
  ON public.spa_citas (horario_id);

CREATE INDEX IF NOT EXISTS ix_spa_notif_elegibles
  ON public.spa_notificaciones (estado, disponible_desde)
  WHERE estado IN ('pendiente','procesando');

-- --------------------------------------------------------------------------
-- 3. RLS + PRIVILEGIOS (todas las tablas, sin políticas públicas)
-- service_role (la función alojada) conserva acceso; anon/authenticated no.
-- --------------------------------------------------------------------------

ALTER TABLE public.spa_servicios      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spa_horarios       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spa_citas          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spa_eventos        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spa_notificaciones ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.spa_servicios,
                    public.spa_horarios,
                    public.spa_citas,
                    public.spa_eventos,
                    public.spa_notificaciones
  FROM PUBLIC, anon, authenticated;

GRANT ALL ON TABLE public.spa_servicios,
                   public.spa_horarios,
                   public.spa_citas,
                   public.spa_eventos,
                   public.spa_notificaciones
  TO service_role;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- --------------------------------------------------------------------------
-- 4. SERVICIOS FICTICIOS (idempotentes, una sola estación, bloques de 60 min)
-- --------------------------------------------------------------------------

INSERT INTO public.spa_servicios (id, nombre, precio_cop, duracion_min, activo)
VALUES (1, 'Manicure', 30000, 60, true),
       (2, 'Pedicure', 40000, 60, true),
       (3, 'Manos y pies', 65000, 60, true)
ON CONFLICT (id) DO UPDATE
  SET nombre = EXCLUDED.nombre,
      precio_cop = EXCLUDED.precio_cop,
      duracion_min = EXCLUDED.duracion_min,
      activo = EXCLUDED.activo;

-- --------------------------------------------------------------------------
-- 5. SEMILLA DE HORARIOS (Bogotá, próximos 7 días de atención, sin hoy)
-- Lunes a sábado, inicios 09:00/10:00/11:00/14:00/15:00/16:00, 60 minutos.
-- Semilla dinámica relativa al día de ejecución. Idempotente.
-- --------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.spa_generar_horarios()
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v_hoy_bog date := (now() AT TIME ZONE 'America/Bogota')::date;
  v_d       integer;
  v_fecha   date;
  v_dow     integer;
  v_h       integer;
  v_inicio  timestamptz;
  v_n       integer := 0;
BEGIN
  FOR v_d IN 1..7 LOOP
    v_fecha := v_hoy_bog + v_d;
    v_dow := EXTRACT(ISODOW FROM v_fecha)::integer;
    IF v_dow = 7 THEN
      CONTINUE; -- domingo cerrado
    END IF;
    FOREACH v_h IN ARRAY ARRAY[9, 10, 11, 14, 15, 16] LOOP
      v_inicio := (v_fecha::text || ' ' || lpad(v_h::text, 2, '0') || ':00:00')::timestamp
                  AT TIME ZONE 'America/Bogota';
      INSERT INTO public.spa_horarios (inicio, fin)
      VALUES (v_inicio, v_inicio + interval '60 minutes')
      ON CONFLICT (inicio) DO NOTHING;
      IF FOUND THEN
        v_n := v_n + 1;
      END IF;
    END LOOP;
  END LOOP;
  RETURN v_n;
END;
$$;

-- --------------------------------------------------------------------------
-- 6. MUTACIÓN TRANSACCIONAL DE CITAS
-- Guarda evento + cita + avisos en UNA sola transacción. Un error técnico
-- revierte todo, incluido update_id. Repetir update_id devuelve "duplicado"
-- sin efectos. ADMIN_* llegan SOLO del entorno del servidor (la función
-- los inyecta desde sus variables), nunca del cuerpo de Telegram.
-- Códigos: solicitada | confirmada | rechazada | cancelada | duplicado |
--   horario_ocupado | cita_activa | sin_permiso | estado_invalido |
--   horario_vencido | horario_invalido | servicio_invalido | cita_inexistente
-- --------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.spa_mutar_cita(
  p_update_id     bigint,
  p_accion        text,
  p_actor_user_id bigint,
  p_actor_chat_id bigint,
  p_actor_nombre  text DEFAULT '',
  p_cita_id       bigint DEFAULT NULL,
  p_servicio_id   bigint DEFAULT NULL,
  p_horario_id    bigint DEFAULT NULL,
  p_admin_user_id bigint DEFAULT NULL,
  p_admin_chat_id bigint DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v_now      timestamptz := now();
  v_nombre   text := left(coalesce(p_actor_nombre, ''), 80);
  v_cita     public.spa_citas%ROWTYPE;
  v_hor_fin  timestamptz;
  v_cons     text;
BEGIN
  IF p_accion NOT IN ('solicitar', 'confirmar', 'rechazar', 'cancelar') THEN
    RETURN jsonb_build_object('ok', false, 'codigo', 'accion_invalida');
  END IF;

  -- 1) Reservar update_id (idempotencia del webhook).
  INSERT INTO public.spa_eventos (update_id, tipo)
  VALUES (p_update_id, p_accion)
  ON CONFLICT (update_id) DO NOTHING;
  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', true, 'codigo', 'duplicado');
  END IF;

  -- ---------------------------------------------------------- SOLICITAR --
  IF p_accion = 'solicitar' THEN
    IF p_servicio_id IS NULL OR p_horario_id IS NULL THEN
      RETURN jsonb_build_object('ok', false, 'codigo', 'horario_invalido');
    END IF;

    PERFORM 1 FROM public.spa_servicios s
      WHERE s.id = p_servicio_id AND s.activo;
    IF NOT FOUND THEN
      RETURN jsonb_build_object('ok', false, 'codigo', 'servicio_invalido');
    END IF;

    PERFORM 1 FROM public.spa_horarios h
      WHERE h.id = p_horario_id AND h.inicio > v_now;
    IF NOT FOUND THEN
      RETURN jsonb_build_object('ok', false, 'codigo', 'horario_invalido');
    END IF;

    -- Cerrar vencidas de esa persona para que el pasado no bloquee.
    UPDATE public.spa_citas c
      SET estado = 'finalizada'
      FROM public.spa_horarios h
      WHERE c.horario_id = h.id
        AND c.cliente_user_id = p_actor_user_id
        AND c.estado IN ('pendiente', 'confirmada')
        AND h.fin <= v_now;

    BEGIN
      INSERT INTO public.spa_citas
        (cliente_user_id, cliente_chat_id, cliente_nombre, servicio_id, horario_id, estado)
      VALUES (p_actor_user_id, p_actor_chat_id, v_nombre, p_servicio_id, p_horario_id, 'pendiente')
      RETURNING * INTO v_cita;
    EXCEPTION WHEN unique_violation THEN
      GET STACKED DIAGNOSTICS v_cons = CONSTRAINT_NAME;
      IF v_cons = 'ux_spa_citas_cliente_activa' THEN
        RETURN jsonb_build_object('ok', false, 'codigo', 'cita_activa');
      ELSE
        RETURN jsonb_build_object('ok', false, 'codigo', 'horario_ocupado');
      END IF;
    END;

    INSERT INTO public.spa_notificaciones (clave, cita_id, chat_id, payload)
    VALUES ('cita:' || v_cita.id || ':pendiente:cliente',
            v_cita.id, v_cita.cliente_chat_id,
            jsonb_build_object('cita_id', v_cita.id, 'estado', 'pendiente', 'destino', 'cliente'))
    ON CONFLICT (clave) DO NOTHING;

    IF p_admin_chat_id IS NOT NULL THEN
      INSERT INTO public.spa_notificaciones (clave, cita_id, chat_id, payload)
      VALUES ('cita:' || v_cita.id || ':pendiente:admin',
              v_cita.id, p_admin_chat_id,
              jsonb_build_object('cita_id', v_cita.id, 'estado', 'pendiente', 'destino', 'responsable'))
      ON CONFLICT (clave) DO NOTHING;
    END IF;

    RETURN jsonb_build_object('ok', true, 'codigo', 'solicitada', 'cita_id', v_cita.id);
  END IF;

  -- ------------------------------------------------- CONFIRMAR/RECHAZAR --
  IF p_accion IN ('confirmar', 'rechazar') THEN
    IF p_cita_id IS NULL THEN
      RETURN jsonb_build_object('ok', false, 'codigo', 'cita_inexistente');
    END IF;

    SELECT * INTO v_cita FROM public.spa_citas WHERE id = p_cita_id FOR UPDATE;
    IF NOT FOUND THEN
      RETURN jsonb_build_object('ok', false, 'codigo', 'cita_inexistente');
    END IF;

    IF p_actor_user_id IS DISTINCT FROM p_admin_user_id OR p_admin_user_id IS NULL THEN
      RETURN jsonb_build_object('ok', false, 'codigo', 'sin_permiso');
    END IF;

    IF v_cita.estado <> 'pendiente' THEN
      RETURN jsonb_build_object('ok', false, 'codigo', 'estado_invalido');
    END IF;

    SELECT h.fin INTO v_hor_fin FROM public.spa_horarios h WHERE h.id = v_cita.horario_id;
    IF v_hor_fin IS NULL OR v_hor_fin <= v_now THEN
      UPDATE public.spa_citas SET estado = 'finalizada' WHERE id = v_cita.id;
      RETURN jsonb_build_object('ok', false, 'codigo', 'horario_vencido');
    END IF;

    IF p_accion = 'confirmar' THEN
      UPDATE public.spa_citas SET estado = 'confirmada' WHERE id = v_cita.id;
    ELSE
      UPDATE public.spa_citas SET estado = 'rechazada' WHERE id = v_cita.id;
    END IF;

    INSERT INTO public.spa_notificaciones (clave, cita_id, chat_id, payload)
    VALUES ('cita:' || v_cita.id || ':' ||
              CASE WHEN p_accion = 'confirmar' THEN 'confirmada' ELSE 'rechazada' END || ':cliente',
            v_cita.id, v_cita.cliente_chat_id,
            jsonb_build_object('cita_id', v_cita.id,
              'estado', CASE WHEN p_accion = 'confirmar' THEN 'confirmada' ELSE 'rechazada' END,
              'destino', 'cliente'))
    ON CONFLICT (clave) DO NOTHING;

    IF p_accion = 'confirmar' THEN
      RETURN jsonb_build_object('ok', true, 'codigo', 'confirmada', 'cita_id', v_cita.id);
    ELSE
      RETURN jsonb_build_object('ok', true, 'codigo', 'rechazada', 'cita_id', v_cita.id);
    END IF;
  END IF;

  -- ------------------------------------------------------------ CANCELAR --
  SELECT * INTO v_cita FROM public.spa_citas WHERE id = p_cita_id FOR UPDATE;
  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'codigo', 'cita_inexistente');
  END IF;

  IF p_actor_user_id <> v_cita.cliente_user_id
     AND p_actor_user_id IS DISTINCT FROM p_admin_user_id THEN
    RETURN jsonb_build_object('ok', false, 'codigo', 'sin_permiso');
  END IF;

  IF v_cita.estado NOT IN ('pendiente', 'confirmada') THEN
    RETURN jsonb_build_object('ok', false, 'codigo', 'estado_invalido');
  END IF;

  UPDATE public.spa_citas SET estado = 'cancelada' WHERE id = v_cita.id;

  IF p_actor_user_id = v_cita.cliente_user_id AND p_admin_chat_id IS NOT NULL THEN
    INSERT INTO public.spa_notificaciones (clave, cita_id, chat_id, payload)
    VALUES ('cita:' || v_cita.id || ':cancelada:admin',
            v_cita.id, p_admin_chat_id,
            jsonb_build_object('cita_id', v_cita.id, 'estado', 'cancelada', 'destino', 'responsable'))
    ON CONFLICT (clave) DO NOTHING;
  ELSIF p_actor_user_id IS NOT DISTINCT FROM p_admin_user_id THEN
    INSERT INTO public.spa_notificaciones (clave, cita_id, chat_id, payload)
    VALUES ('cita:' || v_cita.id || ':cancelada:cliente',
            v_cita.id, v_cita.cliente_chat_id,
            jsonb_build_object('cita_id', v_cita.id, 'estado', 'cancelada', 'destino', 'cliente'))
    ON CONFLICT (clave) DO NOTHING;
  END IF;

  RETURN jsonb_build_object('ok', true, 'codigo', 'cancelada', 'cita_id', v_cita.id);
END;
$$;

-- --------------------------------------------------------------------------
-- 7. COLA DE AVISOS: reclamar con lease + finalizar con token.
-- Lotes limitados, SKIP LOCKED, solo el dueño del lease finaliza.
-- p_resultado: enviada | reintentable | fallida | revision
-- --------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.spa_reclamar_avisos(
  p_limite    integer DEFAULT 10,
  p_lease_seg integer DEFAULT 300
)
RETURNS SETOF public.spa_notificaciones
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  UPDATE public.spa_notificaciones n
    SET estado = 'procesando',
        lease_hasta = now() + make_interval(secs => greatest(p_lease_seg, 30)),
        lease_token = gen_random_uuid()
    WHERE n.id IN (
      SELECT a.id FROM public.spa_notificaciones a
      WHERE (a.estado = 'pendiente' AND a.disponible_desde <= now())
         OR (a.estado = 'procesando' AND a.lease_hasta IS NOT NULL AND a.lease_hasta < now())
      ORDER BY a.disponible_desde, a.id
      LIMIT greatest(least(p_limite, 50), 1)
      FOR UPDATE SKIP LOCKED
    )
    RETURNING n.*;
END;
$$;

CREATE OR REPLACE FUNCTION public.spa_finalizar_aviso(
  p_id          bigint,
  p_token       uuid,
  p_resultado   text,
  p_message_id  bigint DEFAULT NULL,
  p_error       text DEFAULT NULL,
  p_retry_seg   integer DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v      public.spa_notificaciones%ROWTYPE;
  v_espera integer;
BEGIN
  IF p_resultado NOT IN ('enviada', 'reintentable', 'fallida', 'revision') THEN
    RETURN jsonb_build_object('ok', false, 'codigo', 'resultado_invalido');
  END IF;

  SELECT * INTO v FROM public.spa_notificaciones WHERE id = p_id FOR UPDATE;
  IF NOT FOUND THEN
    RETURN jsonb_build_object('ok', false, 'codigo', 'aviso_inexistente');
  END IF;

  IF v.estado <> 'procesando'
     OR v.lease_token IS DISTINCT FROM p_token
     OR v.lease_hasta IS NULL OR v.lease_hasta < now() THEN
    RETURN jsonb_build_object('ok', false, 'codigo', 'lease_invalido');
  END IF;

  IF p_resultado = 'enviada' THEN
    UPDATE public.spa_notificaciones
      SET estado = 'enviada', telegram_message_id = p_message_id,
          lease_hasta = NULL, lease_token = NULL
      WHERE id = p_id;
    RETURN jsonb_build_object('ok', true, 'codigo', 'enviada');
  END IF;

  IF p_resultado = 'fallida' THEN
    UPDATE public.spa_notificaciones
      SET estado = 'fallida', error_codigo = left(coalesce(p_error, 'fallida'), 50),
          lease_hasta = NULL, lease_token = NULL
      WHERE id = p_id;
    RETURN jsonb_build_object('ok', true, 'codigo', 'fallida');
  END IF;

  IF p_resultado = 'revision' THEN
    UPDATE public.spa_notificaciones
      SET estado = 'revision', error_codigo = left(coalesce(p_error, 'revision'), 50),
          lease_hasta = NULL, lease_token = NULL
      WHERE id = p_id;
    RETURN jsonb_build_object('ok', true, 'codigo', 'revision');
  END IF;

  -- reintentable: espera creciente 60s, 120s, 240s… tope 1h (+ retry_after de 429).
  IF v.intentos + 1 >= 5 THEN
    UPDATE public.spa_notificaciones
      SET estado = 'fallida', intentos = v.intentos + 1,
          error_codigo = left(coalesce(p_error, 'max_intentos'), 50),
          lease_hasta = NULL, lease_token = NULL
      WHERE id = p_id;
    RETURN jsonb_build_object('ok', true, 'codigo', 'fallida');
  END IF;

  v_espera := least(60 * (2 ^ v.intentos)::integer, 3600) + coalesce(p_retry_seg, 0);
  UPDATE public.spa_notificaciones
    SET estado = 'pendiente', intentos = v.intentos + 1,
        disponible_desde = now() + make_interval(secs => v_espera),
        error_codigo = left(p_error, 50),
        lease_hasta = NULL, lease_token = NULL
    WHERE id = p_id;
  RETURN jsonb_build_object('ok', true, 'codigo', 'reprogramado');
END;
$$;

-- --------------------------------------------------------------------------
-- 8. RPC solo para service_role (la función alojada). Ni anon, ni
-- authenticated, ni PUBLIC pueden invocarlas ni leer las tablas.
-- --------------------------------------------------------------------------

REVOKE ALL ON FUNCTION public.spa_generar_horarios() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.spa_generar_horarios() TO service_role;

REVOKE ALL ON FUNCTION public.spa_mutar_cita(bigint, text, bigint, bigint, text, bigint, bigint, bigint, bigint, bigint)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.spa_mutar_cita(bigint, text, bigint, bigint, text, bigint, bigint, bigint, bigint, bigint)
  TO service_role;

REVOKE ALL ON FUNCTION public.spa_reclamar_avisos(integer, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.spa_reclamar_avisos(integer, integer) TO service_role;

REVOKE ALL ON FUNCTION public.spa_finalizar_aviso(bigint, uuid, text, bigint, text, integer)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.spa_finalizar_aviso(bigint, uuid, text, bigint, text, integer)
  TO service_role;

-- --------------------------------------------------------------------------
-- 9. Semilla inicial de horarios (la función también se llama desde el bot
-- antes de mostrar disponibilidad, para seguir útil después de una semana).
-- --------------------------------------------------------------------------

SELECT public.spa_generar_horarios();
