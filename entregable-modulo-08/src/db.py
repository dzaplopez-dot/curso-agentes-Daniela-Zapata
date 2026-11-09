"""SQLite local. Semilla independiente del proyecto anterior; importes en COP enteros."""
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@contextmanager
def conectar(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def construir(destino):
    """Solo crea bases nuevas. Para volver al inicio se conserva una copia completa."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        raise FileExistsError('La base ya existe. Usa scripts.reiniciar para conservar un respaldo.')
    fd, temporal = tempfile.mkstemp(dir=destino.parent, suffix='.sqlite3.tmp')
    os.close(fd)
    try:
        with conectar(temporal) as db:
            db.executescript((ROOT / 'datos/esquema.sql').read_text())
            catalogo = json.loads((ROOT / 'datos/semilla/catalogo.json').read_text())
            for tabla in ('proveedores','productos','inventario'):
                filas = catalogo[tabla]
                columnas = list(filas[0])
                sql = f'INSERT INTO {tabla} ({",".join(columnas)}) VALUES ({",".join("?" for _ in columnas)})'
                db.executemany(sql, [tuple(f[c] for c in columnas) for f in filas])
            ventas = json.loads((ROOT / 'datos/semilla/ventas.json').read_text())
            for v in ventas:
                db.execute('INSERT INTO ventas(id,fecha_comercial,cliente,factura_externa) VALUES(?,?,?,?)',
                           (v['id'],v['fecha_comercial'],v['cliente'],v['factura_externa']))
                db.executemany('INSERT INTO venta_lineas(venta_id,producto_codigo,cantidad,precio_unitario) VALUES(?,?,?,?)',
                    [(v['id'], l['producto_codigo'],l['cantidad'],l['precio_unitario']) for l in v['lineas']])
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
        # El enlace falla si otra instancia ganó la creación: nunca sobreescribe.
        os.link(temporal, destino)
    finally:
        Path(temporal).unlink(missing_ok=True)


def buscar_ventas(db, texto='', importe=None, fecha=None):
    filtros, valores = [], []
    if texto:
        filtros.append('(id LIKE ? OR COALESCE(cliente,\'\') LIKE ? OR COALESCE(factura_externa,\'\') LIKE ?)')
        valores += [f'%{texto}%']*3
    if importe is not None:
        filtros.append('total = ?')
        valores.append(importe)
    if fecha:
        filtros.append('fecha_comercial = ?')
        valores.append(fecha)
    where = ' WHERE ' + ' AND '.join(filtros) if filtros else ''
    return [dict(r) for r in db.execute('SELECT * FROM resumen_ventas'+where+' ORDER BY fecha_comercial DESC,id LIMIT 100', valores)]


def consultar_venta(db, venta_id):
    fila = db.execute('SELECT * FROM resumen_ventas WHERE id=?',(venta_id,)).fetchone()
    if not fila:
        return None
    venta = dict(fila)
    venta['lineas'] = [dict(r) for r in db.execute('''
        SELECT l.producto_codigo,p.nombre,l.cantidad,l.precio_unitario,
               l.cantidad*l.precio_unitario AS subtotal
        FROM venta_lineas l JOIN productos p ON p.codigo=l.producto_codigo
        WHERE l.venta_id=? ORDER BY l.id''',(venta_id,))]
    return venta


def consultar_comprobante(db, comprobante_id):
    fila = db.execute('SELECT * FROM comprobantes WHERE id=?',(comprobante_id,)).fetchone()
    if not fila:
        return None
    comprobante = dict(fila)
    comprobante['correcciones'] = [dict(r) for r in db.execute(
        'SELECT * FROM correcciones WHERE comprobante_id=? ORDER BY id',(comprobante_id,))]
    comprobante['eventos'] = [dict(r) for r in db.execute(
        'SELECT * FROM eventos WHERE tabla_origen=? AND registro_id=? ORDER BY id',('comprobantes',comprobante_id))]
    archivo = db.execute('SELECT * FROM archivos_ingresados WHERE id=?',(comprobante['archivo_id'],)).fetchone()
    comprobante['archivo'] = dict(archivo) if archivo else None
    return comprobante


def consultar_propuesta(db, propuesta_id):
    fila = db.execute('SELECT * FROM propuestas WHERE id=?',(propuesta_id,)).fetchone()
    if not fila:
        return None
    p = dict(fila)
    p['datos_exactos'] = json.loads(p['datos_exactos']) if p['datos_exactos'] else {}
    p['resultado'] = json.loads(p['resultado']) if p['resultado'] else None
    return p


def consultar_vinculo(db, operacion_id):
    fila = db.execute(
        '''
        SELECT v.*, o.naturaleza, o.monto, o.moneda, o.estado_financiero,
               s.id AS venta_id, s.fecha_comercial, s.cliente
        FROM vinculos_comerciales v
        JOIN operaciones_reportadas o ON o.id = v.operacion_id
        LEFT JOIN ventas s ON s.id = v.venta_id
        WHERE v.operacion_id=?
        ''', (operacion_id,)
    ).fetchone()
    if not fila:
        return None
    return dict(fila)


MIGRACIONES = [
    """
    CREATE TABLE IF NOT EXISTS comprobantes (
        id TEXT PRIMARY KEY,
        archivo_id TEXT NOT NULL REFERENCES archivos_ingresados(id),
        modelo TEXT NOT NULL,
        version_prompt TEXT NOT NULL,
        extraccion_original TEXT NOT NULL,
        estado_extraccion TEXT NOT NULL DEFAULT 'pendiente_revision' CHECK(estado_extraccion IN ('pendiente_revision','revisada','rechazada')),
        fecha_creacion TEXT NOT NULL,
        fecha_revision TEXT,
        revisado_por TEXT,
        notas_revision TEXT
    );
    CREATE TABLE IF NOT EXISTS correcciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comprobante_id TEXT NOT NULL REFERENCES comprobantes(id),
        campo TEXT NOT NULL,
        valor_original TEXT,
        valor_corregido TEXT,
        origen_correccion TEXT NOT NULL DEFAULT 'revisor_humano',
        fecha_correccion TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS operaciones_reportadas (
        id TEXT PRIMARY KEY,
        comprobante_id TEXT REFERENCES comprobantes(id),
        naturaleza TEXT NOT NULL CHECK(naturaleza IN ('cobro','financiación','gasto')),
        monto INTEGER NOT NULL CHECK(monto >= 0),
        moneda TEXT NOT NULL DEFAULT 'COP',
        referencias TEXT,
        estado_financiero TEXT NOT NULL DEFAULT 'no_verificado' CHECK(estado_financiero IN ('no_verificado','verificado','rechazado')),
        fecha_creacion TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS soportes_operacion (
        operacion_id TEXT NOT NULL REFERENCES operaciones_reportadas(id),
        archivo_id TEXT NOT NULL REFERENCES archivos_ingresados(id),
        PRIMARY KEY(operacion_id, archivo_id)
    );
    CREATE TABLE IF NOT EXISTS vinculos_comerciales (
        id TEXT PRIMARY KEY,
        operacion_id TEXT NOT NULL REFERENCES operaciones_reportadas(id),
        venta_id TEXT NOT NULL REFERENCES ventas(id),
        importe_aplicado INTEGER NOT NULL CHECK(importe_aplicado > 0),
        aprobado_por_propuesta TEXT REFERENCES propuestas(id),
        fecha_creacion TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS propuestas (
        id TEXT PRIMARY KEY,
        version INTEGER NOT NULL DEFAULT 1,
        tipo_operacion TEXT NOT NULL,
        datos_exactos TEXT NOT NULL,
        evidencia TEXT,
        estado TEXT NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente','aprobada','rechazada','ejecutada')),
        aprobado_por TEXT,
        fecha_aprobacion TEXT,
        fecha_creacion TEXT NOT NULL,
        resultado TEXT,
        clave_idempotente TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tabla_origen TEXT NOT NULL,
        registro_id TEXT NOT NULL,
        tipo_evento TEXT NOT NULL,
        detalle TEXT,
        fecha_evento TEXT NOT NULL
    );
    PRAGMA user_version = 2;
    """,
]


def migrar(path):
    """Aplica migraciones versionadas si la base está por detrás de user_version."""
    path = Path(path)
    with conectar(path) as db:
        fila = db.execute('PRAGMA user_version').fetchone()
        version = fila[0] if fila else 0
        if version < 2:
            db.executescript(MIGRACIONES[0])
