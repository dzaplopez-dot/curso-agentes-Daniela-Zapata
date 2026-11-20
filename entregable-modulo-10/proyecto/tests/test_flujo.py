from efy import repository
from efy.repository import HerramientaError
from efy.texto import normalizar


def test_normalizacion_de_familias():
    assert normalizar("Aromática") == normalizar("AROMATICA")
    assert normalizar("FLORAL-MADEROSA") == "FLORAL MADEROSA"
    assert normalizar("Fougére") == normalizar("FOUGERE")


def test_catalogo_carga_las_80_referencias(agente):
    filas = repository.listar_todo()
    assert len(filas) == 80
    assert len({f["codigo"] for f in filas}) == 80
    assert {f["genero"] for f in filas} == {"F", "M", "U"}
    assert all(f["ml"] == 100 for f in filas)
    assert all(float(f["precio"]) == 40000 for f in filas)
    assert all(f["stock"] == 10 for f in filas)


def test_caso_normal_con_desambiguacion_y_confirmacion(agente):
    respuesta = agente.responder("u1", "busco algo como sauvage para hombre", "m1")
    assert "3859" in respuesta
    assert "2069" in respuesta
    assert "100 ml" in respuesta
    assert "$40.000" in respuesta

    respuesta = agente.responder("u1", "3859", "m2")
    assert "Borrador #" in respuesta
    assert "Todavía no se descontó stock" in respuesta

    respuesta = agente.responder("u1", "si", "m3")
    assert "confirmado" in respuesta
    assert "Stock restante de 3859: 9" in respuesta


def test_dato_ambiguo_pregunta_en_vez_de_adivinar(agente):
    respuesta = agente.responder("u2", "quiero chance", "m1")
    assert "893" in respuesta
    assert "3647" in respuesta
    assert "Responde con el código" in respuesta


def test_sin_coincidencia_no_inventa(agente):
    respuesta = agente.responder("u3", "quiero baccarat rouge", "m1")
    assert "No manejamos inspirado en" in respuesta
    assert "BACCARAT ROUGE" in respuesta
    assert repository.pedidos() == []


def test_dato_faltante_pide_contexto(agente):
    respuesta = agente.responder("u4", "algo rico", "m1")
    assert "necesito un poco más de contexto" in respuesta
    assert repository.pedidos() == []


def test_mensaje_repetido_no_duplica(agente):
    primera = agente.responder("u5", "dos unidades de 440", "m1")
    segunda = agente.responder("u5", "dos unidades de 440", "m1")
    assert "Borrador #" in primera
    assert "No lo dupliqué" in segunda
    pedidos = repository.pedidos()
    assert len(pedidos) == 1
    assert pedidos[0]["cantidad"] == 2


def test_falla_de_herramienta_no_anuncia_exito(agente, monkeypatch):
    def caido(*args, **kwargs):
        raise HerramientaError("catalogo_no_disponible", "simulado")

    monkeypatch.setattr(repository, "buscar", caido)
    respuesta = agente.responder("u6", "algo como sauvage", "m1")
    assert "No pude consultar el catálogo" in respuesta
    assert repository.pedidos() == []


def test_doble_confirmacion_no_descuenta_dos_veces(agente):
    agente.responder("u7", "3859", "m1")
    agente.responder("u7", "si", "m2")
    respuesta = agente.responder("u7", "si", "m3")
    assert "ya estaba confirmado" in respuesta
    assert repository.ver_stock("3859") == 9


def test_cancelar_no_descuenta_stock(agente):
    agente.responder("u8", "3859", "m1")
    respuesta = agente.responder("u8", "no", "m2")
    assert "cancelado" in respuesta
    assert repository.ver_stock("3859") == 10


def test_unisex_limitado_ofrece_alternativas(agente):
    respuesta = agente.responder("u9", "unisex floral", "m1")
    assert "No tenemos referencias unisex" in respuesta
    assert "Responde con el código" in respuesta


def test_busqueda_por_casa(agente):
    respuesta = agente.responder("u10", "algo de christian dior", "m1")
    assert "3859" in respuesta
    assert "2069" in respuesta
    assert "718" in respuesta
