-- ============================================================================
-- Módulo 5 · tests/integration.sql — integración real contra la base.
-- Ejecutar en SQL Editor DESPUÉS de la migración, en una New query aparte.
-- Todo queda en BEGIN/ROLLBACK: no deja citas ficticias. Debe terminar sin
-- errores. IDs 90000x ficticios, nunca reales.
--
-- CONCURRENCIA REAL (dos sesiones, aparte de este archivo):
--   Sesión A y B: BEGIN;
--     A: SELECT public.spa_mutar_cita(910101,'solicitar',900011,900012,'A',NULL,1,H,'',900001,900021);
--     B: SELECT public.spa_mutar_cita(910102,'solicitar',900012,900022,'B',NULL,1,H,'',900001,900021);
--     (mismo H = id de un horario futuro libre; ambas ven "libre" primero)
--   A: COMMIT;  B: COMMIT;  -- una recibe solicitada, la otra horario_ocupado.
--   Solo UNA fila activa sobre H: SELECT count(*) FROM spa_citas
--     WHERE horario_id = H AND estado IN ('pendiente','confirmada'); → 1.
--   Las consultas secuenciales NO comprueban carreras; si no se hace esta
--   prueba, la concurrencia queda PENDIENTE en evidencia/RESULTADOS.md.
-- ============================================================================

BEGIN;

-- 0) Servicios semilla y horarios futuros en Bogotá -------------------------
DO $$
DECLARE
  v_serv integer;
  v_hor  integer;
BEGIN
  SELECT count(*) INTO v_serv FROM public.spa_servicios WHERE activo;
  IF v_serv < 3 THEN
    RAISE EXCEPTION 'Servicios semilla incompletos: %', v_serv;
  END IF;

  PERFORM public.spa_generar_horarios();
  SELECT count(*) INTO v_hor FROM public.spa_horarios WHERE inicio > now();
  IF v_hor < 6 THEN
    RAISE EXCEPTION 'Horarios futuros insuficientes: %', v_hor;
  END IF;
END $$;

-- 1) Solicitud OK (clienta B) ------------------------------------------------
-- Toma dos horarios futuros distintos para las pruebas.
CREATE TEMP TABLE t_hor AS
  SELECT id FROM public.spa_horarios WHERE inicio > now() ORDER BY inicio LIMIT 2;

DO $$
DECLARE
  r   jsonb;
  h1  bigint;
  v_cita bigint;
BEGIN
  SELECT id INTO h1 FROM t_hor ORDER BY id LIMIT 1;

  r := public.spa_mutar_cita(910001, 'solicitar', 900002, 900012, 'ClientaB', NULL, 1, h1, 900001, 900011);
  IF r->>'codigo' <> 'solicitada' THEN
    RAISE EXCEPTION 'Solicitar falló: %', r;
  END IF;
  v_cita := (r->>'cita_id')::bigint;

  -- Aviso al responsable y a la clienta.
  IF (SELECT count(*) FROM public.spa_notificaciones
      WHERE cita_id = v_cita AND estado = 'pendiente') < 2 THEN
    RAISE EXCEPTION 'Faltan avisos de la solicitud %', v_cita;
  END IF;
END $$;

-- 2) Replay del mismo update_id → duplicado sin efectos ----------------------
DO $$
DECLARE
  r jsonb;
  n integer;
BEGIN
  SELECT count(*) INTO n FROM public.spa_citas WHERE cliente_user_id = 900002;
  r := public.spa_mutar_cita(910001, 'solicitar', 900002, 900012, 'ClientaB', NULL, 2,
                             (SELECT id FROM t_hor ORDER BY id DESC LIMIT 1), 900001, 900011);
  IF r->>'codigo' <> 'duplicado' THEN
    RAISE EXCEPTION 'Replay debió ser duplicado: %', r;
  END IF;
  IF (SELECT count(*) FROM public.spa_citas WHERE cliente_user_id = 900002) <> n THEN
    RAISE EXCEPTION 'El replay creó una cita extra';
  END IF;
END $$;

-- 3) Segunda solicitud de la misma persona → cita_activa ---------------------
DO $$
DECLARE
  r jsonb;
BEGIN
  r := public.spa_mutar_cita(910002, 'solicitar', 900002, 900012, 'ClientaB', NULL, 2,
                             (SELECT id FROM t_hor ORDER BY id DESC LIMIT 1), 900001, 900011);
  IF r->>'codigo' <> 'cita_activa' THEN
    RAISE EXCEPTION 'Debió responder cita_activa: %', r;
  END IF;
END $$;

-- 4) Otra persona, mismo horario → horario_ocupado ----------------------------
DO $$
DECLARE
  r jsonb;
