# Evidencia de ejecución — 9 casos (2026-10-13)

Comandos base:
```bash
uv sync
uv run python scripts/importar_excel.py datos/original/operacion_comercial_app.xlsm datos/procesados/inventario.db
uv run pytest
uv run python -m src.app
```
Resultado importación: Proveedores 75 / Productos 1250 / Inventario 827 / Bajo mínimo 73 / Relaciones inválidas 0.
Resultado pytest: 11 passed.

## 1. Código válido — APROBADA
- Solicitud: `FER-0001`
- Herramienta: `obtener_producto + consultar_existencias`
- Resultado: Martillo de uña Forte Mini, stock total 141, mínimo 10, estado OK, lote LT-2506251 (fila 498)
- Fuente: productos + proveedores + inventario

## 2. Nombre ambiguo — APROBADA
- Solicitud: `busca Martillo`
- Herramienta: `buscar_productos`
- Resultado: 10 coincidencias (FER-0007, FER-0002, FER-0006, FER-0001...), pide precisar código
- Fuente: productos.nombre LIKE

## 3. Producto inexistente — APROBADA
- Solicitud: `XXX-9999`
- Herramienta: `obtener_producto`
- Resultado: "El código XXX-9999 no existe en productos. No invento información."
- Fuente: productos

## 4. Stock bajo — APROBADA
- Solicitud: `bajo minimo`
- Herramienta: `productos_bajo_minimo + proponer_reposicion`
- Resultado: 73 productos bajo mínimo (ej. PAP-0028 stock 0 min 20 sugerido 20). Regla cantidad = max(0, minimo - stock)
- Fuente: inventario

## 5. Lote vencido — APROBADA
- Solicitud: `vencidos` y `ABA-0220 vencido`
- Herramienta: `consultar_vencimientos + vencimiento_por_producto`
- Resultado: 140 lotes vencidos separados. Ej. ABA-0220: disponible 0, vencido 8 (LT-2602617 fv 2025-04-28 fila 6)
- Fuente: inventario.fecha_vencimiento < hoy (2026-10-13)

## 6. Proveedor inválido — APROBADA
- Solicitud: importar fila con proveedor PRV-999 inexistente
- Herramienta: `scripts/importar_excel.py` (PRAGMA foreign_key_check + FK SQLite)
- Resultado: detenido, `FOREIGN KEY constraint failed` / `Se encontraron relaciones inválidas`. No inserta parcial (rollback)
- Fuente: productos.proveedor_id -> proveedores.id

## 7. Segunda importación — APROBADA
- Solicitud: ejecutar el conversor otra vez sobre la misma base
- Herramienta: `convertir()` (temporal + replace, UNIQUE producto_codigo+lote)
- Resultado: conteos idénticos 75/1250/827/73, sin duplicados
- Fuente: datos/procesados/inventario.db

## 8. Columna ausente — APROBADA
- Solicitud: copia del Excel sin columna `Código` en Productos (fila 4 col 1 vacía)
- Herramienta: `validar_columnas()` en importador
- Resultado: detenido, "Columna ausente en 'Productos': se esperaba 'Código' en la columna 1 (fila 4). Carga detenida."
- Fuente: libro Productos fila 4

## 9. Escritura no autorizada — APROBADA
- Solicitud: `cambia el stock de FER-0001 a 500`
- Herramienta: `responder()` detector de escritura
- Resultado: "RECHAZADO: No puedo modificar el inventario. Solo consulto... La base no fue alterada."
- Fuente: ninguna escritura ejecutada (verificado: conteos intactos tras el rechazo)
