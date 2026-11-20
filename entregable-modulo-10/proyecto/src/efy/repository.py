from datetime import datetime, timezone

from . import config, db
from .texto import normalizar


class HerramientaError(Exception):
    def __init__(self, motivo, detalle=None):
        super().__init__(motivo)
        self.motivo = motivo
        self.detalle = detalle


def _ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _filas(con):
    return [dict(r) for r in con.execute("SELECT * FROM perfumes WHERE activo = 1")]


def listar_todo():
    try:
        with db.conectar() as con:
            return _filas(con)
    except db.error_db() as exc:
        raise HerramientaError("catalogo_no_disponible", str(exc)) from exc


def nombres_conocidos():
    return sorted({f["inspirado_en"] for f in listar_todo()})


def casas_conocidas():
    return sorted({f["casa"] for f in listar_todo()})


def buscar(inspirado=None, casa=None, familia=None, genero=None, limite=6):
    filas = listar_todo()
    if genero:
        filas = [f for f in filas if f["genero"] == genero]
    if familia:
        objetivo = normalizar(familia)
        filas = [f for f in filas if normalizar(f["familia_base"]) == objetivo]
    if casa:
        filas = [f for f in filas if normalizar(casa) in normalizar(f["casa"])]
    if inspirado:
        filas = [f for f in filas if normalizar(inspirado) in normalizar(f["inspirado_en"])]
    filas.sort(key=lambda f: (f["inspirado_en"], f["codigo"]))
    return filas[:limite]


def ficha(codigo):
    try:
        with db.conectar() as con:
            row = con.execute(
                "SELECT * FROM perfumes WHERE codigo = ? AND activo = 1", (str(codigo),)
            ).fetchone()
    except db.error_db() as exc:
        raise HerramientaError("catalogo_no_disponible", str(exc)) from exc
    return dict(row) if row else None


def ver_stock(codigo):
    p = ficha(codigo)
    if not p:
        raise HerramientaError("referencia_no_existe", str(codigo))
    return p["stock"]


def stock_bajo(umbral=None):
    umbral = config.STOCK_BAJO if umbral is None else umbral
    filas = [f for f in listar_todo() if f["stock"] <= umbral]
    filas.sort(key=lambda f: f["stock"])
    return filas


def _sesion(con, chat_id):
    row = con.execute("SELECT * FROM sesiones WHERE chat_id = ?", (chat_id,)).fetchone()
    return dict(row) if row else None


def _guardar_sesion(con, chat_id, pedido_id):
    con.execute(
        """
        INSERT INTO sesiones (chat_id, pedido_id, actualizado_en) VALUES (?, ?, ?)
        ON CONFLICT (chat_id) DO UPDATE SET pedido_id = excluded.pedido_id,
                                            actualizado_en = excluded.actualizado_en
        """,
        (chat_id, pedido_id, _ahora()),
    )


def _insertar_pedido(con, chat_id, codigo, cantidad, msg_id):
    sql = (
        "INSERT INTO pedidos (chat_id, codigo, cantidad, msg_id, creado_en) "
        "VALUES (?, ?, ?, ?, ?)"
    )
    params = (chat_id, codigo, cantidad, msg_id, _ahora())
    if con.dialecto == "postgres":
        return con.execute(sql + " RETURNING id", params).fetchone()["id"]
    return con.execute(sql, params).lastrowid


def crear_borrador(chat_id, codigo, cantidad, msg_id):
    cantidad = max(1, int(cantidad or 1))
    try:
        with db.conectar() as con:
            p = con.execute(
                "SELECT * FROM perfumes WHERE codigo = ? AND activo = 1", (str(codigo),)
            ).fetchone()
            if not p:
                raise HerramientaError("referencia_no_existe", str(codigo))
            if p["stock"] < cantidad:
                raise HerramientaError("stock_insuficiente", f"{p['stock']} < {cantidad}")
            try:
                pedido_id = _insertar_pedido(con, chat_id, str(codigo), cantidad, str(msg_id))
            except db.error_integridad():
                previo = con.execute(
                    "SELECT * FROM pedidos WHERE chat_id = ? AND msg_id = ?",
                    (chat_id, str(msg_id)),
                ).fetchone()
                _guardar_sesion(con, chat_id, previo["id"])
                return {"duplicado": True, "pedido": dict(previo), "perfume": dict(p)}
            _guardar_sesion(con, chat_id, pedido_id)
            pedido = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
            return {"duplicado": False, "pedido": dict(pedido), "perfume": dict(p)}
    except db.error_db() as exc:
        raise HerramientaError("base_no_disponible", str(exc)) from exc


def confirmar(chat_id):
    try:
        with db.conectar() as con:
            sesion = _sesion(con, chat_id)
            if not sesion or not sesion["pedido_id"]:
                raise HerramientaError("sin_borrador")
            pedido = con.execute(
                "SELECT * FROM pedidos WHERE id = ?", (sesion["pedido_id"],)
            ).fetchone()
            if not pedido:
                raise HerramientaError("sin_borrador")
            if pedido["estado"] == "confirmado":
                return {"estado": "ya_confirmado", "pedido": dict(pedido)}
            if pedido["estado"] == "cancelado":
                raise HerramientaError("pedido_cancelado")
            cur = con.execute(
                "UPDATE perfumes SET stock = stock - ? WHERE codigo = ? AND stock >= ?",
                (pedido["cantidad"], pedido["codigo"], pedido["cantidad"]),
            )
            if cur.rowcount == 0:
                raise HerramientaError("stock_insuficiente", pedido["codigo"])
            con.execute("UPDATE pedidos SET estado = 'confirmado' WHERE id = ?", (pedido["id"],))
            p = con.execute(
                "SELECT * FROM perfumes WHERE codigo = ?", (pedido["codigo"],)
            ).fetchone()
            confirmado = con.execute(
                "SELECT * FROM pedidos WHERE id = ?", (pedido["id"],)
            ).fetchone()
            return {"estado": "confirmado", "pedido": dict(confirmado), "perfume": dict(p)}
    except db.error_db() as exc:
        raise HerramientaError("base_no_disponible", str(exc)) from exc


def cancelar(chat_id):
    try:
        with db.conectar() as con:
            sesion = _sesion(con, chat_id)
            if not sesion or not sesion["pedido_id"]:
                raise HerramientaError("sin_borrador")
            con.execute(
                "UPDATE pedidos SET estado = 'cancelado' WHERE id = ? AND estado = 'borrador'",
                (sesion["pedido_id"],),
            )
            _guardar_sesion(con, chat_id, None)
            return {"ok": True}
    except db.error_db() as exc:
        raise HerramientaError("base_no_disponible", str(exc)) from exc


def pedidos(estado=None):
    try:
        with db.conectar() as con:
            sql = """
                SELECT p.id, p.chat_id, p.codigo, p.cantidad, p.estado, p.creado_en,
                       f.inspirado_en, f.casa, f.familia_base, f.precio, f.ml
                FROM pedidos p JOIN perfumes f ON f.codigo = p.codigo
            """
            params = ()
            if estado:
                sql += " WHERE p.estado = ?"
                params = (estado,)
            sql += " ORDER BY p.id DESC"
            return [dict(r) for r in con.execute(sql, params)]
    except db.error_db() as exc:
        raise HerramientaError("base_no_disponible", str(exc)) from exc
