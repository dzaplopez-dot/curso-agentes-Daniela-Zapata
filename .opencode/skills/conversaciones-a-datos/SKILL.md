---
name: conversaciones-a-datos
description: Convierte conversaciones en datos verificables
---

# Conversaciones a datos

Convierte 100–300 conversaciones en una tabla verificable que un agente pueda consultar. No modifica el archivo original. Todo registro conserva `conversation_id` y es trazable a su evidencia.

## Entrada

Dos rutas posibles, elegir UNA sola por entregable. No combinar.

### Ruta A · Taskmaster-1 (reservas restaurante)

- Archivo: `modulo2/datos/original/self-dialogs.json` (descargado de Taskmaster TM-1-2019)
- Estructura: `conversation_id → utterances[] → index · speaker · text`
- Fuente y licencia: https://github.com/google-research-datasets/Taskmaster/tree/master/TM-1-2019

### Ruta B · WhatsApp Hogar Colombia

- Archivo: `modulo2/datos/original/whatsapp-pedidos-hogar-colombia-200.json` (no usada en este entregable)

- Archivo: `modulo2/datos/original/whatsapp-pedidos-hogar-colombia-200.json`
- Estructura: `conversation_id → message_list[] → timestamp · from · to · text`
- 200 conversaciones sintéticas en español: pedidos, consultas, ciudades, costos de envío, tiempos de respuesta.

Regla: el archivo original se conserva sin cambios. Todo procesamiento lee de `datos/original/` y escribe en `datos/procesado/`.

## Proceso

1. **Definir preguntas primero.** Escribir 3 preguntas de negocio en `modulo2/preguntas.md` antes de diseñar la tabla.
2. **Diseñar esquema.** Definir en `modulo2/esquema.md` qué representa una fila, campos obligatorios, tipos y valores pendientes.
   - Ruta A (una fila = una reserva): `conversation_id, restaurante, zona, fecha_hora, personas, seating, estado` — elegida (muestra 200 de restaurant-table-1/2, seed 7)
   - Ruta B (una fila = un pedido o consulta): `conversation_id, contacto, tipo, productos, total, envio, estado, primera_respuesta_min`
3. **Extraer solo información verificable.** Si un dato no está explícito en la conversación, dejar `pendiente` y registrar el motivo en `pendientes.csv`. No inventar, no inferir teléfonos reales ni datos personales.
4. **Ejecutar sobre muestra.** Procesar 100–300 conversaciones con `modulo2/scripts/procesar.py` sin tocar el original.
5. **Reconciliar.** `procesados + pendientes = total entrada`. Verificar conteos, ids únicos, tipos, nulos y trazabilidad.

## Validación

- [ ] Original intacto (hash o tamaño registrado).
- [ ] Cada registro conserva `conversation_id`.
- [ ] Tipos y reglas documentados en `esquema.md`.
- [ ] `procesados + pendientes` explica toda la entrada.
- [ ] Nulos solo donde la conversación no trae el dato, con motivo en `pendientes.csv`.
- [ ] 3 preguntas respondidas con evidencia (ids de conversación citados).

## Salida

- `modulo2/datos/procesado/datos.csv` (o `.xlsx` / `.sqlite`) — tabla principal.
- `modulo2/datos/procesado/pendientes.csv` — pendientes y excepciones con `conversation_id, campo, motivo`.
- `modulo2/informe.md` — 3 respuestas con evidencia, límites conocidos y 1 recomendación de negocio.
- `modulo2/dashboard/index.html` — dashboard estático (interactivo es plus).

## Manejo de ambigüedad

- Texto ambiguo ("martillo fuerte pero pequeño", "lo de siempre") → `pendiente`, motivo `ambiguo`, no adjudicar.
- Varias coincidencias → pedir precisión, no elegir automáticamente.
- Fechas/horas relativas ("mañana", "esta noche") → normalizar solo si hay fecha base en la conversación; si no, `pendiente`.
- Privacidad: usar solo datasets suministrados. No incluir teléfonos reales ni datos identificables.
