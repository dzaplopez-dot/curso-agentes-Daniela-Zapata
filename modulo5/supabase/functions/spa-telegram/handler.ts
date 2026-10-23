import {
  listarServicios,
  listarHorariosFuturos,
  obtenerServicio,
  obtenerHorario,
  obtenerCita,
  obtenerCitaActiva,
  listarCitasPendientes,
  mutarCita,
  reclamarAvisos,
  finalizarAviso,
  type AccionCita,
  type Cita,
  type Notificacion,
} from "./repository.ts";
import {
  enviarMensaje,
  responderCallback,
  parsearCallback,
  TelegramError,
} from "./telegram.ts";

const ADMIN_USER_ID = Number(Deno.env.get("ADMIN_USER_ID") ?? "0");
const ADMIN_CHAT_ID = Number(Deno.env.get("ADMIN_CHAT_ID") ?? "0");

// ---------- Tipos mínimos de Telegram ----------
interface TgUser { id: number; first_name?: string; }
interface TgChat { id: number; type: string; }
interface TgMessage { from?: TgUser; chat: TgChat; text?: string; }
interface TgCallback { id: string; from: TgUser; message?: TgMessage; data?: string; }
export interface TgUpdate {
  update_id: number;
  message?: TgMessage;
  callback_query?: TgCallback;
}

// ---------- Utilidades de formato ----------
function money(n: number): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(n);
}
function ymdBogota(d: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Bogota",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}
function horaBogota(iso: string): string {
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: "America/Bogota",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));
}
function fechaLarga(iso: string): string {
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: "America/Bogota",
    weekday: "long",
    day: "2-digit",
    month: "long",
  }).format(new Date(iso));
}
function diaSemanaYmd(ymd: string): number {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).getUTCDay();
}
function sumarDias(ymd: string, n: number): string {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}
function etiquetaDia(ymd: string): string {
  const [y, m, d] = ymd.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: "UTC",
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  }).format(dt);
}
function proximosDias(): string[] {
  const out: string[] = [];
  const hoy = ymdBogota(new Date());
  for (let i = 1; i <= 14 && out.length < 7; i++) {
    const y = sumarDias(hoy, i);
    if (diaSemanaYmd(y) === 0) continue;
    out.push(y);
  }
  return out;
}
function compacto(ymd: string): string { return ymd.replaceAll("-", ""); }
function desdeCompacto(s: string): string {
  return s.length === 8 ? `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}` : s;
}

// ---------- Teclados ----------
type Boton = { text: string; callback_data: string };
type Teclado = { inline_keyboard: Boton[][] };

function filas(botones: Boton[], porFila = 2): Boton[][] {
  const out: Boton[][] = [];
  for (let i = 0; i < botones.length; i += porFila) out.push(botones.slice(i, i + porFila));
  return out;
}

function tecladoMenu(): Teclado {
  return {
    inline_keyboard: [
      [{ text: "Servicios", callback_data: "menu:servicios" }, { text: "Agendar", callback_data: "menu:agendar" }],
      [{ text: "Mi cita", callback_data: "menu:micita" }],
    ],
  };
}

// ---------- Mensajes fijos ----------
const TEXTO_AYUDA =
  "Spa Manos y Pies\n\n" +
  "Puedo ayudarte a:\n" +
  "• Ver Servicios\n" +
  "• Agendar una cita\n" +
  "• Consultar Mi cita\n\n" +
  "Usa los botones o /start.";

const TEXTO_GRUPO = "Este bot atiende solo por chat privado. Escríbeme en privado para agendar.";

// ---------- Entrada principal ----------
export async function handleUpdate(update: TgUpdate): Promise<void> {
  if (update.callback_query) {
    await handleCallback(update.callback_query, update.update_id);
    return;
  }
  if (update.message) {
    await handleMessage(update.message, update.update_id);
  }
}

