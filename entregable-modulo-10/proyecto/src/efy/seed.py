import csv

from . import config, db


def cargar(con=None, ruta=None):
    ruta = ruta or config.CATALOGO
    cerrar = False
    if con is None:
        con = db.conectar()
        cerrar = True
    total = 0
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as fh:
            for fila in csv.DictReader(fh):
                if not fila.get("codigo"):
                    continue
                con.execute(
                    """
                    INSERT INTO perfumes
                        (codigo, inspirado_en, casa, genero, familia_raw, familia_base,
                         ml, precio, stock, activo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (codigo) DO UPDATE SET
                        inspirado_en = excluded.inspirado_en,
                        casa = excluded.casa,
                        genero = excluded.genero,
                        familia_raw = excluded.familia_raw,
                        familia_base = excluded.familia_base,
                        ml = excluded.ml,
                        precio = excluded.precio,
                        activo = excluded.activo
                    """,
                    (
                        str(fila["codigo"]).strip(),
                        fila["inspirado_en"].strip().upper(),
                        fila["casa"].strip().upper(),
                        fila["genero"].strip().upper(),
                        (fila.get("familia_raw") or "").strip().upper(),
                        fila["familia_base"].strip().upper(),
                        int(fila.get("ml") or config.ML_DEFECTO),
                        float(fila.get("precio") or config.PRECIO_DEFECTO),
                        int(fila.get("stock") or config.STOCK_INICIAL),
                        1 if str(fila.get("activo", "true")).lower() in ("1", "true", "si") else 0,
                    ),
                )
                total += 1
        con.commit()
    finally:
        if cerrar:
            con.close()
    return total
