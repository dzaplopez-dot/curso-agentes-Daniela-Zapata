"""Pruebas del ejercicio 2: asociar comprobante con venta existente.
No llama a OpenAI real. Usa la base de prueba temporal de SQLite."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src import ejercicios
from src.db import conectar, construir, migrar

EXTRACCION_OK = {
    "document_type": "card_voucher",
    "payment_brand_or_medium": "Visa crédito",
    "payment_medium_alternatives": [],
    "currency_observed": "COP",
    "operation_status_observed": "Aprobado",
    "amount_basis": "observed_total",
    "total_amount": 148000,
    "inferred_amount": None,
    "stated_cash_amount": None,
    "document_date": "2026-09-11",
    "document_time": "12:14:00",
    "time_precision": "minute",
    "merchant_or_store": None,
    "notes": None,
    "references": {
        "receipt": None, "authorization": None, "rrn": None, "transaction_id": None,
        "invoice": None, "promissory_note": None, "application_id": None,
        "credit_id": None, "order_id": None, "transfer_reference": None,
        "handwritten": None,
    },
    "confidence": {"document_type": 0.9, "payment_brand_or_medium": 0.85},
    "observed_text": {},
    "warnings": [],
    "missing_fields": [],
}


def _crear_base_con_comprobante(tmp_path, archivo_id="ARC-1234567890ab", comprobante_id="COMP-1234567890ab"):
    """Crea una base con migraciones, archivo y comprobante revisado."""
    from src.db import ROOT
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
        db.commit()
    return db_path


def test_preparar_operacion_importe_invalido(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "importe_aplicado": -5000,
        "venta_id": "V-001",
        "motivo": "Prueba",
    }
    with pytest.raises(ValueError) as exc:
        with conectar(db_path) as db:
            ejercicios.preparar_operacion(datos, db)
    assert "mayor a cero" in str(exc.value)

    datos2 = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "importe_aplicado": "no-es-numero",
        "venta_id": "V-001",
        "motivo": "Prueba",
    }
    with pytest.raises(ValueError) as exc:
        with conectar(db_path) as db:
            ejercicios.preparar_operacion(datos2, db)
    assert "inválido" in str(exc.value)


def test_preparar_operacion_naturaleza_invalida(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "invalida",
        "importe_aplicado": 100000,
        "venta_id": "V-001",
        "motivo": "Prueba",
    }
    with pytest.raises(ValueError) as exc:
        with conectar(db_path) as db:
            ejercicios.preparar_operacion(datos, db)
    assert "Naturaleza inválida" in str(exc.value)


def test_preparar_operacion_sin_comprobante_revisado(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    # El archivo existe pero no tiene comprobante asociado (usar archivo_id distinto).
    datos = {
        "archivo_id": "ARC-INEEXISTENTE",
        "naturaleza": "cobro",
        "importe_aplicado": 100000,
        "venta_id": "V-001",
        "motivo": "Prueba",
    }
    with pytest.raises(ValueError) as exc:
        with conectar(db_path) as db:
            ejercicios.preparar_operacion(datos, db)
    assert "comprobante revisado" in str(exc.value)


def test_preparar_operacion_exito(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "importe_aplicado": 130700,
        "venta_id": "V-001",
        "motivo": "Asociación de cobro",
    }
    with conectar(db_path) as db:
        p = ejercicios.preparar_operacion(datos, db)
        assert p["estado"] == "pendiente"
        assert p["version"] == 1
        assert p["naturaleza"] == "cobro"
        assert p["importe_aplicado"] == 130700
        assert p["venta_id"] == "V-001"
        assert p["estado_financiero"] == "no_verificado"
        assert p["clave_idempotente"] is not None
        assert p["id"].startswith("PROP-")


def test_aprobar_propuesta_sin_preparar(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    with pytest.raises(ValueError) as exc:
        with conectar(db_path) as db:
            ejercicios.aprobar_propuesta("PROP-INEXISTENTE", db)
    assert "no existe" in str(exc.value)


def test_ejecutar_sin_aprobacion(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    # Preparar pero no aprobar
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "importe_aplicado": 130700,
        "venta_id": "V-001",
        "motivo": "Asociación de cobro",
    }
    with conectar(db_path) as db:
        p = ejercicios.preparar_operacion(datos, db)
        # Intentar ejecutar sin aprobar
        with pytest.raises(ValueError) as exc:
            ejercicios.registrar_operacion_aprobada({
                "propuesta_id": p["id"],
                "version": p["version"],
                "clave_idempotente": p["clave_idempotente"],
            }, db)
        assert "no está aprobada" in str(exc.value)


def test_ejecutar_version_no_coincide(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "importe_aplicado": 130700,
        "venta_id": "V-001",
        "motivo": "Asociación de cobro",
    }
    with conectar(db_path) as db:
        p = ejercicios.preparar_operacion(datos, db)
        ejercicios.aprobar_propuesta(p["id"], db)
        # Versión distinta a la aprobada
        with pytest.raises(ValueError) as exc:
            ejercicios.registrar_operacion_aprobada({
                "propuesta_id": p["id"],
                "version": 999,
                "clave_idempotente": p["clave_idempotente"],
            }, db)
        assert "no coincide" in str(exc.value)


def test_doble_ejecucion_idempotencia(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "importe_aplicado": 130700,
        "venta_id": "V-001",
        "motivo": "Asociación de cobro",
    }
    with conectar(db_path) as db:
        p = ejercicios.preparar_operacion(datos, db)
        ejercicios.aprobar_propuesta(p["id"], db)
        # Primera ejecución
        r1 = ejercicios.registrar_operacion_aprobada({
            "propuesta_id": p["id"],
            "version": p["version"],
            "clave_idempotente": p["clave_idempotente"],
        }, db)
        assert r1["estado"] == "ejecutada"
        # Segunda ejecución con misma clave idempotente -> debe fallar
        with pytest.raises(ValueError) as exc:
            ejercicios.registrar_operacion_aprobada({
                "propuesta_id": p["id"],
                "version": p["version"],
                "clave_idempotente": p["clave_idempotente"],
            }, db)
        assert "ya fue ejecutada" in str(exc.value)


def test_consultar_vinculo(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "cobro",
        "importe_aplicado": 130700,
        "venta_id": "V-001",
        "motivo": "Asociación de cobro",
    }
    with conectar(db_path) as db:
        p = ejercicios.preparar_operacion(datos, db)
        ejercicios.aprobar_propuesta(p["id"], db)
        r = ejercicios.registrar_operacion_aprobada({
            "propuesta_id": p["id"],
            "version": p["version"],
            "clave_idempotente": p["clave_idempotente"],
        }, db)
        from src.db import consultar_vinculo
        v = consultar_vinculo(db, r["operacion_id"])
        assert v is not None
        assert v["venta_id"] == "V-001"
        assert v["importe_aplicado"] == 130700
        assert v["estado_financiero"] == "no_verificado"


def test_persistencia_al_reiniciar(tmp_path):
    db_path = _crear_base_con_comprobante(tmp_path)
    datos = {
        "archivo_id": "ARC-1234567890ab",
        "naturaleza": "financiación",
        "importe_aplicado": 148000,
        "venta_id": None,
        "motivo": "Financiación sin venta asociada",
    }
    # Primera instancia: preparar y aprobar
    with conectar(db_path) as db:
        p = ejercicios.preparar_operacion(datos, db)
        ejercicios.aprobar_propuesta(p["id"], db)

    # Segunda instancia (simula reinicio): la propuesta debe seguir aprobada
    from src.db import consultar_propuesta
    with conectar(db_path) as db:
        p2 = consultar_propuesta(db, p["id"])
        assert p2 is not None
        assert p2["estado"] == "aprobada"
        # Ejecutar en la segunda instancia
        r = ejercicios.registrar_operacion_aprobada({
            "propuesta_id": p["id"],
            "version": p2["version"],
            "clave_idempotente": p2["clave_idempotente"],
        }, db)
        assert r["estado"] == "ejecutada"
