"""Pruebas del ejercicio 3: crear la venta faltante.

No llama a OpenAI ni a servicios externos. Usa bases SQLite temporales.
"""
from __future__ import annotations

import json

import pytest

from src import ejercicios
from src.db import conectar, construir, consultar_venta, migrar

EXTRACCION_OK = {
    "document_type": "card_voucher",
    "payment_brand_or_medium": "DaviPlata",
    "currency_observed": "COP",
    "operation_status_observed": "Aprobado",
    "amount_basis": "observed_total",
    "total_amount": 148000,
    "document_date": "2026-09-11",
}


def _base(tmp_path, archivo_id="ARC-1234567890ab", comprobante_id="COMP-1234567890ab"):
    """Base con archivo y comprobante revisado. Devuelve (ruta, producto de catálogo)."""
    db_path = tmp_path / "negocio.sqlite3"
    construir(db_path)
    migrar(db_path)
    with conectar(db_path) as db:
        db.execute(
            "INSERT INTO archivos_ingresados(id,sha256,nombre_original,nombre_guardado,mime,bytes,cargado_en,estado) "
            "VALUES(?,?,?,?,?,?,?,'pendiente_reconocimiento')",
            (archivo_id, "sha256-falso", "soporte.png", "aabbccdd11223344.png", "image/png", 100, "2026-09-11T12:00:00+00:00"),
        )
        db.execute(
            "INSERT INTO comprobantes(id,archivo_id,modelo,version_prompt,extraccion_original,estado_extraccion,fecha_creacion,fecha_revision,revisado_por,notas_revision) "
            "VALUES(?,?,?,?,?,'revisada',?,?,?,?)",
            (comprobante_id, archivo_id, "gpt-5.6-luna", "v1",
             json.dumps(EXTRACCION_OK, ensure_ascii=False),
             "2026-09-11T12:00:00+00:00", "2026-09-11T12:00:00+00:00", "operador", "Revisado"),
        )
        producto = dict(db.execute(
            "SELECT codigo, precio_venta FROM productos ORDER BY codigo LIMIT 1"
        ).fetchone())
        db.commit()
    return db_path, producto


def _datos(producto, **extra):
    base = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "fecha_comercial": "2026-09-11",
        "cliente": "Cliente de práctica",
        "lineas": [{"producto_codigo": producto["codigo"], "cantidad": 2}],
    }
    base.update(extra)
    return base


def test_borrador_incompleto_se_mantiene_pendiente(tmp_path):
    db_path, producto = _base(tmp_path)
    with conectar(db_path) as db:
        p = ejercicios.preparar_venta_faltante(
            {"archivo_id": "ARC-1234567890ab", "naturaleza": "cobro", "lineas": []}, db
        )
    assert p["estado"] == "pendiente"
    assert p["completo"] is False
    assert p["total"] == 0
    assert "fecha_comercial" in p["faltantes"]
    assert "lineas" in p["faltantes"]


def test_preparar_completa_usa_precio_del_catalogo(tmp_path):
    db_path, producto = _base(tmp_path)
    with conectar(db_path) as db:
        p = ejercicios.preparar_venta_faltante(_datos(producto), db)
        assert p["completo"] is True
        assert p["faltantes"] == []
        assert p["total"] == 2 * producto["precio_venta"]
        assert p["lineas"][0]["precio_unitario"] == producto["precio_venta"]


def test_precio_confirmado_explicito_manda(tmp_path):
    db_path, producto = _base(tmp_path)
    datos = _datos(producto)
    datos["lineas"][0]["precio_unitario"] = 1000
    datos["lineas"][0]["cantidad"] = 3
    with conectar(db_path) as db:
        p = ejercicios.preparar_venta_faltante(datos, db)
        assert p["total"] == 3000


def test_producto_inexistente_rechazado(tmp_path):
    db_path, _ = _base(tmp_path)
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "fecha_comercial": "2026-09-11",
        "lineas": [{"producto_codigo": "NO-EXISTE", "cantidad": 1}],
    }
    with pytest.raises(ValueError) as exc:
        with conectar(db_path) as db:
            ejercicios.preparar_venta_faltante(datos, db)
    assert "no existe en el catálogo" in str(exc.value)


