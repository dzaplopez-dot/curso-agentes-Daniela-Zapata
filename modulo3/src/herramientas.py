"""Seis herramientas exactas de consulta (solo lectura).

Contratos:
- Todas leen SQLite con SQL, nunca escriben.
- Ninguna inventa datos: si no existe, devuelve None / lista vacía.
- Cada resultado incluye su fuente (tabla + fila_origen cuando aplica).

Herramientas:
1. obtener_producto(codigo)
2. buscar_productos(nombre, limite=10)
3. consultar_existencias(codigo)
4. productos_bajo_minimo(limite=100)
5. consultar_vencimientos(solo_vencidos=True, limite=100) + vencimiento_por_producto(codigo)
6. proponer_reposicion(codigo=None)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .db import conectar


def _norm_codigo(codigo: str) -> str:
    return (codigo or "").strip().upper()


def obtener_producto(codigo: str, db_path: Path | str | None = None) -> dict | None:
    """1. Ficha de producto por código exacto + proveedor."""
    codigo = _norm_codigo(codigo)
    if not codigo:
        return None
    with conectar(db_path) as con:
        fila = con.execute(
            """
            SELECT p.codigo, p.nombre, p.categoria, p.unidad,
                   p.precio_costo, p.precio_venta,
                   p.proveedor_id, pr.razon_social AS proveedor
            FROM productos p
            JOIN proveedores pr ON pr.id = p.proveedor_id
            WHERE p.codigo = ?
            """,
            (codigo,),
        ).fetchone()
        if fila is None:
            return None
        dato = dict(fila)
        dato["fuente"] = "productos + proveedores"
        return dato


def buscar_productos(nombre: str, limite: int = 10, db_path: Path | str | None = None) -> list[dict]:
    """2. Búsqueda por nombre (para ambigüedad: varios candidatos)."""
    nombre = (nombre or "").strip()
    if not nombre:
        return []
    with conectar(db_path) as con:
        filas = con.execute(
            """
            SELECT codigo, nombre, categoria, proveedor_id
            FROM productos
            WHERE nombre LIKE ? COLLATE NOCASE
            ORDER BY nombre
            LIMIT ?
            """,
            (f"%{nombre}%", limite),
        ).fetchall()
        return [{**dict(f), "fuente": "productos"} for f in filas]


def consultar_existencias(codigo: str, db_path: Path | str | None = None) -> dict | None:
    """3. Existencias por código: stock total, mínimo, detalle por lote/ubicación."""
    codigo = _norm_codigo(codigo)
    prod = obtener_producto(codigo, db_path)
    if prod is None:
        return None
    with conectar(db_path) as con:
        filas = con.execute(
            """
            SELECT producto_codigo, ubicacion, lote, stock, stock_minimo,
                   fecha_vencimiento, estado, fila_origen
            FROM inventario
            WHERE producto_codigo = ?
            ORDER BY fecha_vencimiento
            """,
            (codigo,),
        ).fetchall()
        detalle = [dict(f) for f in filas]
        total = sum(d["stock"] for d in detalle)
        minimo = max((d["stock_minimo"] for d in detalle), default=0)
        return {
            "codigo": codigo,
            "nombre": prod["nombre"],
            "proveedor": prod["proveedor"],
            "stock_total": total,
            "stock_minimo": minimo,
            "bajo_minimo": total < minimo if detalle else False,
            "movimientos": detalle,
            "fuente": "inventario (fila_origen por lote)",
        }


def productos_bajo_minimo(limite: int = 100, db_path: Path | str | None = None) -> list[dict]:
    """4. Productos cuyo stock está bajo el mínimo (agregado por producto)."""
    with conectar(db_path) as con:
        filas = con.execute(
            """
            SELECT producto_codigo, SUM(stock) AS stock_total,
                   MAX(stock_minimo) AS stock_minimo,
                   COUNT(*) AS lotes
            FROM inventario
            GROUP BY producto_codigo
            HAVING stock_total < stock_minimo
            ORDER BY stock_total
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
        return [
            {
                **dict(f),
                "faltante": f["stock_minimo"] - f["stock_total"],
                "fuente": "inventario",
            }
            for f in filas
        ]


def consultar_vencimientos(
    solo_vencidos: bool = True, limite: int = 100, db_path: Path | str | None = None
) -> list[dict]:
    """5. Lotes vencidos (fecha < hoy). Separa el lote del disponible."""
    hoy = date.today().isoformat()
    operador = "<" if solo_vencidos else ">="
    with conectar(db_path) as con:
        filas = con.execute(
            f"""
            SELECT producto_codigo, lote, stock, fecha_vencimiento, estado,
                   ubicacion, fila_origen
            FROM inventario
            WHERE fecha_vencimiento IS NOT NULL
              AND fecha_vencimiento {operador} ?
            ORDER BY fecha_vencimiento
            LIMIT ?
            """,
            (hoy, limite),
        ).fetchall()
        return [{**dict(f), "fuente": "inventario"} for f in filas]


def vencimiento_por_producto(codigo: str, db_path: Path | str | None = None) -> dict | None:
    """5b. Para un código: separa disponible vs vencido (caso lote vencido)."""
    ex = consultar_existencias(codigo, db_path)
    if ex is None:
        return None
    hoy = date.today().isoformat()
    disponible, vencido = [], []
    for m in ex["movimientos"]:
        fv = m.get("fecha_vencimiento")
        if fv is not None and fv < hoy:
            vencido.append(m)
        else:
            disponible.append(m)
    return {
        "codigo": ex["codigo"],
        "nombre": ex["nombre"],
        "stock_disponible": sum(m["stock"] for m in disponible),
        "stock_vencido": sum(m["stock"] for m in vencido),
        "lotes_disponibles": disponible,
        "lotes_vencidos": vencido,
        "fuente": "inventario (fecha_vencimiento vs hoy)",
    }


def proponer_reposicion(
    codigo: str | None = None, db_path: Path | str | None = None
) -> dict | list[dict]:
    """6. Propuesta reproducible: cantidad = max(0, minimo - stock).

    - Con código: una propuesta.
    - Sin código: lista de todos los bajo mínimo.
    - Nunca escribe, solo propone.
    """
    if codigo:
        ex = consultar_existencias(codigo, db_path)
        if ex is None:
            return {"codigo": _norm_codigo(codigo), "existe": False}
        cantidad = max(0, ex["stock_minimo"] - ex["stock_total"])
        return {
            "codigo": ex["codigo"],
            "nombre": ex["nombre"],
            "stock_total": ex["stock_total"],
            "stock_minimo": ex["stock_minimo"],
            "cantidad_sugerida": cantidad,
            "regla": "cantidad = max(0, stock_minimo - stock_total)",
            "necesita_reposicion": cantidad > 0,
            "fuente": "inventario",
        }
    propuestas = []
    for item in productos_bajo_minimo(db_path=db_path):
        propuestas.append(
            {
                "codigo": item["producto_codigo"],
                "stock_total": item["stock_total"],
                "stock_minimo": item["stock_minimo"],
                "cantidad_sugerida": item["faltante"],
                "regla": "cantidad = max(0, stock_minimo - stock_total)",
                "fuente": "inventario",
            }
        )
    return propuestas
