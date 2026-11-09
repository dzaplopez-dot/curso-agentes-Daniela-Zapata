"""Pruebas del ejercicio 1 con respuestas simuladas (mocks). No llama a OpenAI real."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src import ejercicios
from src.ocr_client import OCRClientError

ROOT = Path(__file__).resolve().parents[1]

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
    "confidence": {
        "document_type": 0.9, "payment_brand_or_medium": 0.85,
        "payment_medium_alternatives": None, "currency_observed": 0.9,
        "operation_status_observed": 0.8, "amount_basis": 0.95, "total_amount": 0.9,
        "inferred_amount": None, "stated_cash_amount": None, "document_date": 0.9,
        "document_time": 0.85, "time_precision": 0.9, "merchant_or_store": None,
        "notes": None, "references": {
            "receipt": None, "authorization": None, "rrn": None, "transaction_id": None,
            "invoice": None, "promissory_note": None, "application_id": None,
            "credit_id": None, "order_id": None, "transfer_reference": None,
            "handwritten": None,
        },
    },
    "observed_text": {
        "document_type": "Voucher", "payment_brand_or_medium": "Visa crédito",
        "payment_medium_alternatives": None, "currency_observed": "COP",
        "operation_status_observed": "Aprobado", "amount_basis": "observed_total",
        "total_amount": "148000", "inferred_amount": None, "stated_cash_amount": None,
        "document_date": "2026-09-11", "document_time": "12:14:00", "time_precision": "minute",
        "merchant_or_store": None, "notes": None, "references": {
            "receipt": None, "authorization": None, "rrn": None, "transaction_id": None,
            "invoice": None, "promissory_note": None, "application_id": None,
            "credit_id": None, "order_id": None, "transfer_reference": None,
            "handwritten": None,
        },
    },
    "warnings": [],
    "missing_fields": [],
}


def _archivo_registro(tmp_path, id_archivo="ARC-1234567890ab"):
    upload_dir = tmp_path / "archivos"
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "aabbccdd11223344.png").write_bytes(b"imagen-falsa")
    return {
        "id": id_archivo,
        "nombre_guardado": "aabbccdd11223344.png",
        "nombre_original": "soporte.png",
    }, upload_dir


def test_extraer_soporte_exito_con_mock(tmp_path, monkeypatch):
    archivo, upload_dir = _archivo_registro(tmp_path)

    def mock_extraer(path_imagen, prompt, schema, max_reintentos=2):
        assert prompt is not None and len(prompt) > 0
        return dict(EXTRACCION_OK)

    monkeypatch.setattr(ejercicios, "extraer_con_openai", mock_extraer)

    resultado = ejercicios.extraer_soporte(archivo, None, upload_dir)
    assert resultado["modelo"] == "gpt-5.6-luna"
    assert resultado["version_prompt"] == "v1"
    assert resultado["extraccion_original"]["document_type"] == "card_voucher"
    assert resultado["extraccion_original"]["total_amount"] == 148000


def test_extraer_soporte_clave_ausente(tmp_path, monkeypatch):
    archivo, upload_dir = _archivo_registro(tmp_path)

    def mock_extraer_clave_vacia(path_imagen, prompt, schema, max_reintentos=2):
        raise OCRClientError("Falta OPENAI_API_KEY en la configuración privada del backend.", codigo_http=401, reintentable=False)

    monkeypatch.setattr(ejercicios, "extraer_con_openai", mock_extraer_clave_vacia)

    with pytest.raises(OCRClientError) as exc:
        ejercicios.extraer_soporte(archivo, None, upload_dir)
    assert exc.value.codigo_http == 401


def test_extraer_soporte_respuesta_incompleta(tmp_path, monkeypatch):
    archivo, upload_dir = _archivo_registro(tmp_path)

    def mock_extraer_incompleto(path_imagen, prompt, schema, max_reintentos=2):
        return {"document_type": "card_voucher"}

    monkeypatch.setattr(ejercicios, "extraer_con_openai", mock_extraer_incompleto)

    with pytest.raises(OCRClientError) as exc:
        ejercicios.extraer_soporte(archivo, None, upload_dir)
    assert exc.value.codigo_http == 502
    assert "faltan campos" in str(exc.value)


def _crear_base_con_archivo(tmp_path, archivo_id="ARC-1234567890ab"):
    from src.db import conectar, construir, migrar
    db_path = tmp_path / "negocio.sqlite3"
    construir(db_path)
    migrar(db_path)
    with conectar(db_path) as db:
        db.execute(
            "INSERT INTO archivos_ingresados(id,sha256,nombre_original,nombre_guardado,mime,bytes,cargado_en,estado) "
            "VALUES(?,?,?,?,?,?,?,'pendiente_reconocimiento')",
            (archivo_id, "sha256-falso", "soporte.png", "aabbccdd11223344.png", "image/png", 100, "2026-09-11T12:00:00+00:00"),
        )
        db.commit()
    return db_path


def test_registrar_comprobante_con_revision_humana(tmp_path):
    db_path = _crear_base_con_archivo(tmp_path)

    datos = {
        "archivo_id": "ARC-1234567890ab",
        "revisado_humano": True,
        "revisado_por": "operador",
        "modelo": "gpt-5.6-luna",
        "version_prompt": "v1",
        "extraccion_original": EXTRACCION_OK,
        "notas_revision": "Revisado y validado por el operador.",
        "correcciones": [],
    }

    from src.db import conectar, consultar_comprobante
    with conectar(db_path) as db:
        resultado = ejercicios.registrar_comprobante(datos, db, None)
        assert resultado["estado"] == "revisada"
        assert resultado["archivo_id"] == "ARC-1234567890ab"
        assert resultado["modelo"] == "gpt-5.6-luna"

        comprobante = consultar_comprobante(db, resultado["id"])
        assert comprobante is not None
        assert comprobante["estado_extraccion"] == "revisada"
        assert comprobante["archivo"]["id"] == "ARC-1234567890ab"
        extraccion = json.loads(comprobante["extraccion_original"])
        assert extraccion["document_type"] == "card_voucher"
        assert comprobante["correcciones"] == []
        assert len(comprobante["eventos"]) == 1


def test_registrar_comprobante_sin_revision_humana(tmp_path):
    db_path = _crear_base_con_archivo(tmp_path)

    datos = {
        "archivo_id": "ARC-1234567890ab",
        "revisado_humano": False,
        "modelo": "gpt-5.6-luna",
        "version_prompt": "v1",
        "extraccion_original": EXTRACCION_OK,
        "correcciones": [],
    }

    from src.db import conectar
    with pytest.raises(ValueError) as exc:
        with conectar(db_path) as db:
            ejercicios.registrar_comprobante(datos, db, None)
    assert "revisión humana explícita" in str(exc.value)