async function handleMessage(m: TgMessage, updateId: number): Promise<void> {
  const from = m.from;
  if (!from || !m.chat) return;
  const chatId = m.chat.id;

  if (m.chat.type !== "private") {
    await enviarMensaje(chatId, TEXTO_GRUPO);
    return;
  }

  const texto = (m.text ?? "").trim();
  const nombre = (from.first_name ?? "").slice(0, 80);
  const cmd = texto.toLowerCase();

  if (cmd === "/start" || cmd === "/help" || cmd === "menu" || cmd === "ayuda") {
    await enviarMensaje(chatId, TEXTO_AYUDA, { replyMarkup: tecladoMenu() });
    return;
  }
  if (cmd === "/servicios" || cmd === "servicios") {
    await mostrarServicios(chatId);
    return;
  }
  if (cmd === "/agendar" || cmd === "agendar") {
    await mostrarServiciosParaAgendar(chatId);
    return;
  }
  if (cmd === "/micitta" || cmd === "/micita" || cmd === "mi cita") {
    await mostrarMiCita(chatId, from.id);
    return;
  }
  if (cmd === "/pendientes") {
    await mostrarPendientes(chatId, from.id, updateId);
    return;
  }
  if (cmd === "/reintentar") {
    await reintentar(chatId, from.id);
    return;
  }

  await enviarMensaje(chatId, TEXTO_AYUDA, { replyMarkup: tecladoMenu() });
  void nombre;
  void updateId;
}

// ---------- Callbacks ----------
async function handleCallback(cq: TgCallback, updateId: number): Promise<void> {
  await responderCallback(cq.id); // rápido; su falla no revierte nada

  const from = cq.from;
  const chat = cq.message?.chat;
  if (!from || !chat) return;
  if (chat.type !== "private") {
    await enviarMensaje(chat.id, TEXTO_GRUPO);
    return;
  }

  const parsed = parsearCallback(cq.data ?? "");
  if (!parsed) {
    await enviarMensaje(chat.id, TEXTO_AYUDA, { replyMarkup: tecladoMenu() });
    return;
  }
  const { tipo, args } = parsed;
  const chatId = chat.id;

  switch (tipo) {
    case "menu": {
      if (args[0] === "servicios") await mostrarServicios(chatId);
      else if (args[0] === "agendar") await mostrarServiciosParaAgendar(chatId);
      else if (args[0] === "micita") await mostrarMiCita(chatId, from.id);
      else await enviarMensaje(chatId, TEXTO_AYUDA, { replyMarkup: tecladoMenu() });
      return;
    }
    case "volver":
      await enviarMensaje(chatId, TEXTO_AYUDA, { replyMarkup: tecladoMenu() });
      return;
    case "servicio": {
      const servicioId = Number(args[0]);
      await mostrarDias(chatId, servicioId);
      return;
    }
    case "dia": {
      const servicioId = Number(args[0]);
      const ymd = desdeCompacto(args[1] ?? "");
      await mostrarHorarios(chatId, servicioId, ymd);
      return;
    }
    case "horario": {
      const servicioId = Number(args[0]);
      const horarioId = Number(args[1]);
      await mostrarResumen(chatId, servicioId, horarioId);
      return;
    }
    case "enviar": {
      const servicioId = Number(args[0]);
      const horarioId = Number(args[1]);
      await solicitar(chatId, from, servicioId, horarioId, updateId);
      return;
    }
    case "cancelar": {
      const citaId = Number(args[0]);
      await pedirConfirmacionCancelar(chatId, citaId);
      return;
    }
    case "cancelar_ok": {
      const citaId = Number(args[0]);
      await cancelar(chatId, from, citaId, updateId);
      return;
    }
    case "confirmar": {
      const citaId = Number(args[0]);
      await decidirResponsable(chatId, from, citaId, "confirmar", updateId);
      return;
    }
    case "rechazar": {
      const citaId = Number(args[0]);
      await decidirResponsable(chatId, from, citaId, "rechazar", updateId);
      return;
    }
    case "pend_sig": {
      const lastId = Number(args[0]);
      await mostrarPendientes(chatId, from.id, updateId, lastId);
      return;
    }
    default:
      await enviarMensaje(chatId, TEXTO_AYUDA, { replyMarkup: tecladoMenu() });
  }
}

// ---------- Pantallas ----------
async function mostrarServicios(chatId: number): Promise<void> {
  const servicios = await listarServicios();
  const lineas = servicios.map((s) =>
    `• ${s.nombre}: ${money(s.precio_cop)} (${s.duracion_min} min)`
  );
  await enviarMensaje(
    chatId,
    "Nuestros servicios:\n\n" + lineas.join("\n") +
      "\n\nTodos ocupan un bloque de 60 minutos.",
    {
      replyMarkup: {
        inline_keyboard: [
          [{ text: "Agendar", callback_data: "menu:agendar" }],
          [{ text: "Mi cita", callback_data: "menu:micita" }],
        ],
      },
    },
  );
}

async function mostrarServiciosParaAgendar(chatId: number): Promise<void> {
  const servicios = await listarServicios();
  const botones: Boton[] = servicios.map((s) => ({
    text: s.nombre,
    callback_data: `servicio:${s.id}`,
  }));
  await enviarMensaje(
    chatId,
    "¿Qué servicio deseas agendar?",
    { replyMarkup: { inline_keyboard: filas(botones, 1) } },
  );
}

