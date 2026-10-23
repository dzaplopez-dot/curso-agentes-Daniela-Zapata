// Cliente Telegram mínimo sobre fetch. Sin frameworks.
// No imprime ni propaga URLs con token.

export class TelegramError extends Error {
  constructor(
    public code: number,
    public description: string,
    public retryAfter?: number,
  ) {
    super(description);
    this.name = "TelegramError";
  }
}

async function telegramCall(
  method: string,
  body: Record<string, unknown>,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const token = Deno.env.get("TELEGRAM_BOT_TOKEN") ?? "";
  if (!token) throw new Error("Falta TELEGRAM_BOT_TOKEN en el entorno del servidor.");

  let response: Response;
  try {
    response = await fetcher(`https://api.telegram.org/bot${token}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(12000),
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "TimeoutError") {
      throw new Error("timeout de Telegram: resultado incierto");
    }
    throw new Error("No se pudo conectar con Telegram.");
  }

  let data: {
    ok?: boolean;
    result?: unknown;
    error_code?: number;
    description?: string;
    parameters?: { retry_after?: number };
  };
  try {
    data = await response.json();
  } catch {
    throw new Error("Telegram devolvió una respuesta no interpretable.");
  }

  if (!response.ok || data.ok !== true) {
    throw new TelegramError(
      data.error_code ?? response.status,
      data.description ?? "operación rechazada por Telegram",
      data.parameters?.retry_after,
    );
  }
  return data.result;
}

export interface EnvioOpciones {
  replyMarkup?: unknown;
  parseMode?: "Markdown" | "HTML";
}

export async function enviarMensaje(
  chatId: number | string,
  texto: string,
  opciones: EnvioOpciones = {},
): Promise<{ message_id?: number }> {
  const body: Record<string, unknown> = { chat_id: chatId, text: texto };
  if (opciones.parseMode) body.parse_mode = opciones.parseMode;
  if (opciones.replyMarkup) body.reply_markup = opciones.replyMarkup;
  return await telegramCall("sendMessage", body) as { message_id?: number };
}

export async function responderCallback(
  callbackQueryId: string,
  texto = "",
  showAlert = false,
): Promise<void> {
  try {
    await telegramCall("answerCallbackQuery", {
      callback_query_id: callbackQueryId,
      text: texto,
      show_alert: showAlert,
    });
  } catch {
    // Una falla al responder el callback no revierte ni impide procesar.
  }
}

/** callback_data como máximo 64 bytes. */
export function construirCallback(...partes: (string | number)[]): string {
  const data = partes.map(String).join(":");
  if (new TextEncoder().encode(data).length > 64) {
    throw new Error("callback_data excede 64 bytes");
  }
  return data;
}

/** Divide callback_data; cada parte es texto corto, nunca SQL. */
export function parsearCallback(
  data: string,
): { tipo: string; args: string[] } | null {
  if (!data || typeof data !== "string") return null;
  const [tipo, ...args] = data.split(":");
  if (!tipo || tipo.length > 20) return null;
  if (args.some((a) => a.length > 20 || !/^[\w-]+$/.test(a))) return null;
  return { tipo, args };
}