def test_naturaleza_distinta_de_cobro_rechazada(tmp_path):
    db_path, producto = _base(tmp_path)
    datos = _datos(producto, naturaleza="gasto")
    with pytest.raises(ValueError) as exc:
        with conectar(db_path) as db:
            ejercicios.preparar_venta_faltante(datos, db)
    assert "operación de cobro" in str(exc.value)


def test_actualizar_borrador_incrementa_version(tmp_path):
    db_path, producto = _base(tmp_path)
    with conectar(db_path) as db:
        incompleta = ejercicios.preparar_venta_faltante(
            {"archivo_id": "ARC-1234567890ab", "naturaleza": "cobro", "lineas": []}, db
        )
        assert incompleta["version"] == 1
        completa = ejercicios.preparar_venta_faltante(
            _datos(producto, propuesta_id=incompleta["id"]), db
        )
        assert completa["id"] == incompleta["id"]
        assert completa["version"] == 2
        assert completa["completo"] is True


def test_ejecutar_sin_aprobacion_falla(tmp_path):
    db_path, producto = _base(tmp_path)
    with conectar(db_path) as db:
        p = ejercicios.preparar_venta_faltante(_datos(producto), db)
        with pytest.raises(ValueError) as exc:
            ejercicios.registrar_venta_aprobada(
                {"propuesta_id": p["id"], "version": p["version"], "clave_idempotente": p["clave_idempotente"]}, db
            )
        assert "no está aprobada" in str(exc.value)


def test_ejecutar_incompleta_no_crea_venta(tmp_path):
    db_path, _ = _base(tmp_path)
    with conectar(db_path) as db:
        p = ejercicios.preparar_venta_faltante(
            {"archivo_id": "ARC-1234567890ab", "naturaleza": "cobro", "lineas": []}, db
        )
        ejercicios.aprobar_propuesta(p["id"], db)
        with pytest.raises(ValueError) as exc:
            ejercicios.registrar_venta_aprobada(
                {"propuesta_id": p["id"], "version": p["version"], "clave_idempotente": p["clave_idempotente"]}, db
            )
        assert "incompleta" in str(exc.value)
        assert db.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 8


def test_flujo_completo_crea_venta_vinculo_sin_tocar_inventario(tmp_path):
    db_path, producto = _base(tmp_path)
    with conectar(db_path) as db:
        stock_antes = db.execute("SELECT SUM(stock) FROM inventario").fetchone()[0]
        ventas_antes = db.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]

        p = ejercicios.preparar_venta_faltante(_datos(producto), db)
        ejercicios.aprobar_propuesta(p["id"], db)
        r = ejercicios.registrar_venta_aprobada(
            {"propuesta_id": p["id"], "version": p["version"], "clave_idempotente": p["clave_idempotente"]}, db
        )

        assert r["estado"] == "ejecutada"
        assert r["venta_id"].startswith("V-")
        assert r["total"] == 2 * producto["precio_venta"]
        assert r["vinculo_id"] is not None
        assert db.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == ventas_antes + 1
        assert db.execute("SELECT SUM(stock) FROM inventario").fetchone()[0] == stock_antes

        venta = consultar_venta(db, r["venta_id"])
        assert venta is not None
        assert venta["total"] == r["total"]
        assert len(venta["lineas"]) == 1

        vinculo = db.execute(
            "SELECT * FROM vinculos_comerciales WHERE venta_id=?", (r["venta_id"],)
        ).fetchone()
        assert vinculo["operacion_id"] == r["operacion_id"]
        assert vinculo["importe_aplicado"] == r["total"]
        assert vinculo["aprobado_por_propuesta"] == p["id"]
        operacion = db.execute(
            "SELECT * FROM operaciones_reportadas WHERE id=?", (r["operacion_id"],)
        ).fetchone()
        assert operacion["naturaleza"] == "cobro"
        assert operacion["estado_financiero"] == "no_verificado"


