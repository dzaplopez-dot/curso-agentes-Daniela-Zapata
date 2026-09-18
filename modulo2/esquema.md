# Esquema — Módulo 2 (Ruta A Taskmaster)

Una fila = una reserva (una conversación `restaurant-table-1/2`).

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| conversation_id | texto | sí | ID original, trazabilidad |
| restaurante | texto | no | nombre explícito, si no `pendiente` |
| zona | texto | no | location explícita, si no `pendiente` |
| fecha_hora | texto | no | time.reservation explícito, si no `pendiente` |
| personas | entero | no | num.guests explícito, si no `pendiente` |
| seating | texto | no | tipo seating explícito, si no `pendiente` |
| estado | `aceptado \| rechazado \| pendiente` | sí | ver reglas abajo |

Reglas de estado:
- `aceptado` solo si hay anotación `restaurant_reservation.reservation.accept` o accept explícito de nombre+hora+grupo sin rechazo posterior.
- `rechazado` si hay `*.reject` sin accept posterior que lo revierta.
- En otro caso `pendiente` + motivo en `pendientes.csv`.
- Solo datos explícitos. Nada inventado.
- `procesados (200) + pendientes por campo` explica toda la entrada. Archivo original intacto.
