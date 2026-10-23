# RESULTADOS — Módulo 5 (etapa estructura + base de datos)

Fecha etapa: 2026-10-16 · Zona: America/Bogota
No se leyó `.env`; no se llamaron servicios reales; datos ficticios (IDs 90000x).

## Archivos creados en esta etapa
- `deno.json` — tareas `check`/`test` proyecto + `imports` con
  `@supabase/supabase-js` fija (`npm:@supabase/supabase-js@2.48.0`);
  se conservan `telegram:identificar|conectar|estado`.
- `supabase/config.toml` — `project_id = "spa-manos-pies"`,
  `[functions.spa-telegram] verify_jwt = false`.
- `supabase/migrations/202610020001_spa.sql` — 5 tablas + checks + índices
  (2 únicos parciales de ocupación), RLS en todas sin políticas públicas,
  revoke a anon/authenticated/PUBLIC, grant a service_role, servicios
  ficticios, `spa_generar_horarios()`, `spa_mutar_cita`,
  `spa_reclamar_avisos()`, `spa_finalizar_aviso()`, semilla inicial.
- `tests/integration.sql` — BEGIN/ROLLBACK con 10 bloques (reserva, replay,
  cita_activa, horario_ocupado, permisos, doble transición, cancelación y
  liberación, vencimiento, cola con lease, RLS/RPC) + guía de concurrencia
  en dos sesiones.

## Etapa 2 — bot implementado (2026-10-23)
Archivos creados:
- `supabase/functions/spa-telegram/index.ts` — entrada, `Deno.serve`,
  401 secreto antes del cuerpo, 405 método, 400 JSON/evento, 200 negocio,
  500 técnico; procesa un lote de avisos tras el evento.
- `supabase/functions/spa-telegram/handler.ts` — /start, /help, Servicios,
  Agendar (servicio → día → horario → resumen), Enviar solicitud, Mi cita,
  cancelación con segunda confirmación, confirmar/rechazar solo si
  `ADMIN_USER_ID`, /pendientes paginado, /reintentar, avisos con lease.
- `supabase/functions/spa-telegram/repository.ts` — RPC `spa_mutar_cita`,
  `spa_generar_horarios`, `spa_reclamar_avisos`, `spa_finalizar_aviso`;
  clave de servidor desde `SUPABASE_SECRET_KEYS` o `SUPABASE_SERVICE_ROLE_KEY`.
- `supabase/functions/spa-telegram/telegram.ts` — fetch, timeout, `ok=true`,
  error tipado con `retry_after`, callbacks ≤64 bytes.
- `supabase/functions/spa-telegram/deno.json` — imports fijos + check/test.
- `supabase/functions/spa-telegram/handler_test.ts`, `telegram_test.ts`.
- `GUIA_PUBLICACION.md` — variables, ruta, comprobaciones y limitación sin cron.

Correcciones aplicadas:
- Migración: el seed de servicios ya no inserta `id` explícito (columna
  `GENERATED ALWAYS`); se omitió en el INSERT.
- `tests/integration.sql` bloque 10: acepta `insufficient_privilege` como
  resultado correcto de anon (privilegios revocados), en vez de romper.

## Verificación local
- `deno task check`: APROBADO 2026-10-23 (scripts + función + tests; 0 errores).
- `deno task test`: APROBADO 2026-10-23 (15/15: 6 de configuración Telegram,
  5 de handler con mocks de fetch, 4 de callbacks).
- Integración SQL real: APROBADA (ejecutada por el estudiante en SQL Editor;
  terminó con ROLLBACK tras corregir el bloque 10).
- Concurrencia dos sesiones: NO EJECUTADA (instrucciones en tests/integration.sql).
- Telegram real (menú, recorrido, permisos, fallas): PENDIENTE de prueba en
  vivo tras publicar y conectar el webhook.

## Etapa 3 — publicación y prueba en vivo (2026-10-23)
Publicación:
- Función `spa-telegram` desplegada con `--use-api`; `Verify JWT` desactivado.
- Webhook registrado; `telegram:estado` → `conectado_a_esta_funcion: true`.
- Incidencia corregida: el webhook devolvía 401 porque
  `TELEGRAM_WEBHOOK_SECRET` no coincidía entre `.env` y los Secrets de Supabase.
  Se alineó el valor y se volvió a ejecutar `telegram:conectar`.

Resultados observados por el estudiante (dos cuentas, A responsable y B clienta):
- Menú y Servicios: OK.
- Solicitud con estado pendiente y aviso al responsable: OK.
- Doble clic al enviar (sin duplicar): OK.
- Confirmación por el responsable: OK.
- Doble confirmación (sin segunda transición): OK.
- Consulta Mi cita (solo la propia): OK.
- Cancelación con segunda confirmación y horario liberado: OK.
- Rechazo y nueva solicitud: OK.
- Permisos de /pendientes y /reintentar para cliente: OK (acceso denegado).
- Capturas en `evidencia/capturas/`: `menu.jpeg`, `servicios-agendar.jpeg`,
  `solicitud-y-confirmacion.jpeg`, `confirmacion-servicio-dia-hora.jpeg`,
  `cancelacion.jpeg`, `estados-sql.jpeg`.

Pendiente de verificación:
- Concurrencia real en dos sesiones SQL: NO EJECUTADA.
- Horario ocupado con dos clientas simultáneas: NO EJECUTADA.
- Falla de notificación (bloquear bot y confirmar): NO EJECUTADA.

## Pendiente de verificación en vivo (etapa publicación)
1. Desplegar `spa-telegram` y registrar el webhook (`GUIA_PUBLICACION.md`).
2. Probar con dos cuentas: servicios, solicitud, confirmación, rechazo,
   cancelación, doble clic, permisos y horario ocupado.
3. Probar falla de notificación (bloquear bot) y confirmar que la cita no se pierde.

## Cómo ejecutar la migración (una sola vez, proyecto nuevo)
1. Abre `supabase/migrations/202610020001_spa.sql`, cópialo completo.
2. Supabase → SQL Editor → New query → pega → Run.
3. Comprueba: `select id, nombre, precio_cop from public.spa_servicios order by id;`
   (3 filas) y horarios Bogotá con
   `select id, inicio at time zone 'America/Bogota' as hora_bogota
    from public.spa_horarios order by inicio limit 12;`
4. Luego abre `tests/integration.sql` en otra query y ejecútalo: debe terminar
   sin errores y con ROLLBACK (no deja citas ficticias).
5. Si falla: entrega solo el error sin credenciales para corrección incremental.
   No reejecutar la migración ni borrar la base.

## Nota de concurrencia
El índice único parcial `ux_spa_citas_horario_activa` (y el de clienta)
protege el horario incluso con solicitudes simultáneas: si dos personas ven
"libre" y envían a la vez, una inserta y la otra viola el índice → la RPC
devuelve `horario_ocupado`/`cita_activa` sin dejar reservas huérfanas.
Consultar-disponibilidad-antes-de-insertar, por sí solo, no evita la carrera.