async function mostrarDias(chatId: number, servicioId: number): Promise<void> {
  const servicio = await obtenerServicio(servicioId);
  if (!servicio) {
    await enviarMensaje(chatId, "Ese servicio no está disponible.", { replyMarkup: tecladoMenu() });
    return;
  }
  const botones: Boton[] = proximosDias().map((ymd) => ({
    text: etiquetaDia(ymd),
    callback_data: `dia:${servicioId}:${compacto(ymd)}`,
  }));
  await enviarMensaje(
    chatId,
    `${servicio.nombre}. ¿Para qué día?`,
    { replyMarkup: { inline_keyboard: filas(botones, 2) } },
  );
}

async function mostrarHorarios(
  chatId: number,
  servicioId: number,
  ymd: string,
): Promise<void> {
  const horarios = (await listarHorariosFuturos()).filter(
    (h) => ymdBogota(new Date(h.inicio)) === ymd,
  );
  if (horarios.length === 0) {
    await enviarMensaje(
      chatId,
      "No hay horarios disponibles para ese día. Elige otro día.",
      { replyMarkup: { inline_keyboard: [[{ text: "Volver", callback_data: "volver" }]] } },
    );
    return;
  }
  const botones: Boton[] = horarios.map((h) => ({
    text: horaBogota(h.inicio),
    callback_data: `horario:${servicioId}:${h.id}`,
  }));
  await enviarMensaje(
    chatId,
    "Elige un horario:",
    { replyMarkup: { inline_keyboard: filas(botones, 3) } },
  );
}

async function mostrarResumen(
  chatId: number,
  servicioId: number,
  horarioId: number,
): Promise<void> {
  const [servicio, horario] = await Promise.all([
    obtenerServicio(servicioId),
    obtenerHorario(horarioId),
  ]);
  if (!servicio || !horario) {
    await enviarMensaje(chatId, "Ese horario ya no está disponible.", { replyMarkup: tecladoMenu() });
    return;
  }
  const texto =
    `Resumen de tu solicitud:\n\n` +
    `Servicio: ${servicio.nombre}\n` +
    `Día: ${fechaLarga(horario.inicio)}\n` +
    `Hora: ${horaBogota(horario.inicio)}\n` +
    `Precio: ${money(servicio.precio_cop)}\n\n` +
    `El horario todavía no está reservado. Pulsa Enviar solicitud para crearla. Quedará pendiente de confirmación.`;
  await enviarMensaje(chatId, texto, {
    replyMarkup: {
      inline_keyboard: [
        [{ text: "Enviar solicitud", callback_data: `enviar:${servicioId}:${horarioId}` }],
        [{ text: "Volver al inicio", callback_data: "volver" }],
      ],
    },
  });
}

async function solicitar(
  chatId: number,
  from: TgUser,
  servicioId: number,
  horarioId: number,
  updateId: number,
): Promise<void> {
  const r = await mutarCita({
    updateId,
    accion: "solicitar",
    actorUserId: from.id,
    actorChatId: chatId,
    actorNombre: from.first_name ?? "",
    servicioId,
    horarioId,
    adminUserId: ADMIN_USER_ID > 0 ? ADMIN_USER_ID : null,
    adminChatId: ADMIN_CHAT_ID > 0 ? ADMIN_CHAT_ID : null,
  });
  await enviarMensaje(chatId, mensajeSolicitud(r), { replyMarkup: tecladoMenu() });
}

async function mostrarMiCita(chatId: number, userId: number): Promise<void> {
  const cita = await obtenerCitaActiva(userId);
  if (!cita) {
    await enviarMensaje(chatId, "No tienes una cita activa.", { replyMarkup: tecladoMenu() });
    return;
  }
  const texto = await textoCita(cita);
  await enviarMensaje(chatId, texto, {
    replyMarkup: {
      inline_keyboard: [[{ text: "Cancelar cita", callback_data: `cancelar:${cita.id}` }]],
    },
  });
}

async function pedirConfirmacionCancelar(chatId: number, citaId: number): Promise<void> {
  await enviarMensaje(
    chatId,
    `¿Confirmas que deseas cancelar la cita #${citaId}?`,
    {
      replyMarkup: {
        inline_keyboard: [
          [{ text: "Sí, cancelar", callback_data: `cancelar_ok:${citaId}` }],
          [{ text: "No, volver", callback_data: "menu:micita" }],
        ],
      },
    },
  );
}

