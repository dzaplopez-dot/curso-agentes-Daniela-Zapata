# Decisiones — Módulo 1 (10 casos Comercial La Esquina)

**Participante:** Daniela Zapata López
**Modelo utilizado (análisis de casos):** Muse Spark 1.3 Free OpenCode Zen
**Fecha:** 10 de septiembre de 2026
**Fuente:** `actividad-individual-10-casos-Daniela-Zapata-Lopez.xlsx`, hoja `Principal`

Detalle completo de justificación, riesgo y condición de cambio en el Excel, columnas E–G. Columna H trae la revisión personal de OpenCode.

## Resumen de rutas elegidas

| Caso | Área | Ruta elegida | Estado frente a OpenCode |
|------|------|--------------|---------------------------|
| P1 | Productos | Respuesta directa | Aceptado pleno |
| P2 | Productos | Agente limitado | Ajustado (precisar motivo: pedir precisión, no adjudicar) |
| I1 | Inventario | Regla | Ajustado (precisar: Stock < Stock mínimo propio, no "X fija") |
| I2 | Inventario | Flujo | Ajustado (completar: falta validar proveedor activo + aprobador) |
| V1 | Ventas | Respuesta directa | Ajustado (precisar: solo las 10 del extracto, máx. 5 líneas) |
| V2 | Ventas | Flujo | Ajustado (completar: necesita Ventas del día + Libro por Referencia) |
| R1 | Proveedores | Regla | Aceptado pleno (bloqueo estricto Estado != 'Activo') |
| R2 | Proveedores | Agente limitado | Ajustado (completar resguardos: solo activos, 3 criterios, sin pedido) |
| C1 | Clientes y contabilidad | No automatizar todavía | Ajustado (completar: triple bloqueo, no solo consentimiento) |
| C2 | Clientes y contabilidad | No automatizar todavía | Ajustado (precisar: más que ética, alteración contable sin soporte) |

**Balance:** 10/10 clasificaciones de ruta correctas. 2 aceptadas plenas (P1, R1). 8 ajustadas solo en motivo/precisión. 0 rechazadas.

## Explicación de lo aceptado, ajustado o rechazado

- **Aceptado (P1, R1):** la propuesta mínima basta y el motivo ya es correcto. P1 es solo formateo sin consultar otros archivos ni cambiar estado. R1 es filtro literal Estado == 'Activo' (PRV-001 'En revisión' queda fuera).
- **Ajustado (P2, I1, I2, V1, V2, R2, C1, C2):** se mantiene la ruta, se corrige o completa el motivo:
  - P2: no devolver un producto automáticamente ante Forte Mini vs Andino Pequeño vs Maestro Mediano; pedir precisión.
  - I1: comparar contra el Stock mínimo de cada uno de los 827 productos, sin sobrescribir masivamente.
  - I2: validar proveedor en Proveedores (Estado Activo) y exigir aprobación; no asumir que todo está en Inventario.
  - V1: no tocar el archivo de 12.631 transacciones; resumir solo las 10 entregadas.
  - V2: contrastar cada venta contra Libro por Referencia; prohibido alterar Libro para forzar diferencia cero (caso C2).
  - R2: aplicar primero R1, comparar solo por condiciones de pago, ciudad y medio preferido, explicar sin crear pedido.
  - C1: bloquear por falta de fuente autorizada + falta de confirmación + datos ficticios (238 incompletos + mostrador).
  - C2: bloquear borrar/modificar Libro sin soportes ni aprobación; la vía permitida es V2 (registrar coincidencia o enviar a revisión).
- **Rechazado:** ninguna ruta fue rechazada. Se rechazan explícitamente las alternativas riesgosas descritas en el Excel (ej. Regla con auto-ajuste en V2, completar desde internet en C1, borrar hasta cuadrar en C2, mostrar Precio costo/Margen en P1).
