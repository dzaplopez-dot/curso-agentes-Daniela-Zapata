import { handleUpdate, procesarAvisosPendientes } from "./handler.ts";

const fetchReal = globalThis.fetch;

interface Llamada {
  url: string;
  body: Record<string, unknown>;
}

function respuestaOk(): Response {
  return new Response(JSON.stringify({ ok: true, result: { message_id: 1 } }), {
    headers: { "Content-Type": "application/json" },
  });
}

async function conTelegramMock(
  fn: (llamadas: Llamada[]) => Promise<void>,
): Promise<void> {
  const llamadas: Llamada[] = [];
  Deno.env.set("TELEGRAM_BOT_TOKEN", "123456:token_ficticio");
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    llamadas.push({
      url: String(input),
      body: init?.body ? JSON.parse(String(init.body)) : {},
    });
    return respuestaOk();
  }) as typeof fetch;
  try {
    await fn(llamadas);
  } finally {
    globalThis.fetch = fetchReal;
  }
}

function mensajes(llamadas: Llamada[]): Record<string, unknown>[] {
  return llamadas.filter((l) => l.url.endsWith("/sendMessage")).map((l) => l.body);
}

Deno.test("grupo: responde breve y no ejecuta acciones", async () => {
  await conTelegramMock(async (llamadas) => {
    await handleUpdate({
      update_id: 1,
      message: {
        from: { id: 10, first_name: "Alguien" },
        chat: { id: -100, type: "group" },
        text: "/start",
      },
    });
    const enviados = mensajes(llamadas);
    if (enviados.length !== 1) throw new Error("Debía enviar un solo aviso al grupo");
    if (!String(enviados[0].text).includes("chat privado")) {
      throw new Error("Debía indicar que solo atiende en privado");
    }
  });
});

Deno.test("texto no reconocido: muestra ayuda con botones", async () => {
  await conTelegramMock(async (llamadas) => {
    await handleUpdate({
      update_id: 2,
      message: {
        from: { id: 11, first_name: "Clienta" },
        chat: { id: 11, type: "private" },
        text: "hola, qué puedes hacer",
      },
    });
    const enviados = mensajes(llamadas);
    if (enviados.length !== 1) throw new Error("Debía enviar la ayuda");
    if (!enviados[0].reply_markup) throw new Error("La ayuda debe traer botones");
  });
});

Deno.test("callback inválido: responde callback y muestra ayuda", async () => {
  await conTelegramMock(async (llamadas) => {
    await handleUpdate({
      update_id: 3,
      callback_query: {
        id: "cb-1",
        from: { id: 12, first_name: "Clienta" },
        message: { chat: { id: 12, type: "private" } },
        data: "",
      },
    });
    if (!llamadas.some((l) => l.url.endsWith("/answerCallbackQuery"))) {
      throw new Error("Debía responder el callback");
    }
    if (mensajes(llamadas).length < 1) throw new Error("Debía mostrar ayuda");
  });
});

Deno.test("/pendientes sin ser responsable: acceso denegado", async () => {
  await conTelegramMock(async (llamadas) => {
    await handleUpdate({
      update_id: 4,
      message: {
        from: { id: 13, first_name: "Clienta" },
        chat: { id: 13, type: "private" },
        text: "/pendientes",
      },
    });
    const enviados = mensajes(llamadas);
    if (enviados.length !== 1) throw new Error("Debía responder una vez");
    if (!String(enviados[0].text).includes("permiso")) {
      throw new Error("Debía denegar el acceso");
    }
  });
});

Deno.test("procesarAvisosPendientes sin base: no lanza y devuelve ceros", async () => {
  const r = await procesarAvisosPendientes(3);
  if (r.enviadas !== 0 || r.fallidas !== 0 || r.revision !== 0 || r.pendientes !== 0) {
    throw new Error("Con base no disponible debía devolver ceros");
  }
});