async function cancelar(
  chatId: number,
  from: TgUser,
  citaId: number,
  updateId: number,
): Promise<void> {
  const r = await mutarCita({
    updateId,
    accion: "cancelar",
    actorUserId: from.id,
    actorChatId: chatId,
    actorNombre: from.first_name ?? "",
    citaId,
    adminUserId: ADMIN_USER_ID > 0 ? ADMIN_USER_ID : null,
    adminChatId: ADMIN_CHAT_ID > 0 ? ADMIN_CHAT_ID : null,
  });
  await enviarMensaje(chatId, mensajeTransicion(r.codigo), { replyMarkup: tecladoMenu() });
}

async function decidirResponsable(
  chatId: number,
  from: TgUser,
  citaId: number,
  accion: "confirmar" | "rechazar",
  updateId: number,
): Promise<void> {
  if (ADMIN_USER_ID <= 0 || from.id !== ADMIN_USER_ID) {
    await enviarMensaje(chatId, "No tienes permiso para esta acción.");
    return;
  }
  const r = await mutarCita({
    updateId,
    accion,
    actorUserId: from.id,
    actorChatId: chatId,
    actorNombre: from.first_name ?? "",
    citaId,
    adminUserId: ADMIN_USER_ID,
    adminChatId: ADMIN_CHAT_ID > 0 ? ADMIN_CHAT_ID : null,
  });
  const base = mensajeTransicion(r.codigo);
  await enviarMensaje(chatId, `Cita #${citaId}: ${base}`);
}

async function mostrarPendientes(
  chatId: number,
  userId: number,
  _updateId: number,
  antesDeId?: number,
): Promise<void> {
  if (ADMIN_USER_ID <= 0 || userId !== ADMIN_USER_ID) {
    await enviarMensaje(chatId, "No tienes permiso para /pendientes.");
    return;
  }
  const citas = await listarCitasPendientes(10, antesDeId);
  if (citas.length === 0) {
    await enviarMensaje(chatId, "No hay solicitudes pendientes.", { replyMarkup: tecladoMenu() });
    return;
  }
  const bloques: string[] = [];
  const botones: Boton[][] = [];
  for (const c of citas) {
    bloques.push(await textoCita(c));
    botones.push([
      { text: `Confirmar #${c.id}`, callback_data: `confirmar:${c.id}` },
      { text: `Rechazar #${c.id}`, callback_data: `rechazar:${c.id}` },
    ]);
  }
  if (citas.length === 10) {
    const ultimo = citas[citas.length - 1].id;
    botones.push([{ text: "Ver más", callback_data: `pend_sig:${ultimo}` }]);
  }
  await enviarMensaje(chatId, bloques.join("\n\n"), {
    replyMarkup: { inline_keyboard: botones },
  });
}

async function reintentar(chatId: number, userId: number): Promise<void> {
  if (ADMIN_USER_ID <= 0 || userId !== ADMIN_USER_ID) {
    await enviarMensaje(chatId, "No tienes permiso para /reintentar.");
    return;
  }
  const r = await procesarAvisosPendientes(10);
  await enviarMensaje(
    chatId,
    `Avisos procesados: enviados ${r.enviadas}, fallidos ${r.fallidas}, revisión ${r.revision}, pendientes ${r.pendientes}.`,
  );
}

// ---------- Cola de avisos ----------
export interface ResumenAvisos {
  enviadas: number;
  fallidas: number;
  revision: number;
  pendientes: number;
}

export async function procesarAvisosPendientes(limite = 5): Promise<ResumenAvisos> {
  const resumen: ResumenAvisos = { enviadas: 0, fallidas: 0, revision: 0, pendientes: 0 };
  let avisos: Notificacion[] = [];
  try {
    avisos = await reclamarAvisos(limite, 300);
  } catch {
    return resumen;
  }

  for (const a of avisos) {
    if (!a.lease_token) continue;
    try {
      const texto = await textoAviso(a);
      const msg = await enviarMensaje(a.chat_id, texto);
      await finalizarAviso(a.id, a.lease_token, "enviada", msg.message_id ?? null);
      resumen.enviadas++;
    } catch (e) {
      const clas = clasificarError(e);
      try {
        await finalizarAviso(
          a.id,
          a.lease_token,
          clas.resultado,
          null,
          clas.codigo,
          clas.retrySeg,
        );
      } catch {
        // Si no se puede finalizar, el lease vence y se reintenta luego.
      }
      if (clas.resultado === "fallida") resumen.fallidas++;
      else if (clas.resultado === "revision") resumen.revision++;
      else resumen.pendientes++;
    }
  }
  return resumen;
}

