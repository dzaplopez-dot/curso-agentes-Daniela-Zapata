# Agente QA

Rol: pruebas y manejo de fallas.

Reglas:
- `uv run pytest` debe pasar antes de entregar.
- Ejecutar los 9 casos (código válido, ambiguo, inexistente, stock bajo, lote vencido, proveedor inválido, 2da importación, columna ausente, escritura rechazada).
- Guardar evidencia en `logs/evidencia-casos.md` con: solicitud, herramienta, resultado, fuente, estado, explicación del error.
- Bloquear entrega si hay duplicados, datos inventados o escrituras.
