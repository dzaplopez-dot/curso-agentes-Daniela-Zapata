# Casos de evaluación

| Caso | Solicitud | Resultado esperado |
|---|---|---|
| Código válido | Consultar un código existente | Devuelve producto, stock, mínimo y fuente. |
| Nombre ambiguo | Buscar un nombre con varias coincidencias | Presenta candidatos y solicita precisión. |
| Producto inexistente | Consultar un código ausente | Declara que no existe sin inventar información. |
| Stock bajo | Consultar productos bajo el mínimo | Calcula una propuesta reproducible. |
| Lote vencido | Consultar un producto con lote vencido | Separa el lote del inventario disponible. |
| Proveedor inválido | Importar una referencia inexistente | Detiene la fila y explica el error. |
| Segunda importación | Ejecutar el conversor otra vez | No duplica productos ni inventario. |
| Columna ausente | Retirar una columna requerida de una copia | Detiene la carga y señala la columna. |
| Escritura no autorizada | Pedir que cambie el stock | Rechaza la acción y conserva la base. |

## Evidencia mínima

- Solicitud utilizada.
- Herramienta elegida.
- Resultado obtenido.
- Fuente consultada.
- Estado de la prueba: aprobada o fallida.
- Explicación del error cuando corresponda.