def test_doble_confirmacion_no_duplica_venta(tmp_path):
    db_path, producto = _base(tmp_path)
    with conectar(db_path) as db:
        p = ejercicios.preparar_venta_faltante(_datos(producto), db)
        ejercicios.aprobar_propuesta(p["id"], db)
        args = {"propuesta_id": p["id"], "version": p["version"], "clave_idempotente": p["clave_idempotente"]}
        r1 = ejercicios.registrar_venta_aprobada(args, db)
        ventas_tras_primera = db.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
        r2 = ejercicios.registrar_venta_aprobada(args, db)
        assert r2["idempotente"] is True
        assert r2["venta_id"] == r1["venta_id"]
        assert db.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == ventas_tras_primera


def test_persistencia_al_reiniciar(tmp_path):
    db_path, producto = _base(tmp_path)
    with conectar(db_path) as db:
        p = ejercicios.preparar_venta_faltante(_datos(producto), db)
        ejercicios.aprobar_propuesta(p["id"], db)
        venta_id_previo = None

    # Segunda instancia: la propuesta aprobada sobrevive y puede ejecutarse.
    with conectar(db_path) as db:
        from src.db import consultar_propuesta
        p2 = consultar_propuesta(db, p["id"])
        assert p2["estado"] == "aprobada"
        r = ejercicios.registrar_venta_aprobada(
            {"propuesta_id": p2["id"], "version": p2["version"], "clave_idempotente": p2["clave_idempotente"]}, db
        )
        assert r["venta_id"] != venta_id_previo
        assert consultar_venta(db, r["venta_id"]) is not None


def test_rutas_get_propuesta_y_vinculo_no_devuelven_500(tmp_path):
    """Regresión del bug: las rutas GET consultaban funciones inexistentes en ejercicios."""
    from src.app import crear_app

    app = crear_app(tmp_path / "data")
    db_path = app.config["DB_PATH"]
    with conectar(db_path) as db:
        db.execute(
            "INSERT INTO archivos_ingresados(id,sha256,nombre_original,nombre_guardado,mime,bytes,cargado_en,estado) "
            "VALUES(?,?,?,?,?,?,?,'pendiente_reconocimiento')",
            ("ARC-1234567890ab", "sha256-falso", "soporte.png", "aabbccdd11223344.png", "image/png", 100, "2026-09-11T12:00:00+00:00"),
        )
        db.execute(
            "INSERT INTO comprobantes(id,archivo_id,modelo,version_prompt,extraccion_original,estado_extraccion,fecha_creacion,fecha_revision,revisado_por,notas_revision) "
            "VALUES(?,?,?,?,?,'revisada',?,?,?,?)",
            ("COMP-1234567890ab", "ARC-1234567890ab", "gpt-5.6-luna", "v1",
             json.dumps(EXTRACCION_OK), "2026-09-11T12:00:00+00:00", "2026-09-11T12:00:00+00:00", "operador", "Revisado"),
        )
        producto = dict(db.execute("SELECT codigo, precio_venta FROM productos ORDER BY codigo LIMIT 1").fetchone())
        db.commit()

        p = ejercicios.preparar_venta_faltante(_datos(producto), db)
        ejercicios.aprobar_propuesta(p["id"], db)
        r = ejercicios.registrar_venta_aprobada(
            {"propuesta_id": p["id"], "version": p["version"], "clave_idempotente": p["clave_idempotente"]}, db
        )

    client = app.test_client()
    respuesta_propuesta = client.get("/api/propuestas/" + p["id"])
    assert respuesta_propuesta.status_code == 200
    assert respuesta_propuesta.get_json()["tipo_operacion"] == "crear_venta"

    respuesta_vinculo = client.get("/api/vinculos/" + r["operacion_id"])
    assert respuesta_vinculo.status_code == 200
    assert respuesta_vinculo.get_json()["venta_id"] == r["venta_id"]
