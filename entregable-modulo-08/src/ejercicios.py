"""Puntos de extensión del taller. Implementados siguiendo docs/CONTRATOS.md y AGENTS.md.

Las rutas devuelven 501 mientras estas funciones estén pendientes. El ejercicio 1
implementa extraer_soporte y registrar_comprobante. El ejercicio 2 implementa
preparar_operacion, aprobar_propuesta y registrar_operacion_aprobada.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import db as db_mod
from .ocr_client import OCRClientError, extraer_con_openai

OCR_MODEL = 'gpt-5.6-luna'

PROMPT_PATH = Path(__file__).resolve().parents[1] / 'prompts' / 'extractor-v1.txt'
SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'prompts' / 'extraccion-v1.schema.json'

CAMPOS_REQUERIDOS = [
    'document_type', 'payment_brand_or_medium', 'payment_medium_alternatives',
    'currency_observed', 'operation_status_observed', 'amount_basis',
    'total_amount', 'inferred_amount', 'stated_cash_amount', 'document_date',
    'document_time', 'time_precision', 'merchant_or_store', 'notes',
    'references', 'confidence', 'observed_text', 'warnings', 'missing_fields',
]


def _ahora():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _leer_prompt():
    return PROMPT_PATH.read_text(encoding='utf-8')


def _leer_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


def _ruta_archivo(archivo: dict, upload_dir: Path) -> Path:
    nombre = archivo.get('nombre_guardado') or archivo.get('nombre_original')
    if not nombre:
        raise ValueError('El registro del archivo no tiene nombre guardado.')
    return upload_dir / nombre


def extraer_soporte(archivo: dict, db, upload_dir: Path | None = None):
    """Ejercicio 1: conecta con OpenAI Responses API, valida el esquema y devuelve la extracción.

    Nunca permite rutas arbitrarias provenientes del modelo; resuelve la ruta desde el
    almacén local validado. No simula OCR ni llama a la API si falta la clave.
    """
    if upload_dir is None:
        raise ValueError('Se requiere el directorio de subidas para localizar el archivo.')

    ruta = _ruta_archivo(archivo, upload_dir)
    prompt = _leer_prompt()
    schema = _leer_schema()

    try:
        extraccion = extraer_con_openai(ruta, prompt, schema)
    except OCRClientError:
        raise
    except Exception as exc:  # pragma: no cover - fallback de seguridad
        raise OCRClientError(f'Error inesperado en el reconocimiento: {exc}', codigo_http=500, reintentable=False) from exc

    # Validar que la respuesta contenga los campos exigidos por el esquema v1.
    faltantes = [k for k in CAMPOS_REQUERIDOS if k not in extraccion]
    if faltantes:
        raise OCRClientError(
            f'Respuesta incompleta: faltan campos {faltantes}',
            codigo_http=502,
            reintentable=False,
        )

    return {
        'extraccion_original': extraccion,
        'modelo': OCR_MODEL,
        'version_prompt': 'v1',
        'fecha_extraccion': _ahora(),
    }


def registrar_comprobante(datos: dict, db, upload_dir: Path | None = None):
    """Ejercicio 1: guarda el comprobante tras revisión humana explícita.

    La salida del modelo no puede aprobarse sola. Requiere revisado_humano=True.
    Conserva extracción original inmutable, campos corregidos, origen de corrección
    y eventos. Permite consultar por ID.
    """
    if datos.get('revisado_humano') is not True:
        raise ValueError('El registro de comprobante requiere revisión humana explícita (revisado_humano=true).')

    archivo_id = datos.get('archivo_id')
    if not archivo_id:
        raise ValueError('Se requiere archivo_id.')

    fila_archivo = db.execute('SELECT * FROM archivos_ingresados WHERE id=?', (archivo_id,)).fetchone()
    if not fila_archivo:
        raise ValueError('El archivo referenciado no existe.')

    comprobante_id = 'COMP-' + uuid4().hex[:12]
    ahora = _ahora()
    modelo = datos.get('modelo', OCR_MODEL)
    version_prompt = datos.get('version_prompt', 'v1')
    extraccion_original = json.dumps(datos.get('extraccion_original', {}), ensure_ascii=False)

    db.execute('BEGIN IMMEDIATE')
    try:
        db.execute(
            '''
            INSERT INTO comprobantes
                (id, archivo_id, modelo, version_prompt, extraccion_original,
                 estado_extraccion, fecha_creacion, fecha_revision, revisado_por, notas_revision)
            VALUES (?, ?, ?, ?, ?, 'revisada', ?, ?, ?, ?)
            ''',
            (
                comprobante_id, archivo_id, modelo, version_prompt, extraccion_original,
                ahora, ahora,
                datos.get('revisado_por', 'operador'),
                datos.get('notas_revision'),
            ),
        )

        for correccion in datos.get('correcciones', []):
            db.execute(
                '''
                INSERT INTO correcciones
                    (comprobante_id, campo, valor_original, valor_corregido, origen_correccion, fecha_correccion)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    comprobante_id,
                    correccion.get('campo'),
                    json.dumps(correccion.get('valor_original'), ensure_ascii=False) if correccion.get('valor_original') is not None else None,
                    json.dumps(correccion.get('valor_corregido'), ensure_ascii=False) if correccion.get('valor_corregido') is not None else None,
                    'revisor_humano',
                    ahora,
                ),
            )

        db.execute(
            '''
            INSERT INTO eventos(tabla_origen, registro_id, tipo_evento, detalle, fecha_evento)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                'comprobantes', comprobante_id, 'revision',
                json.dumps({'archivo_id': archivo_id, 'modelo': modelo}, ensure_ascii=False),
                ahora,
            ),
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        'id': comprobante_id,
        'archivo_id': archivo_id,
        'modelo': modelo,
        'version_prompt': version_prompt,
        'estado': 'revisada',
        'fecha_creacion': ahora,
    }


def preparar_operacion(datos: dict, db):
    """Ejercicio 2: crea una propuesta persistente, versionada y pendiente.

    No ejecuta cambios comerciales. Requiere archivo_id (comprobante revisado),
    naturaleza, importe_aplicado. Monto y fecha son indicios, no prueba de coincidencia.
    """
    archivo_id = datos.get('archivo_id')
    naturaleza = datos.get('naturaleza')
    importe_aplicado = datos.get('importe_aplicado')
    moneda = datos.get('moneda', 'COP')
    venta_id = datos.get('venta_id')  # opcional: se selecciona entre candidatos
    motivo = datos.get('motivo')
    referencias = datos.get('referencias')

    if naturaleza not in ('cobro', 'financiación', 'gasto'):
        raise ValueError('Naturaleza inválida. Use cobro, financiación o gasto.')
    try:
        importe_aplicado = int(importe_aplicado)
    except (TypeError, ValueError):
        raise ValueError('Importe aplicado inválido. Debe ser un entero positivo en COP.')
    if importe_aplicado <= 0:
        raise ValueError('Importe aplicado inválido. Debe ser mayor a cero.')

    # Verificar que el comprobante exista y esté revisado.
    if archivo_id:
        comprobante = db.execute(
            'SELECT id, estado_extraccion FROM comprobantes WHERE archivo_id=?', (archivo_id,)
        ).fetchone()
        if not comprobante:
            raise ValueError('No existe un comprobante revisado para ese archivo.')
        if comprobante['estado_extraccion'] != 'revisada':
            raise ValueError('El comprobante debe estar revisado antes de asociar una operación.')

    clave_idempotente = 'PROP-' + uuid4().hex[:12]
    ahora = _ahora()

    db.execute('BEGIN IMMEDIATE')
    try:
        propuesta_id = 'PROP-' + uuid4().hex[:12]
        datos_exactos = json.dumps({
            'archivo_id': archivo_id,
            'naturaleza': naturaleza,
            'importe_aplicado': importe_aplicado,
            'moneda': moneda,
            'venta_id': venta_id,
            'motivo': motivo,
            'referencias': referencias,
        }, ensure_ascii=False)

        db.execute(
            '''
            INSERT INTO propuestas
                (id, version, tipo_operacion, datos_exactos, evidencia, estado,
                 fecha_creacion, clave_idempotente)
            VALUES (?, 1, ?, ?, ?, 'pendiente', ?, ?)
            ''',
            (
                propuesta_id, naturaleza, datos_exactos,
                json.dumps(referencias, ensure_ascii=False) if referencias else None,
                ahora, clave_idempotente,
            ),
        )

        db.execute(
            '''
            INSERT INTO eventos(tabla_origen, registro_id, tipo_evento, detalle, fecha_evento)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                'propuestas', propuesta_id, 'preparacion',
                json.dumps({'naturaleza': naturaleza, 'importe_aplicado': importe_aplicado}, ensure_ascii=False),
                ahora,
            ),
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        'id': propuesta_id,
        'version': 1,
        'archivo_id': archivo_id,
        'venta_id': venta_id,
        'naturaleza': naturaleza,
        'importe_aplicado': importe_aplicado,
        'moneda': moneda,
        'motivo': motivo,
        'referencias': referencias,
        'estado_financiero': 'no_verificado',
        'estado': 'pendiente',
        'clave_idempotente': clave_idempotente,
        'fecha_creacion': ahora,
    }


def aprobar_propuesta(propuesta_id: str, db, aprobado_por: str = 'operador'):
    """Ejercicio 2: aprueba una propuesta pendiente. Acción humana emitida por servidor.

    Un approved=true del cuerpo o del modelo no sustituye este paso.
    """
    ahora = _ahora()

    db.execute('BEGIN IMMEDIATE')
    try:
        propuesta = db.execute(
            'SELECT * FROM propuestas WHERE id=?', (propuesta_id,)
        ).fetchone()
        if not propuesta:
            raise ValueError('La propuesta no existe.')
        if propuesta['estado'] != 'pendiente':
            raise ValueError('Solo se pueden aprobar propuestas pendientes.')

        # La versión no cambia al aprobar: solo cambia si se modifica el contenido.
        nueva_version = propuesta['version']

        db.execute(
            '''
            UPDATE propuestas
            SET estado='aprobada', aprobado_por=?, fecha_aprobacion=?, version=?
            WHERE id=?
            ''',
            (aprobado_por, ahora, nueva_version, propuesta_id),
        )

        db.execute(
            '''
            INSERT INTO eventos(tabla_origen, registro_id, tipo_evento, detalle, fecha_evento)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                'propuestas', propuesta_id, 'aprobacion',
                json.dumps({'aprobado_por': aprobado_por, 'version': nueva_version}, ensure_ascii=False),
                ahora,
            ),
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        'id': propuesta_id,
        'version': nueva_version,
        'estado': 'aprobada',
        'aprobado_por': aprobado_por,
        'fecha_aprobacion': ahora,
    }


def registrar_operacion_aprobada(datos: dict, db):
    """Ejercicio 2: valida aprobación en servidor y ejecuta una sola vez.

    Requiere propuesta_id, versión y clave_idempotente. Si la versión no coincide
    con la aprobada, la aprobación está invalidada. La clave idempotente UNIQUE
    garantiza un solo efecto comercial.
    """
    propuesta_id = datos.get('propuesta_id')
    version = datos.get('version')
    clave_idempotente = datos.get('clave_idempotente')

    if not propuesta_id or version is None or not clave_idempotente:
        raise ValueError('Se requieren propuesta_id, versión y clave idempotente.')

    ahora = _ahora()

    db.execute('BEGIN IMMEDIATE')
    try:
        propuesta = db.execute(
            'SELECT * FROM propuestas WHERE id=?', (propuesta_id,)
        ).fetchone()
        if not propuesta:
            raise ValueError('La propuesta no existe.')
        if propuesta['resultado'] is not None:
            raise ValueError('La propuesta ya fue ejecutada.')
        if propuesta['estado'] != 'aprobada':
            raise ValueError('La propuesta no está aprobada.')
        if str(propuesta['version']) != str(version):
            raise ValueError(
                f'La versión de la propuesta no coincide ({propuesta["version"]} vs {version}). '
                'La aprobación fue invalidada.'
            )
        if propuesta['clave_idempotente'] != clave_idempotente:
            raise ValueError('La clave idempotente no coincide.')
        if propuesta['resultado'] is not None:
            raise ValueError('La propuesta ya fue ejecutada.')

        datos_op = json.loads(propuesta['datos_exactos'])

        # Resolver el comprobante_id a partir del archivo_id (FK requiere comprobantes.id).
        comprobante_id = None
        if datos_op.get('archivo_id'):
            fila_comp = db.execute(
                'SELECT id FROM comprobantes WHERE archivo_id=?', (datos_op['archivo_id'],)
            ).fetchone()
            if not fila_comp:
                raise ValueError('No se encontró el comprobante asociado al archivo.')
            comprobante_id = fila_comp['id']

        # Crear operación reportada (estado financiero no_verificado).
        operacion_id = 'OPE-' + uuid4().hex[:12]
        db.execute(
            '''
            INSERT INTO operaciones_reportadas
                (id, comprobante_id, naturaleza, monto, moneda, referencias,
                 estado_financiero, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, 'no_verificado', ?)
            ''',
            (
                operacion_id, comprobante_id, datos_op['naturaleza'],
                datos_op['importe_aplicado'], datos_op.get('moneda', 'COP'),
                datos_op.get('referencias'), ahora,
            ),
        )

        # Vincular soporte si hay archivo.
        if datos_op.get('archivo_id'):
            db.execute(
                '''
                INSERT INTO soportes_operacion (operacion_id, archivo_id)
                VALUES (?, ?)
                ''',
                (operacion_id, datos_op['archivo_id']),
            )

        # Crear vínculo comercial si hay venta seleccionada.
        vinculo_id = None
        if datos_op.get('venta_id'):
            vinculo_id = 'VINC-' + uuid4().hex[:12]
            db.execute(
                '''
                INSERT INTO vinculos_comerciales
                    (id, operacion_id, venta_id, importe_aplicado, aprobado_por_propuesta, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    vinculo_id, operacion_id, datos_op['venta_id'],
                    datos_op['importe_aplicado'], propuesta_id, ahora,
                ),
            )

        # Marcar propuesta como ejecutada con resultado.
        resultado = json.dumps(
            {'operacion_id': operacion_id, 'vinculo_id': vinculo_id, 'idempotente': clave_idempotente},
            ensure_ascii=False,
        )
        db.execute(
            'UPDATE propuestas SET estado=\'ejecutada\', resultado=? WHERE id=?',
            (resultado, propuesta_id),
        )

        db.execute(
            '''
            INSERT INTO eventos(tabla_origen, registro_id, tipo_evento, detalle, fecha_evento)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                'propuestas', propuesta_id, 'ejecucion',
                json.dumps({'operacion_id': operacion_id, 'vinculo_id': vinculo_id,
                            'idempotente': clave_idempotente}, ensure_ascii=False),
                ahora,
            ),
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        'id': operacion_id,
        'propuesta_id': propuesta_id,
        'version': propuesta['version'],
        'estado': 'ejecutada',
        'clave_idempotente': clave_idempotente,
        'operacion_id': operacion_id,
        'vinculo_id': vinculo_id,
    }


# ---------------------------------------------------------------------------
# Ejercicio 3 · Crear la venta faltante
# ---------------------------------------------------------------------------

def _entero_positivo(valor, nombre):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f'{nombre} debe ser un número entero.')
    if numero <= 0:
        raise ValueError(f'{nombre} debe ser mayor que cero.')
    return numero


def _normalizar_lineas(db, lineas):
    """Valida las líneas confirmadas contra el catálogo y calcula sus importes.

    El precio omitido se toma del catálogo (fuente comercial). El total nunca se
    calcula con aritmética del modelo, sino con cantidad × precio confirmado.
    """
    if not isinstance(lineas, list):
        raise ValueError('Las líneas deben ser una lista de objetos.')

    vistos = set()
    resultado = []
    for posicion, linea in enumerate(lineas, 1):
        if not isinstance(linea, dict):
            raise ValueError(f'La línea {posicion} no es válida.')
        codigo = str(linea.get('producto_codigo') or '').strip()
        if not codigo:
            raise ValueError(f'La línea {posicion} no tiene producto_codigo.')
        if codigo in vistos:
            raise ValueError(f'El producto {codigo} aparece más de una vez; unifica la cantidad.')
        vistos.add(codigo)

        producto = db.execute('SELECT precio_venta FROM productos WHERE codigo=?', (codigo,)).fetchone()
        if not producto:
            raise ValueError(f'El producto {codigo} no existe en el catálogo.')

        cantidad = _entero_positivo(linea.get('cantidad'), f'La cantidad de {codigo}')
        precio = linea.get('precio_unitario')
        if precio is None or precio == '':
            precio = producto['precio_venta']
        else:
            try:
                precio = int(precio)
            except (TypeError, ValueError):
                raise ValueError(f'El precio de {codigo} debe ser un entero en COP.')
            if precio < 0:
                raise ValueError(f'El precio de {codigo} no puede ser negativo.')

        resultado.append({
            'producto_codigo': codigo,
            'cantidad': cantidad,
            'precio_unitario': int(precio),
        })
    return resultado


def preparar_venta_faltante(datos: dict, db):
    """Ejercicio 3: prepara (o actualiza) la propuesta de una venta faltante.

    Mantiene borradores incompletos: si falta la fecha comercial o las líneas, la
    propuesta queda en estado pendiente con ``completo=False`` y no puede
    ejecutarse. Al actualizar una propuesta existente se incrementa la versión y,
    si estaba aprobada, se invalida su aprobación.
    """
    archivo_id = datos.get('archivo_id')
    if not archivo_id:
        raise ValueError('Se requiere el archivo del comprobante revisado.')

    naturaleza = datos.get('naturaleza') or 'cobro'
    if naturaleza != 'cobro':
        raise ValueError('Solo se puede crear una venta faltante para una operación de cobro.')

    comprobante = db.execute(
        'SELECT id, estado_extraccion FROM comprobantes WHERE archivo_id=?', (archivo_id,)
    ).fetchone()
    if not comprobante:
        raise ValueError('No existe un comprobante revisado para ese archivo.')
    if comprobante['estado_extraccion'] != 'revisada':
        raise ValueError('El comprobante debe estar revisado antes de crear una venta.')

    fecha_comercial = datos.get('fecha_comercial') or None
    if fecha_comercial:
        try:
            date.fromisoformat(str(fecha_comercial))
        except ValueError:
            raise ValueError('La fecha comercial debe ser una fecha válida YYYY-MM-DD.')

    lineas_crudas = datos.get('lineas') or []
    lineas = _normalizar_lineas(db, lineas_crudas) if lineas_crudas else []
    total = sum(l['cantidad'] * l['precio_unitario'] for l in lineas)

    faltantes = []
    if not fecha_comercial:
        faltantes.append('fecha_comercial')
    if not lineas:
        faltantes.append('lineas')
    completo = not faltantes

    contenido = {
        'archivo_id': archivo_id,
        'naturaleza': 'cobro',
        'fecha_comercial': fecha_comercial,
        'cliente': (datos.get('cliente') or None),
        'factura_externa': (datos.get('factura_externa') or None),
        'lineas': lineas,
        'total': total,
        'moneda': 'COP',
        'completo': completo,
        'faltantes': faltantes,
    }
    datos_exactos = json.dumps(contenido, ensure_ascii=False)
    evidencia = json.dumps({'archivo_id': archivo_id, 'total': total}, ensure_ascii=False)
    ahora = _ahora()
    propuesta_id = datos.get('propuesta_id')

    db.execute('BEGIN IMMEDIATE')
    try:
        if propuesta_id:
            existente = db.execute('SELECT * FROM propuestas WHERE id=?', (propuesta_id,)).fetchone()
            if not existente:
                raise ValueError('La propuesta que se intenta actualizar no existe.')
            if existente['tipo_operacion'] != 'crear_venta':
                raise ValueError('La propuesta no corresponde a la creación de una venta.')
            if existente['estado'] == 'ejecutada':
                raise ValueError('No se puede modificar una propuesta ya ejecutada.')
            version = existente['version'] + 1
            clave_idempotente = existente['clave_idempotente']
            db.execute(
                '''
                UPDATE propuestas
                SET version=?, datos_exactos=?, evidencia=?, estado='pendiente',
                    aprobado_por=NULL, fecha_aprobacion=NULL
                WHERE id=?
                ''',
                (version, datos_exactos, evidencia, propuesta_id),
            )
        else:
            propuesta_id = 'PROP-' + uuid4().hex[:12]
            version = 1
            clave_idempotente = 'KEY-' + uuid4().hex[:12]
            db.execute(
                '''
                INSERT INTO propuestas
                    (id, version, tipo_operacion, datos_exactos, evidencia, estado,
                     fecha_creacion, clave_idempotente)
                VALUES (?, ?, 'crear_venta', ?, ?, 'pendiente', ?, ?)
                ''',
                (propuesta_id, version, datos_exactos, evidencia, ahora, clave_idempotente),
            )

        db.execute(
            '''
            INSERT INTO eventos(tabla_origen, registro_id, tipo_evento, detalle, fecha_evento)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                'propuestas', propuesta_id, 'preparacion_venta',
                json.dumps({'version': version, 'completo': completo, 'faltantes': faltantes}, ensure_ascii=False),
                ahora,
            ),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        'id': propuesta_id,
        'version': version,
        'tipo_operacion': 'crear_venta',
        'archivo_id': archivo_id,
        'fecha_comercial': fecha_comercial,
        'cliente': contenido['cliente'],
        'factura_externa': contenido['factura_externa'],
        'lineas': lineas,
        'total': total,
        'moneda': 'COP',
        'completo': completo,
        'faltantes': faltantes,
        'estado': 'pendiente',
        'clave_idempotente': clave_idempotente,
        'fecha_creacion': ahora,
    }


def registrar_venta_aprobada(datos: dict, db):
    """Ejercicio 3: crea la venta, sus líneas y el vínculo en una sola transacción.

    Requiere una propuesta aprobada y completa. No toca inventario. Repetir la
    misma confirmación devuelve el resultado existente sin duplicar la venta.
    """
    propuesta_id = datos.get('propuesta_id')
    version = datos.get('version')
    clave_idempotente = datos.get('clave_idempotente')
    if not propuesta_id or version is None or not clave_idempotente:
        raise ValueError('Se requieren propuesta_id, versión y clave idempotente.')

    ahora = _ahora()

    db.execute('BEGIN IMMEDIATE')
    try:
        propuesta = db.execute('SELECT * FROM propuestas WHERE id=?', (propuesta_id,)).fetchone()
        if not propuesta:
            raise ValueError('La propuesta no existe.')
        if propuesta['tipo_operacion'] != 'crear_venta':
            raise ValueError('La propuesta no corresponde a la creación de una venta.')

        resultado_existente = json.loads(propuesta['resultado']) if propuesta['resultado'] else None
        if resultado_existente is not None:
            if propuesta['clave_idempotente'] == clave_idempotente:
                return {**resultado_existente, 'estado': 'ejecutada', 'idempotente': True}
            raise ValueError('La propuesta ya fue ejecutada.')

        if propuesta['estado'] != 'aprobada':
            raise ValueError('La propuesta no está aprobada.')
        if str(propuesta['version']) != str(version):
            raise ValueError(
                f'La versión de la propuesta no coincide ({propuesta["version"]} vs {version}). '
                'La aprobación fue invalidada.'
            )
        if propuesta['clave_idempotente'] != clave_idempotente:
            raise ValueError('La clave idempotente no coincide.')

        datos_op = json.loads(propuesta['datos_exactos'])
        lineas = datos_op.get('lineas') or []
        if not datos_op.get('completo') or not datos_op.get('fecha_comercial') or not lineas:
            raise ValueError('La venta está incompleta: faltan fecha comercial o líneas confirmadas.')

        lineas = _normalizar_lineas(db, lineas)

        venta_id = 'V-' + uuid4().hex[:12]
        db.execute(
            'INSERT INTO ventas(id,fecha_comercial,cliente,factura_externa,moneda,origen) '
            "VALUES(?,?,?,?,'COP','practica_ficticia')",
            (venta_id, datos_op['fecha_comercial'], datos_op.get('cliente'), datos_op.get('factura_externa')),
        )
        db.executemany(
            'INSERT INTO venta_lineas(venta_id,producto_codigo,cantidad,precio_unitario) VALUES(?,?,?,?)',
            [(venta_id, l['producto_codigo'], l['cantidad'], l['precio_unitario']) for l in lineas],
        )
        total = db.execute(
            'SELECT SUM(cantidad*precio_unitario) FROM venta_lineas WHERE venta_id=?', (venta_id,)
        ).fetchone()[0] or 0

        operacion_id = None
        vinculo_id = None
        archivo_id = datos_op.get('archivo_id')
        if archivo_id:
            comprobante = db.execute(
                'SELECT id FROM comprobantes WHERE archivo_id=?', (archivo_id,)
            ).fetchone()
            if not comprobante:
                raise ValueError('No se encontró el comprobante revisado del soporte.')

            operacion_id = 'OPE-' + uuid4().hex[:12]
            db.execute(
                '''
                INSERT INTO operaciones_reportadas
                    (id, comprobante_id, naturaleza, monto, moneda, referencias,
                     estado_financiero, fecha_creacion)
                VALUES (?, ?, 'cobro', ?, 'COP', NULL, 'no_verificado', ?)
                ''',
                (operacion_id, comprobante['id'], total, ahora),
            )
            db.execute(
                'INSERT INTO soportes_operacion(operacion_id, archivo_id) VALUES(?, ?)',
                (operacion_id, archivo_id),
            )
            vinculo_id = 'VINC-' + uuid4().hex[:12]
            db.execute(
                '''
                INSERT INTO vinculos_comerciales
                    (id, operacion_id, venta_id, importe_aplicado, aprobado_por_propuesta, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (vinculo_id, operacion_id, venta_id, total, propuesta_id, ahora),
            )

        resultado = json.dumps(
            {'venta_id': venta_id, 'total': total, 'operacion_id': operacion_id, 'vinculo_id': vinculo_id},
            ensure_ascii=False,
        )
        db.execute("UPDATE propuestas SET estado='ejecutada', resultado=? WHERE id=?", (resultado, propuesta_id))
        db.execute(
            '''
            INSERT INTO eventos(tabla_origen, registro_id, tipo_evento, detalle, fecha_evento)
            VALUES (?, ?, ?, ?, ?)
            ''',
            ('propuestas', propuesta_id, 'creacion_venta', resultado, ahora),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        'id': venta_id,
        'venta_id': venta_id,
        'propuesta_id': propuesta_id,
        'version': propuesta['version'],
        'total': total,
        'operacion_id': operacion_id,
        'vinculo_id': vinculo_id,
        'estado': 'ejecutada',
        'idempotente': False,
    }
