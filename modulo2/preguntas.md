# Preguntas de negocio — Módulo 2 (Ruta A Taskmaster)

Acordadas con la participante antes de diseñar la tabla. Muestra: 200 de `restaurant-table-1 + 2`.

## P1 — Demanda por restaurante, zona y grupo

¿Qué restaurantes y zonas concentran más solicitudes y con qué tamaño de grupo?

- Evidencia esperada: top restaurantes + zona + distribución de `personas`, con `conversation_id` citados.

## P2 — Cierre aceptado vs rechazado

¿Cuál es la tasa de aceptación vs rechazo y en qué punto se cae la reserva?

- Evidencia esperada: tasa `estado=aceptado` vs `rechazado/pendiente` + campo que falla (horario, seating, disponibilidad).

## P3 — Fricción por horario y seating

¿Qué horarios o tipos de seating generan más rechazos y qué alternativa propone el asistente?

- Evidencia esperada: rechazos por `fecha_hora`/`seating` + alternativa ofrecida en el turno siguiente.
