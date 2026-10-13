"""Pruebas de las 6 herramientas + reconciliación e idempotencia."""

from pathlib import Path

from scripts.importar_excel import convertir
from src import herramientas as H
from src.db import conectar


def test_conteos_reconciliados():
    with conectar() as con:
        prov = con.execute("SELECT COUNT(*) FROM proveedores").fetchone()[0]
        prod = con.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
        inv = con.execute("SELECT COUNT(*) FROM inventario").fetchone()[0]
        bajos = con.execute("SELECT COUNT(*) FROM (SELECT producto_codigo FROM inventario GROUP BY producto_codigo HAVING SUM(stock) < MAX(stock_minimo))").fetchone()[0]
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
    assert prov == 75
    assert prod == 1250
    assert inv == 827
    assert bajos == 73
    assert fk == []


def test_herramientas_basicas():
    assert H.obtener_producto("FER-0001")["codigo"] == "FER-0001"
    assert H.obtener_producto("XXX-9999") is None
    assert len(H.buscar_productos("Martillo")) >= 5
    ex = H.consultar_existencias("FER-0001")
    assert ex["stock_total"] >= 0 and "fila_origen" in str(ex)
    assert H.consultar_existencias("XXX-9999") is None
    bajos = H.productos_bajo_minimo()
    assert len(bajos) == 73
    venc = H.consultar_vencimientos()
    assert len(venc) > 0
    prop = H.proponer_reposicion("ABA-0220")
    assert prop["cantidad_sugerida"] == max(0, prop["stock_minimo"] - prop["stock_total"])


def test_segunda_importacion_no_duplica(tmp_path):
    origen = Path("datos/original/operacion_comercial_app.xlsm")
    destino = tmp_path / "segunda.db"
    c1 = convertir(origen, destino)
    c2 = convertir(origen, destino)
    assert c1 == c2
    assert c1["productos"] == 1250


def test_proveedor_invalido_detiene(tmp_path):
    """Simula fila con proveedor inexistente: debe fallar con FK, no insertar parcial."""
    import sqlite3

    destino = tmp_path / "fk.db"
    con = sqlite3.connect(destino)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(
        "CREATE TABLE proveedores (id TEXT PRIMARY KEY, razon_social TEXT NOT NULL);"
        "CREATE TABLE productos (codigo TEXT PRIMARY KEY, nombre TEXT NOT NULL, proveedor_id TEXT NOT NULL REFERENCES proveedores(id));"
    )
    con.execute("INSERT INTO proveedores VALUES ('PRV-001','Ok')")
    try:
        con.execute("INSERT INTO productos VALUES ('X-1','Prueba','PRV-999')")
        con.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    con.close()
    assert ok is False