BEGIN
  r := public.spa_mutar_cita(910003, 'solicitar', 900003, 900013, 'ClientaC', NULL, 2,
                             (SELECT id FROM t_hor ORDER BY id LIMIT 1), 900001, 900011);
  IF r->>'codigo' <> 'horario_ocupado' THEN
    RAISE EXCEPTION 'Debió responder horario_ocupado: %', r;
  END IF;
END $$;

-- 5) Confirmar por quien NO es responsable → sin_permiso ----------------------
DO $$
DECLARE
  r jsonb;
  v_cita bigint;
BEGIN
  SELECT id INTO v_cita FROM public.spa_citas WHERE cliente_user_id = 900002
    AND estado = 'pendiente' ORDER BY id DESC LIMIT 1;
  r := public.spa_mutar_cita(910004, 'confirmar', 900004, 900014, 'Intrusa',
                             v_cita, NULL, NULL, 900001, 900011);
  IF r->>'codigo' <> 'sin_permiso' THEN
    RAISE EXCEPTION 'Debió responder sin_permiso: %', r;
  END IF;
  IF (SELECT estado FROM public.spa_citas WHERE id = v_cita) <> 'pendiente' THEN
    RAISE EXCEPTION 'La cita cambió sin permiso';
  END IF;
END $$;

-- 6) Confirmación del responsable OK + doble confirmación inválida ------------
DO $$
DECLARE
  r jsonb;
  v_cita bigint;
BEGIN
  SELECT id INTO v_cita FROM public.spa_citas WHERE cliente_user_id = 900002
    AND estado = 'pendiente' ORDER BY id DESC LIMIT 1;
  r := public.spa_mutar_cita(910005, 'confirmar', 900001, 900011, 'Responsable',
                             v_cita, NULL, NULL, 900001, 900011);
  IF r->>'codigo' <> 'confirmada' THEN
    RAISE EXCEPTION 'Confirmar falló: %', r;
  END IF;

  r := public.spa_mutar_cita(910006, 'confirmar', 900001, 900011, 'Responsable',
                             v_cita, NULL, NULL, 900001, 900011);
  IF r->>'codigo' <> 'estado_invalido' THEN
    RAISE EXCEPTION 'Doble confirmación debió ser estado_invalido: %', r;
  END IF;

  IF (SELECT count(*) FROM public.spa_notificaciones
      WHERE cita_id = v_cita AND payload->>'estado' = 'confirmada') < 1 THEN
    RAISE EXCEPTION 'Falta el aviso de confirmada a la clienta';
  END IF;
END $$;

-- 7) Cancelación ajena denegada; propia libera el horario --------------------
DO $$
DECLARE
  r jsonb;
  v_cita bigint;
  h1 bigint;
  n integer;
BEGIN
  SELECT id INTO v_cita FROM public.spa_citas WHERE cliente_user_id = 900002
    ORDER BY id DESC LIMIT 1;
  SELECT horario_id INTO h1 FROM public.spa_citas WHERE id = v_cita;

  r := public.spa_mutar_cita(910007, 'cancelar', 900004, 900014, 'Intrusa',
                             v_cita, NULL, NULL, 900001, 900011);
  IF r->>'codigo' <> 'sin_permiso' THEN
    RAISE EXCEPTION 'Cancelación ajena debió ser sin_permiso: %', r;
  END IF;

  r := public.spa_mutar_cita(910008, 'cancelar', 900002, 900012, 'ClientaB',
                             v_cita, NULL, NULL, 900001, 900011);
  IF r->>'codigo' <> 'cancelada' THEN
    RAISE EXCEPTION 'Cancelar falló: %', r;
  END IF;

  -- Horario liberado: otra clienta sí puede ocuparlo ahora.
  r := public.spa_mutar_cita(910009, 'solicitar', 900003, 900013, 'ClientaC',
                             NULL, 2, h1, 900001, 900011);
  IF r->>'codigo' <> 'solicitada' THEN
    RAISE EXCEPTION 'El horario no se liberó: %', r;
  END IF;
  SELECT (r->>'cita_id')::bigint INTO n;
  -- Y la rechazan para cerrar el ciclo.
  r := public.spa_mutar_cita(910010, 'rechazar', 900001, 900011, 'Responsable',
                             n, NULL, NULL, 900001, 900011);
  IF r->>'codigo' <> 'rechazada' THEN
    RAISE EXCEPTION 'Rechazar falló: %', r;
  END IF;
END $$;

-- 8) Vencimiento: el pasado no bloquea y se cierra ----------------------------
DO $$
DECLARE
  r jsonb;
  h_pasado bigint;
  v_cita bigint;
