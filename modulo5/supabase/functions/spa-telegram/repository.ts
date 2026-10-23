import { createClient, SupabaseClient } from "@supabase/supabase-js";

/** Lee la clave de servidor inyectada por Supabase, sin copiarla a .env. */
function claveServidor(): string {
  const dicc = Deno.env.get("SUPABASE_SECRET_KEYS");
  if (dicc) {
    try {
      const obj = JSON.parse(dicc);
      if (obj && typeof obj === "object") {
        if (typeof obj.default === "string") return obj.default;
        const primero = Object.values(obj).find((v) => typeof v === "string");
        if (typeof primero === "string") return primero;
      }
    } catch {
      // Ignorar y probar el respaldo.
    }
  }
  return Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
}

let cliente: SupabaseClient | null = null;

function db(): SupabaseClient {
  if (cliente) return cliente;
  const url = Deno.env.get("SUPABASE_URL") ?? "";
  const key = claveServidor();
  if (!url || !key) {
    throw new Error("SUPABASE_URL o clave de servidor no disponibles en el entorno.");
  }
  cliente = createClient(url, key, { auth: { persistSession: false } });
  return cliente;
}

export interface Servicio {
  id: number;
  nombre: string;
  precio_cop: number;
  duracion_min: number;
  activo: boolean;
}

export interface Horario {
  id: number;
  inicio: string;
  fin: string;
}

export interface Cita {
  id: number;
  cliente_user_id: number;
  cliente_chat_id: number;
  cliente_nombre: string;
  servicio_id: number;
  horario_id: number;
  estado: "pendiente" | "confirmada" | "cancelada" | "rechazada" | "finalizada";
  created_at: string;
}

export interface Notificacion {
  id: number;
  clave: string;
  cita_id: number | null;
  chat_id: number;
  payload: { cita_id?: number; estado?: string; destino?: string };
  estado: "pendiente" | "procesando" | "enviada" | "fallida" | "revision";
  intentos: number;
  disponible_desde: string;
  lease_hasta: string | null;
  lease_token: string | null;
  telegram_message_id: number | null;
  error_codigo: string | null;
  created_at: string;
}

export interface ResultadoMutacion {
  ok: boolean;
  codigo: string;
  cita_id?: number;
}

export type AccionCita = "solicitar" | "confirmar" | "rechazar" | "cancelar";

export async function listarServicios(): Promise<Servicio[]> {
  const { data, error } = await db()
    .from("spa_servicios")
    .select("id, nombre, precio_cop, duracion_min, activo")
    .eq("activo", true)
    .order("id");
  if (error) throw error;
  return (data ?? []) as Servicio[];
}

export async function obtenerServicio(id: number): Promise<Servicio | null> {
  const { data, error } = await db()
    .from("spa_servicios")
    .select("id, nombre, precio_cop, duracion_min, activo")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return (data as Servicio) ?? null;
}

export async function generarHorarios(): Promise<number> {
  const { data, error } = await db().rpc("spa_generar_horarios");
  if (error) throw error;
  return Number(data ?? 0);
}

export async function listarHorariosFuturos(limite = 120): Promise<Horario[]> {
  const { data, error } = await db()
    .from("spa_horarios")
    .select("id, inicio, fin")
    .gt("inicio", new Date().toISOString())
    .order("inicio", { ascending: true })
    .limit(limite);
  if (error) throw error;
  return (data ?? []) as Horario[];
}

export async function obtenerHorario(id: number): Promise<Horario | null> {
  const { data, error } = await db()
    .from("spa_horarios")
    .select("id, inicio, fin")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return (data as Horario) ?? null;
}

export async function obtenerCita(id: number): Promise<Cita | null> {
  const { data, error } = await db()
    .from("spa_citas")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return (data as Cita) ?? null;
}

export async function obtenerCitaActiva(clienteUserId: number): Promise<Cita | null> {
  const { data, error } = await db()
    .from("spa_citas")
    .select("*")
    .eq("cliente_user_id", clienteUserId)
    .in("estado", ["pendiente", "confirmada"])
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  return (data as Cita) ?? null;
}

export async function listarCitasPendientes(
  limite = 10,
  antesDeId?: number,
): Promise<Cita[]> {
  let q = db()
    .from("spa_citas")
    .select("*")
    .eq("estado", "pendiente")
    .order("id", { ascending: false })
    .limit(limite);
  if (antesDeId !== undefined) q = q.lt("id", antesDeId);
  const { data, error } = await q;
  if (error) throw error;
  return (data ?? []) as Cita[];
}

export interface MutarEntrada {
  updateId: number;
  accion: AccionCita;
  actorUserId: number;
  actorChatId: number;
  actorNombre?: string;
  citaId?: number | null;
  servicioId?: number | null;
  horarioId?: number | null;
  adminUserId: number | null;
  adminChatId: number | null;
}

export async function mutarCita(p: MutarEntrada): Promise<ResultadoMutacion> {
  const { data, error } = await db().rpc("spa_mutar_cita", {
    p_update_id: p.updateId,
    p_accion: p.accion,
    p_actor_user_id: p.actorUserId,
    p_actor_chat_id: p.actorChatId,
    p_actor_nombre: p.actorNombre ?? "",
    p_cita_id: p.citaId ?? null,
    p_servicio_id: p.servicioId ?? null,
    p_horario_id: p.horarioId ?? null,
    p_admin_user_id: p.adminUserId,
    p_admin_chat_id: p.adminChatId,
  });
  if (error) throw error;
  return data as ResultadoMutacion;
}

export async function reclamarAvisos(
  limite = 5,
  leaseSeg = 300,
): Promise<Notificacion[]> {
  const { data, error } = await db().rpc("spa_reclamar_avisos", {
    p_limite: limite,
    p_lease_seg: leaseSeg,
  });
  if (error) throw error;
  return (data ?? []) as Notificacion[];
}

export async function finalizarAviso(
  id: number,
  token: string,
  resultado: "enviada" | "reintentable" | "fallida" | "revision",
  messageId?: number | null,
  errorCodigo?: string | null,
  retrySeg?: number | null,
): Promise<{ ok: boolean; codigo: string }> {
  const { data, error } = await db().rpc("spa_finalizar_aviso", {
    p_id: id,
    p_token: token,
    p_resultado: resultado,
    p_message_id: messageId ?? null,
    p_error: errorCodigo ?? null,
    p_retry_seg: retrySeg ?? null,
  });
  if (error) throw error;
  return data as { ok: boolean; codigo: string };
}
