# Inventario inteligente — Módulo 3 (Comercial La Esquina)

Asistente local de terminal que consulta existencias, vencimientos y propone reposición **sin modificar el inventario**. Base SQLite reconstruible desde el Excel original.

## Instalación y comandos

```bash
uv sync
uv run python scripts/importar_excel.py datos/original/operacion_comercial_app.xlsm datos/procesados/inventario.db
uv run pytest
uv run python -m src.app
```

La aplicación corre localmente en la terminal. Ejemplos: `FER-0001` | `busca martillo` | `bajo minimo` | `vencidos` | `ayuda`.

## Reconciliación

75 proveedores / 1250 productos / 827 inventario / 73 bajo el mínimo / 0 relaciones inválidas. Segunda importación no duplica (temporal + replace).

## Herramientas (6, sin IA)

`obtener_producto`, `buscar_productos`, `consultar_existencias`, `productos_bajo_minimo`, `consultar_vencimientos` (+ `vencimiento_por_producto`), `proponer_reposicion`. Ver `src/herramientas.py`. Regla de reposición: `cantidad = max(0, stock_minimo - stock_total)`.

## Errores, límites y decisiones

- Producto inexistente: se declara, no se inventa (Fuente: productos).
- Nombre ambiguo: se listan candidatos y se pide precisión.
- Lote vencido: se separa del disponible (`fecha_vencimiento < hoy`).
- Proveedor inválido / columna ausente: la carga se detiene y señala el error (rollback, sin parciales).
- Escritura no autorizada: se rechaza con mensaje fijo, la base queda intacta.
- Límite: consulta y propone. No modifica existencias, no registra compras, no oculta filas inválidas.

## Evidencia

Ver `logs/evidencia-casos.md` (9 casos con solicitud, herramienta, resultado, fuente, estado y explicación).
