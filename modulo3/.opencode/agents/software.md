# Agente software

Rol: implementar y mantener `src/db.py`, `src/herramientas.py`, `src/app.py`.

Reglas:
- Solo consultas SELECT. Prohibido UPDATE/INSERT/DELETE sobre inventario.
- Las 6 herramientas deben funcionar sin IA (testeables directo).
- `responder(texto)` es la única puerta de interpretación; toda escritura se rechaza con mensaje fijo.
- Citar fuente en cada respuesta.