function clasificarError(
  e: unknown,
): {
  resultado: "enviada" | "reintentable" | "fallida" | "revision";
  codigo: string;
  retrySeg?: number;
} {
  if (e instanceof TelegramError) {
    if (e.code === 429) {
      return { resultado: "reintentable", codigo: "429", retrySeg: e.retryAfter ?? 30 };
    }
    if (e.code === 403) return { resultado: "fallida", codigo: "403" };
    if (e.code >= 400 && e.code < 500) return { resultado: "fallida", codigo: String(e.code) };
    return { resultado: "reintentable", codigo: String(e.code) };
  }
  const msg = e instanceof Error ? e.message : "desconocido";
  if (msg.includes("timeout") || msg.includes("no interpretable")) {
    return { resultado: "revision", codigo: "incierto" };
  }
  if (msg.includes("conectar")) {
    return { resultado: "reintentable", codigo: "red" };
  }
  return { resultado: "revision", codigo: "desconocido" };
}

async function textoAviso(n: Notificacion): Promise<string> {
  const estado = n.payload.estado ?? "pendiente";
  const destino = n.payload.destino ?? "cliente";
  const citaId = n.payload.cita_id ?? n.cita_id ?? 0;

  let detalle = "";
  if (n.cita_id) {
    const cita = await obtenerCita(n.cita_id);
    if (cita) detalle = await textoCita(cita);
  }

  if (destino === "responsable") {
    if (estado === "pendiente") {
      return `Nueva solicitud de cita.\n\n${detalle}\n\nUsa /pendientes para confirmar o rechazar.`;
    }
    return `Actualización de la cita #${citaId}: ${estado}.\n\n${detalle}`;
  }

  switch (estado) {
    case "pendiente":
      return `Recibimos tu solicitud.\n\n${detalle}\n\nQueda pendiente de confirmación por el responsable.`;
    case "confirmada":
      return `Tu cita fue confirmada.\n\n${detalle}`;
    case "rechazada":
      return `Tu solicitud fue rechazada.\n\n${detalle}\n\nPuedes solicitar otro horario.`;
    case "cancelada":
      return `Tu cita fue cancelada.\n\n${detalle}`;
    default:
      return `Actualización de tu cita #${citaId}: ${estado}.`;
  }
}

async function textoCita(cita: Cita): Promise<string> {
  const [servicio, horario] = await Promise.all([
    obtenerServicio(cita.servicio_id),
    obtenerHorario(cita.horario_id),
  ]);
  const nombreServicio = servicio?.nombre ?? `Servicio ${cita.servicio_id}`;
  const cuando = horario
    ? `${fechaLarga(horario.inicio)} a las ${horaBogota(horario.inicio)}`
    : "horario no disponible";
  return `Cita #${cita.id}\nServicio: ${nombreServicio}\nHorario: ${cuando}\nEstado: ${cita.estado}`;
}

function mensajeSolicitud(r: { ok: boolean; codigo: string; cita_id?: number }): string {
  switch (r.codigo) {
    case "solicitada":
      return `Solicitud registrada. Número de cita: ${r.cita_id}.\n\nQueda pendiente de confirmación por el responsable.`;
    case "cita_activa":
      return "Ya tienes una cita activa. Cancélala antes de solicitar otra.";
    case "horario_ocupado":
      return "Ese horario acaba de ser ocupado. Elige otro horario.";
    case "horario_vencido":
      return "Ese horario ya pasó. Elige otro día.";
    case "horario_invalido":
      return "El horario ya no está disponible. Elige otro.";
    case "servicio_invalido":
      return "Ese servicio no está disponible.";
    case "duplicado":
      return "Esta solicitud ya fue procesada.";
    default:
      return "No se pudo crear la solicitud. Intenta de nuevo.";
  }
}

function mensajeTransicion(codigo: string): string {
  switch (codigo) {
    case "confirmada":
      return "confirmada. Se avisará a la clienta.";
    case "rechazada":
      return "rechazada. La clienta podrá solicitar otro horario.";
    case "cancelada":
      return "cancelada. El horario quedó liberado.";
    case "sin_permiso":
      return "no tienes permiso para hacerlo.";
    case "estado_invalido":
      return "ya no está pendiente o cambió de estado.";
    case "horario_vencido":
      return "el horario ya pasó.";
    case "cita_inexistente":
      return "no existe.";
    case "duplicado":
      return "ya fue procesada.";
    default:
      return "no se pudo completar la acción.";
  }
}
