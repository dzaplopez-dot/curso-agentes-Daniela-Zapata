from . import nlu, repository
from .repository import HerramientaError
from .texto import formatear_precio, titulo

AYUDA = (
    "Hola, soy el asesor de EFY. Te ayudo a encontrar un perfume y a dejar el pedido listo.\n\n"
    "Puedes pedirme cosas como:\n"
    "• \"algo como Sauvage para hombre\"\n"
    "• \"un perfume floral para mujer\"\n"
    "• \"amaderado, dos unidades\"\n"
    "• o escribe un código, por ejemplo 3859\n\n"
    "Todas las referencias son de 100 ml y cuestan $40.000.\n"
    "Te muestro opciones reales del catálogo y solo confirmo cuando me digas SÍ."
)

SIN_FILTROS = (
    "Para recomendarte necesito un poco más de contexto. ¿Es para hombre, mujer o unisex? "
    "¿Y qué familia te gusta: floral, frutal, amaderada, oriental, aromática o cítrica?\n\n"
    "Ejemplo: \"amaderado para hombre\"."
)

FAMILIAS = "floral, amaderada, oriental, aromática, cítrica, chipre o ambarada"


class Agente:
    def __init__(self, repositorio=None):
        self.repo = repositorio or repository

    def responder(self, chat_id, texto, msg_id):
        try:
            return self._responder(chat_id, texto, msg_id)
        except HerramientaError as exc:
            return self._error(exc)

    def _error(self, exc):
        motivos = {
            "catalogo_no_disponible": (
                "No pude consultar el catálogo en este momento, así que no registré ningún pedido. "
                "El estado no cambió; intenta de nuevo en un momento."
            ),
            "base_no_disponible": (
                "No pude guardar en la base de datos, así que el pedido no quedó registrado. "
                "Puedes intentarlo otra vez."
            ),
            "referencia_no_existe": "No encontré esa referencia en el catálogo.",
            "stock_insuficiente": (
                "No hay stock suficiente para esa cantidad. El pedido no se creó. "
                "Prueba con menos unidades o con otra referencia."
            ),
            "sin_borrador": (
                "No tengo un borrador pendiente. Primero dime qué perfume te interesa y armo uno."
            ),
            "pedido_cancelado": "Ese pedido está cancelado. Empecemos otro desde cero.",
        }
        return motivos.get(exc.motivo, "No pude completar la operación y no se guardó nada.")

    def _responder(self, chat_id, texto, msg_id):
        datos = nlu.interpretar(
            texto, self.repo.nombres_conocidos(), self.repo.casas_conocidas()
        )
        intencion = datos["intencion"]

        if intencion == "saludo":
            return AYUDA
        if intencion == "confirmar":
            return self._confirmar(chat_id)
        if intencion == "cancelar":
            return self._cancelar(chat_id)

        if datos["codigo"]:
            p = self.repo.ficha(datos["codigo"])
            if p:
                return self._borrador(chat_id, p, datos["cantidad"], msg_id)

        return self._buscar(datos, chat_id, msg_id)

    def _buscar(self, datos, chat_id, msg_id):
        filtros = {
            clave: datos.get(clave) for clave in ("inspirado", "casa", "familia", "genero")
        }
        if not any(filtros.values()):
            return SIN_FILTROS

        filas = self.repo.buscar(limite=6, **filtros)

        if not filas and datos["genero"] == "U":
            filtros.pop("genero")
            filas = self.repo.buscar(limite=6, **filtros)
            if filas:
                return self._lista(
                    filas,
                    "No tenemos referencias unisex para esa búsqueda. Estas son las más cercanas:",
                )

        if not filas and datos["inspirado"]:
            alternativas = self.repo.buscar(
                familia=datos["familia"], genero=datos["genero"], limite=5
            ) if (datos["familia"] or datos["genero"]) else []
            if alternativas:
                return self._lista(
                    alternativas,
                    f"No manejamos inspirado en {datos['inspirado']}. "
                    f"En la misma línea tenemos:",
                )
            return (
                f"No manejamos inspirado en {datos['inspirado']} y no lo voy a inventar. "
                f"¿Qué familia te gusta? Trabajo con {FAMILIAS}."
            )

        if not filas:
            return (
                "No encontré referencias con esos datos. Prueba con otra familia olfativa "
                f"({FAMILIAS}) o con otra casa."
            )

        if len(filas) == 1:
            return self._borrador(chat_id, filas[0], datos["cantidad"], msg_id)

        return self._lista(filas, f"Encontré {len(filas)} referencias:")

    def _linea(self, f):
        return (
            f"• {f['codigo']} · {f['inspirado_en']} ({f['casa']})\n"
            f"  {titulo(f['familia_raw'])} · {f['ml']} ml · "
            f"{formatear_precio(f['precio'])} · stock {f['stock']}"
        )

    def _lista(self, filas, encabezado):
        cuerpo = "\n".join(self._linea(f) for f in filas)
        return (
            f"{encabezado}\n\n{cuerpo}\n\n"
            "Todas son de 100 ml y cuestan $40.000. "
            "Responde con el código de la que quieras y armo el borrador del pedido."
        )

    def _borrador(self, chat_id, p, cantidad, msg_id):
        r = self.repo.crear_borrador(chat_id, p["codigo"], cantidad, msg_id)
        pedido = r["pedido"]
        total = float(p["precio"]) * int(pedido["cantidad"])
        detalle = (
            f"{pedido['cantidad']} × {p['codigo']} {p['inspirado_en']} "
            f"({p['casa']}) · {p['ml']} ml\n"
            f"Total: {formatear_precio(total)}"
        )
        if r["duplicado"]:
            return (
                f"Ya tenía registrado este mensaje: pedido #{pedido['id']} en estado "
                f"{pedido['estado']}. No lo dupliqué.\n\n{detalle}"
            )
        return (
            f"Borrador #{pedido['id']}\n{detalle}\n\n"
            "Responde SÍ para confirmar o NO para cancelar. "
            "Todavía no se descontó stock."
        )

    def _confirmar(self, chat_id):
        r = self.repo.confirmar(chat_id)
        if r["estado"] == "ya_confirmado":
            pedido = r["pedido"]
            return (
                f"El pedido #{pedido['id']} ya estaba confirmado y no lo cobré dos veces. "
                "No se descontó stock otra vez."
            )
        pedido = r["pedido"]
        p = r["perfume"]
        total = float(p["precio"]) * int(pedido["cantidad"])
        return (
            f"Pedido #{pedido['id']} confirmado.\n"
            f"{pedido['cantidad']} × {p['codigo']} {p['inspirado_en']} · "
            f"{formatear_precio(total)}\n"
            f"Stock restante de {p['codigo']}: {p['stock']} unidades.\n"
            "Puedes recogerlo en el local o pedir envío."
        )

    def _cancelar(self, chat_id):
        self.repo.cancelar(chat_id)
        return "Pedido cancelado. No se descontó stock y puedes empezar de nuevo cuando quieras."
