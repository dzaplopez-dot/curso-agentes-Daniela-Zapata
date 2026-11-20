"""Copia el catálogo y los pedidos de la base local SQLite al backend configurado.

Uso:
    $env:EFY_BACKEND = "postgres"
    $env:DATABASE_URL = "postgresql://usuario:clave@host:5432/postgres"
    python scripts/migrar.py
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from efy import config, db


def leer_sqlite():
    if not config.DB_PATH.exists():
        raise SystemExit(f"No existe la base local {config.DB_PATH}. Ejecuta demo.py primero.")
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    perfumes = [dict(r) for r in con.execute("SELECT * FROM perfumes")]
    pedidos = [dict(r) for r in con.execute("SELECT * FROM pedidos")]
    con.close()
    return perfumes, pedidos


def main():
    if config.BACKEND != "postgres":
        raise SystemExit("Define EFY_BACKEND=postgres y DATABASE_URL antes de migrar.")

    perfumes, pedidos = leer_sqlite()
    print(f"Origen: {len(perfumes)} perfumes · {len(pedidos)} pedidos")

    db.inicializar()
    with db.conectar() as con:
        for p in perfumes:
            con.execute(
                """
                INSERT INTO perfumes
                    (codigo, inspirado_en, casa, genero, familia_raw, familia_base,
                     ml, precio, stock, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (codigo) DO UPDATE SET
                    stock = excluded.stock,
                    precio = excluded.precio,
                    activo = excluded.activo
                """,
                (
                    p["codigo"], p["inspirado_en"], p["casa"], p["genero"],
                    p["familia_raw"], p["familia_base"], p["ml"], p["precio"],
                    p["stock"], p["activo"],
                ),
            )
        for pedido in pedidos:
            existente = con.execute(
                "SELECT id FROM pedidos WHERE chat_id = ? AND msg_id = ?",
                (pedido["chat_id"], pedido["msg_id"]),
            ).fetchone()
            if existente:
                continue
            con.execute(
                """
                INSERT INTO pedidos (chat_id, codigo, cantidad, estado, msg_id, creado_en)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    pedido["chat_id"], pedido["codigo"], pedido["cantidad"],
                    pedido["estado"], pedido["msg_id"], pedido["creado_en"],
                ),
            )
    print("Migración terminada. Verifica el conteo en el panel o en el Table editor.")


if __name__ == "__main__":
    main()