BEGIN
  INSERT INTO public.spa_horarios (inicio, fin)
  VALUES (now() - interval '2 hours', now() - interval '1 hour')
  RETURNING id INTO h_pasado;

  INSERT INTO public.spa_citas
    (cliente_user_id, cliente_chat_id, cliente_nombre, servicio_id, horario_id, estado)
  VALUES (900002, 900012, 'ClientaB', 1, h_pasado, 'pendiente')
  RETURNING id INTO v_cita;

  -- Solicitar de nuevo cierra la vencida y permite otra cita.
  r := public.spa_mutar_cita(910011, 'solicitar', 900002, 900012, 'ClientaB', NULL, 1,
                             (SELECT id FROM t_hor ORDER BY id DESC LIMIT 1), 900001, 900011);
  IF r->>'codigo' <> 'solicitada' THEN
    RAISE EXCEPTION 'El pasado bloqueó la solicitud: %', r;
  END IF;
  IF (SELECT estado FROM public.spa_citas WHERE id = v_cita) <> 'finalizada' THEN
    RAISE EXCEPTION 'La cita vencida no se cerró';
  END IF;
  -- Limpieza de la solicitud creada en este paso (sigue dentro de ROLLBACK).
  PERFORM public.spa_mutar_cita(910012, 'cancelar', 900002, 900012, 'ClientaB',
                                (r->>'cita_id')::bigint, NULL, NULL, 900001, 900011);
END $$;

-- 9) Cola de avisos: reclamar con lease y finalizar ---------------------------
DO $$
DECLARE
  v_id    bigint;
  v_tok   uuid;
  r       jsonb;
  v_estado text;
BEGIN
  SELECT id INTO v_id FROM public.spa_notificaciones
    WHERE estado = 'pendiente' ORDER BY id LIMIT 1;
  IF v_id IS NULL THEN
    RAISE EXCEPTION 'No hay avisos pendientes para probar la cola';
  END IF;

  SELECT lease_token INTO v_tok FROM public.spa_reclamar_avisos(10, 300)
    WHERE id = v_id;
  IF v_tok IS NULL THEN
    RAISE EXCEPTION 'No se pudo reclamar el aviso %', v_id;
  END IF;

  -- Token ajeno no finaliza.
  r := public.spa_finalizar_aviso(v_id, gen_random_uuid(), 'enviada', 777, NULL, NULL);
  IF r->>'codigo' <> 'lease_invalido' THEN
    RAISE EXCEPTION 'Debió responder lease_invalido: %', r;
  END IF;

  -- Reintentable reprograma con espera; luego se reclama y se envía.
  r := public.spa_finalizar_aviso(v_id, v_tok, 'reintentable', NULL, 'timeout', NULL);
  IF r->>'codigo' <> 'reprogramado' THEN
    RAISE EXCEPTION 'Debió reprogramar: %', r;
  END IF;
  SELECT estado INTO v_estado FROM public.spa_notificaciones WHERE id = v_id;
  IF v_estado <> 'pendiente' THEN
    RAISE EXCEPTION 'Debió volver a pendiente, quedó %', v_estado;
  END IF;
END $$;

-- 10) Públicos sin acceso (privilegios revocados + RPC) ----------------------
-- La migración hace REVOKE ALL a anon, así que el SELECT debe fallar con
-- "permission denied" (insufficient_privilege). Ese bloqueo es el resultado
-- correcto: anon no ve citas ni ejecuta las RPC. También aceptamos 0 filas
-- en caso de que existiera RLS sin privilegios de tabla.
DO $$
DECLARE
  v_ve integer := -1;
BEGIN
  SET LOCAL ROLE anon;
  BEGIN
    SELECT count(*) INTO v_ve FROM public.spa_citas;
  EXCEPTION WHEN insufficient_privilege THEN
    v_ve := 0; -- acceso denegado: correcto
  END;
  IF v_ve <> 0 THEN
    RAISE EXCEPTION 'anon ve citas: RLS/privilegios con fuga';
  END IF;
  BEGIN
    PERFORM public.spa_generar_horarios();
    RAISE EXCEPTION 'anon pudo ejecutar la RPC';
  EXCEPTION WHEN insufficient_privilege THEN
    -- Esperado: sin EXECUTE para anon.
    NULL;
  END;
  RESET ROLE;
END $$;

-- Estado final visible (se revierte todo) -------------------------------------
SELECT id, cliente_user_id, servicio_id, horario_id, estado
  FROM public.spa_citas ORDER BY id DESC LIMIT 10;

SELECT estado, count(*) FROM public.spa_notificaciones GROUP BY estado ORDER BY 1;

ROLLBACK;
