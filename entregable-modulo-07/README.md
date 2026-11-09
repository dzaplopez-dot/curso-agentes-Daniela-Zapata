# Entrega · Módulo 07 · Revisar un caso · Brilla Hogar

## Caso revisado: BH-S103 · Rosa Medina

### 1. ¿Qué pasó?
El 13 de octubre de 2026 a las 09:00, Rosa Medina canceló la reserva BH-S103 (limpieza estándar, 2 habitaciones / 1 baño, $135.000 COP) programada para ese día a las 19:00. Faltaban 10 horas para el servicio. Andrés Ríos informó un cobro del 25% del valor programado: $33.750 COP. Rosa aclaró que no tiene acuerdo firmado con Brilla Hogar y que cancelaba la visita, no que ya pagaba el cobro.

### 2. ¿Qué regla aplicaba en esa fecha?
Regla general del Documento 04 · Cancelaciones y falta de acceso (vigente desde 2026-10-01): entre 4 y 24 horas de anticipación se cobra el 50% del valor programado del servicio, salvo que el cliente tenga un acuerdo vigente propio. Rosa no tiene acuerdo propio, por tanto le aplica el 50%. (El 25% que Andrés aplicó pertenece al acuerdo de Dental Aurora, Documento 07, que no rige para Rosa.)

### 3. ¿Hubo un error o una excepción autorizada?
Hubo un error. No existe acuerdo propio de Rosa ni documentación de que Lucía Mora o Elena Ruiz aprobaran una excepción al 25% para este caso.
- Cobro correcto: 50% × $135.000 = **$67.500 COP**.
- Cobrado por Andrés: 25% × $135.000 = $33.750 COP (se cobró la mitad de lo que corresponde).
Además, el pago no debe marcarse como pagado sin verificación de operaciones (Documento 03).

### 4. ¿Qué mensajes y documentos respaldan la respuesta?
- Conversación BH-C014 (caso BH-S103): mensajes M002, M004, M005, M007, M008.
- Documento 04 · Cancelaciones y falta de acceso.
- Documento 02 · Tarifas aprobadas octubre 2026 (valor $135.000).
- Documento 07 · Acuerdo Dental Aurora (solo para contraste, no aplica a Rosa).
- Documento 03 · Procedimiento de reserva (pago por verificar).
Todas las fuentes están en la bóveda bajo `vault-brilla-hogar/fuentes/` y `vault-brilla-hogar/notas/`.

## Cómo consultar la memoria
En una sesión nueva (`/new`), sin volver a adjuntar los documentos, consultar la bóveda `brilla-hogar` con LLM Wiki y pedir que explique el caso BH-S103, qué regla aplicaba y qué se concluyó. Abrir las notas citadas y verificar que la respuesta coincida con lo guardado, distinguiendo la regla general de cualquier excepción.

## Resultado de la consulta en sesión nueva
La consulta recuperó la nota del caso BH-S103, la regla de cancelaciones (Documento 04) y las fuentes de la conversación BH-C014. La respuesta coincidió con lo guardado: error en el porcentaje de cancelación (25% informado vs 50% regla general), cobro correcto de $67.500 COP y pago pendiente de verificación. Se distinguió la regla general de la excepción de Dental Aurora.

## Documento 09 · Actualización de tarifa
Incorporado el documento 09 (fuente: `vault-brilla-hogar/fuentes/doc-09-cambio-autorizado-noviembre.md`, aprobado por Lucía Mora el 2026-10-23, vigente desde el 2026-11-01). Comprobación de la limpieza estándar de dos habitaciones y un baño:
- 23 de octubre de 2026: **$135.000 COP** (rige aún la tarifa de octubre, Documento 02; el cambio no empieza hasta el 1 de noviembre).
- 3 de noviembre de 2026: **$145.000 COP** (ya aplica el Documento 09).
- ¿Afecta al caso BH-S103? No. Ese caso es del 13 de octubre de 2026, anterior a la entrada en vigor de la actualización; su valor y cálculo se mantienen sin cambio. Se conserva la explicación original y el historial sin modificar.

## Elementos entregados
- Bóveda de Obsidian: `vault-brilla-hogar/` (notas del caso, cliente y regla, con fuentes, enlaces e historial).
- Este README breve.
- Video de 3–5 minutos: explicar el caso, mostrar fuentes y notas, y demostrar cómo Hermes recupera lo aprendido en una sesión nueva. Ruta del video en el repositorio: [`CASO_BH-S103.mov`](./CASO_BH-S103.mov) (duración 4:42).
