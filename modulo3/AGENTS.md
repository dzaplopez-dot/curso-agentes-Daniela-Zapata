# Instrucciones del proyecto

## Alcance

- Consultar productos, proveedores e inventario.
- Proponer reposición sin modificar existencias.
- Usar SQLite como fuente de los valores exactos.

## Roles especializados (.opencode/agents/)

- **software**: implementa `src/db.py`, `src/herramientas.py` y `src/app.py`. Solo SELECT, nunca UPDATE/INSERT/DELETE en inventario.
- **datos**: owns `scripts/importar_excel.py`, reconcilia 75 / 1250 / 827 / 73 / 0 inválidas, garantiza idempotencia (temporal + replace).
- **qa**: owns `tests/`, ejecuta los 9 casos, conserva evidencia en `logs/` y bloquea entrega si algo falla.

## Reglas obligatorias

- Trabaja primero en modo Plan.
- No modifiques el Excel original (`datos/original/*.xlsm` intacto, no ejecutar macros).
- No inventes datos ausentes: si no existe, decláralo + cita fuente.
- Usa SQL para cantidades, precios y fechas exactas.
- Ejecuta las pruebas después de cambiar código.
- No escribas inventario ni registres compras sin aprobación.
- Todo resultado cita fuente (tabla + fila_origen cuando aplique).
- Propuesta de reposición reproducible: `cantidad = max(0, stock_minimo - stock_total)`.

## Definición de terminado

```bash
uv sync
uv run python scripts/importar_excel.py datos/original/operacion_comercial_app.xlsm datos/procesados/inventario.db
uv run pytest
uv run python -m src.app
```
