# Agente datos

Rol: migración y reconciliación `scripts/importar_excel.py` -> `datos/procesados/inventario.db`.

Reglas:
- Excel original intacto en `datos/original/`, no ejecutar macros (openpyxl `data_only=True`).
- Validar hojas requeridas + columnas de fila 4; fallar alto y señalar columna/hoja.
- Verificar `PRAGMA foreign_key_check` = 0 relaciones inválidas.
- Idempotencia: escribir a `.temporal.db` y luego `replace`.
- Conteos esperados: 75 proveedores / 1250 productos / 827 inventario / 73 bajo mínimo.
