// Entrypoint de la Edge Function spa-telegram.
// Deno.serve se registra SOLO aquí, nunca al importar los módulos en pruebas.
import { handleUpdate, procesarAvisosPendientes, type TgUpdate } from "./handler.ts";
import { TelegramError } from "./telegram.ts";

const WEBHOOK_SECRET = Deno.env.get("TELEGRAM_WEBHOOK_SECRET") ?? "";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

Deno.serve(async (req: Request): Promise<Response> => {
  // 405: método incorrecto
  if (req.method !== "POST") {
    await req.body?.cancel();
    return json({ ok: false, error: "method_not_allowed" }, 405);
  }

  // 401: secreto incorrecto, ANTES de leer el cuerpo
  const recibido = req.headers.get("X-Telegram-Bot-Api-Secret-Token") ?? "";
  if (!WEBHOOK_SECRET || recibido !== WEBHOOK_SECRET) {
    await req.body?.cancel();
    return json({ ok: false, error: "unauthorized" }, 401);
  }

  // 400: JSON o evento mal formado
  let update: TgUpdate;
  try {
    update = (await req.json()) as TgUpdate;
  } catch {
    return json({ ok: false, error: "bad_json" }, 400);
  }
  if (!update || typeof update.update_id !== "number") {
    return json({ ok: false, error: "bad_event" }, 400);
  }

  // Procesar el evento. Errores de negocio devuelven 200 desde el handler.
  try {
    await handleUpdate(update);
  } catch (e) {
    if (e instanceof TelegramError) {
      // La cita (si aplica) ya quedó guardada; un fallo al responder a Telegram
      // no debe provocar reintentos que dupliquen mensajes.
      console.error("spa-telegram: fallo al responder a Telegram:", e.code);
      return json({ ok: true, aviso: "telegram_error" }, 200);
    }
    // Falla técnica antes de confirmar la transacción: 500 para que Telegram reintente.
    console.error(
      "spa-telegram: error técnico:",
      e instanceof Error ? e.message : "desconocido",
    );
    return json({ ok: false, error: "internal" }, 500);
  }

  // Mover un lote pequeño de avisos dentro de la misma invocación.
  // Una falla aquí no invalida la cita ya guardada.
  try {
    await procesarAvisosPendientes(5);
  } catch (e) {
    console.error(
      "spa-telegram: error procesando avisos:",
      e instanceof Error ? e.message : "desconocido",
    );
  }

  return json({ ok: true }, 200);
});
