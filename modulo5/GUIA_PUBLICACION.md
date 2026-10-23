# Guía de publicación — spa-telegram

Sin secretos. No incluyas tokens, claves ni capturas de Secrets.

## 1. Variables de Edge Functions (Supabase → Edge Functions → Secrets)

Crea exactamente estas cuatro variables:

| Nombre exacto | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token de BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Secreto de 32+ caracteres (el mismo de `.env`) |
| `ADMIN_USER_ID` | user_id del responsable (lo da `deno task telegram:identificar`) |
| `ADMIN_CHAT_ID` | chat privado del responsable (lo da el mismo script) |

No copies `SUPABASE_URL`, `SUPABASE_SECRET_KEYS` ni `SUPABASE_SERVICE_ROLE_KEY`:
Supabase los inyecta en la función alojada. No uses `SUPABASE_PUBLISHABLE_KEYS`
para estas RPC restringidas.

## 2. Ruta de la función

- Código: `supabase/functions/spa-telegram/` (`index.ts`, `handler.ts`, `repository.ts`, `telegram.ts`, `deno.json`)
- URL publicada: `https://<PROJECT_REF>.supabase.co/functions/v1/spa-telegram`
- `supabase/config.toml` fija `project_id = "spa-manos-pies"` y `verify_jwt = false`.

La autenticación del webhook es el secreto `X-Telegram-Bot-Api-Secret-Token`
comparado antes de leer el cuerpo. No desactives esa comprobación.

## 3. Publicar

```bash
npx --yes supabase@latest login
npx --yes supabase@latest functions deploy spa-telegram --project-ref <PROJECT_REF> --use-api
```

No ejecutes `supabase init` sobre esta carpeta.

## 4. Conectar el webhook

Revisa que `.env` tenga la URL correcta y el mismo secreto que Supabase.

```bash
deno task telegram:conectar
deno task telegram:estado
```

Debes ver `"configurado": true` y `"conectado_a_esta_funcion": true`.

## 5. Comprobaciones posteriores

1. La función aparece publicada y `Verify JWT` desactivado.
2. La URL termina en `/functions/v1/spa-telegram`.
3. En el bot: `/start` muestra Servicios, Agendar, Mi cita.
4. `/servicios` lista 3 servicios con precios ficticios.
5. Solicitar crea cita `pendiente` y avisa al responsable.
6. Confirmar/rechazar solo funciona para `ADMIN_USER_ID`.
7. `Mi cita` muestra solo la cita de quien consulta.
8. Cancelar pide segunda confirmación y libera el horario.
9. `/pendientes` y `/reintentar` deniegan a quien no es responsable.

## 6. Limitación de recuperación (sin cron)

No hay worker permanente ni cron en la ruta básica. Las notificaciones pendientes
avanzan cuando llega un evento nuevo al webhook o cuando el responsable usa
`/reintentar`; no se envían solas. Los estados `revision` (timeout incierto) se
revisan manualmente desde el SQL Editor y no se reenvían automáticamente.
Un aviso `fallida` por bloqueo del bot no se resuelve con `/reintentar`.
