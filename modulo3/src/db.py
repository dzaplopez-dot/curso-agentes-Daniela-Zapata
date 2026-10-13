"""Conexión de solo lectura a la base SQLite reconstruible."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# src/db.py -> padres: src/ -> modulo3/ (raíz del entregable)
RAIZ = Path(__file__).resolve().parents[1]
DB_POR_DEFECTO = RAIZ / "datos" / "procesados" / "inventario.db"


def conectar(db_path: Path | str | None = None) -> sqlite3.Connection:
    ruta = Path(db_path) if db_path else DB_POR_DEFECTO
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró la base: {ruta}. "
            "Reconstrúyela con: "
            "uv run python scripts/importar_excel.py "
            "datos/original/operacion_comercial_app.xlsm datos/procesados/inventario.db"
        )
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def ruta_db() -> Path:
    return DB_POR_DEFECTO
