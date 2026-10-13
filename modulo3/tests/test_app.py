from src.app import main, responder


def test_app_inicia(capsys):
    main()
    salida = capsys.readouterr().out
    assert "ASISTENTE DE INVENTARIO" in salida


def test_codigo_valido():
    r = responder("FER-0001")
    assert "FER-0001" in r
    assert "Fuente" in r


def test_producto_inexistente_no_inventa():
    r = responder("XXX-9999")
    assert "no existe" in r.lower()


def test_nombre_ambiguo_pide_precision():
    r = responder("busca Martillo")
    assert "coincidencia" in r.lower() or "precisa" in r.lower()


def test_stock_bajo_propone():
    r = responder("bajo minimo")
    assert "sugerido" in r.lower() or "propuesta" in r.lower() or "bajo el mínimo" in r.lower()


def test_lote_vencido_separa():
    r = responder("vencidos")
    assert "vencido" in r.lower()
    assert "Fuente" in r


def test_escritura_no_autorizada_rechaza():
    r = responder("cambia el stock de FER-0001 a 500")
    assert "RECHAZADO" in r or "no puedo modificar" in r.lower()
