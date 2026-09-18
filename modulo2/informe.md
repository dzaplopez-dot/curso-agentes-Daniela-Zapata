# Informe — Módulo 2

**Participante:** Daniela Zapata López
**Ruta:** A · Taskmaster-1 `restaurant-table-1 + 2`
**Muestra:** 200 (seed 7) · **Fecha:** 2026-09-18
**Reproducir:** `python3 modulo2/scripts/procesar.py --n 200 --seed 7`

## P1 — Demanda por restaurante, zona y grupo

- **Respuesta:** demanda muy dispersa por restaurante (190/200 con nombre, casi uno distinto por conversación, sin top dominante) y cobertura parcial de zona (131/200, 69 pendientes). El grupo típico es **2 personas (65/200, 32.5%)** seguido de **4 personas (50/200, 25%)** y 3 personas (21/200).
- **Evidencia:** `datos.csv` — ej. `dlg-4697818d-5ec8-430a-9e51-c644ca3b5ae9` (Prime, 2 personas), `dlg-c4051045-d0f4-4d3d-9516-c8629cb82398` (Five Guys, 4 personas), `dlg-91674224-c8a0-4c12-8756-dd1237870c42` (Iyesare, Four). Menciones horarias concentradas 7pm (85), 8pm (59), 6pm (42).

## P2 — Cierre aceptado vs rechazado

- **Respuesta:** tasa **aceptado 46/200 (23%)**, **rechazado 127/200 (63.5%)**, **pendiente 27/200 (13.5%)** con regla conservadora (`reservation.accept` = aceptado). El punto de caída es la disponibilidad del horario/seating pedido: el rechazo aparece como `*.reject` sin `reservation.accept` posterior. Campos que más faltan: zona (69 pendientes) y seating (48 pendientes); fecha_hora casi siempre presente (196/200).
- **Evidencia:** `datos.csv` — ej. aceptado `dlg-91674224-c8a0-4c12-8756-dd1237870c42`; rechazado `dlg-4697818d-5ec8-430a-9e51-c644ca3b5ae9` (7:00 pm sin disponibilidad). Conteos verificables en dashboard.

## P3 — Fricción por horario y seating

- **Respuesta:** la fricción se concentra en **horario pico 6–8pm** (7pm 85 menciones, 8pm 59, 6pm 42) y seating específico (outdoor/booth). Patrón del asistente ante el rechazo: **ofrecer la alternativa más cercana** — ej. "nada para las 7:00, pero sí 6:30 o 7:30 para dos" (`dlg-4697818d…`); "Babette's no tiene outdoor" + sin mesas 8PM (`dlg-153bb3f7…`). En rechazados, 30/127 ni siquiera fijan seating (pendiente) y el resto pide booth/outdoor puntuales.
- **Evidencia:** `dlg-4697818d-5ec8-430a-9e51-c644ca3b5ae9`, `dlg-153bb3f7-1832-482f-bebf-426e89fcb7d6`, `dlg-20e30538-a316-413e-bba6-e8f803b4cd3d` (ver turnos con `.reject` en el original).

## Límites conocidos y decisiones

- Solo anotaciones explícitas de Taskmaster; texto sin anotar → `pendiente` (167 registros en `pendientes.csv`).
- `estado` conservador: solo `reservation.accept` cuenta como aceptado (46/200). Un rechazo parcial (ej. hora) marca `rechazado` aunque haya alternativa; la alternativa se documenta en P3, no cambia el estado.
- `personas` a veces en texto ("two", "Four") y un caso con número espurio de dirección; no se normalizó a entero para no inventar.
- `fecha_hora` relativa ("tonight at 7 pm") sin fecha base; se conserva texto.
- Muestra 200 de 1.198 `restaurant-table-1/2` (seed 7); no generalizar a los 7.708 ni a otros dominios (pizza, uber, etc.).

## Recomendación

- **Asegurar zona + seating desde el primer turno y ofrecer alternativa horaria inmediata en pico 6–8pm:** son los campos con más pendientes (zona 69, seating 48) y la fricción verificada; preguntar zona/seating antes de consultar disponibilidad y, si el slot pedido falla, proponer ±30–60 min en el mismo turno (patrón que ya usa el asistente en los casos citados).
