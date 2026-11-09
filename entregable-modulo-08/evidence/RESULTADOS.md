# Resultados · Módulo 8

Fecha de la evidencia: 2026-11-09.
Entorno: macOS, Python 3.14.7, dependencias fijadas por `uv.lock`.
Video: `video-demostracion-modulo-8.mp4` (1920x1200, H.264, 4:57).

## Comandos ejecutados

```bash
uv sync --locked
uv run python -m scripts.iniciar_datos
uv run python -m src.app
uv run pytest -q
node --check static/app.js
```

Resultado de `uv run pytest -q`: **49 pruebas aprobadas, 0 fallidas**.

| Archivo | Pruebas |
|---|---|
| `tests/test_base.py` | 22 |
| `tests/test_ejercicio1.py` | 5 |
| `tests/test_ejercicio2.py` | 10 |
| `tests/test_ejercicio3.py` | 12 |
| **Total** | **49** |

## Ejercicio 1 · Extracción y registro con revisión humana

- `test_extraer_soporte_exito_con_mock`: extrae con el cliente simulado.
- `test_extraer_soporte_clave_ausente`: informa la falta de clave sin inventar datos.
- `test_extraer_soporte_respuesta_incompleta`: no completa campos no observados.
- `test_registrar_comprobante_con_revision_humana`: exige la revisión antes de registrar.
- `test_registrar_comprobante_sin_revision_humana`: rechaza el registro sin revisión.

El prompt del modelo se conserva byte a byte (`test_original_prompt_is_preserved`) y el contrato de extracción se valida contra el esquema (`test_extraction_schema_contract`).

## Ejercicio 2 · Asociar comprobante con venta existente

Recorrido manual en navegador con el soporte `013` (DaviPlata, 26-08-2026, total observado 22.000):

1. Carga y reconocimiento del soporte; revisión y registro del comprobante.
2. Naturaleza `Cobro`, importe aplicado `22000`, búsqueda de candidatas.
3. Resultado: un candidato, `V-002` (total 22.000).
4. Preparar propuesta, aprobar en el servidor y ejecutar.
5. Vínculo comprobante-venta consultable y persistente.

Pruebas automatizadas: importe y naturaleza inválidos, comprobante sin revisión, ejecución sin aprobación, versión que no coincide, doble ejecución idempotente, consulta de vínculo y persistencia tras reiniciar.

Caso de dos candidatos (`022`, total 134.200): `V-003` y `V-004` comparten total y fecha; la selección de una venta es explícita.

## Ejercicio 3 · Crear venta faltante

Caso `054` (DaviPlata, 11-09-2026, total observado 148.000):

- Fecha comercial `2026-09-11`.
- Líneas: `FER-0001` x 1 (121.300) y `FER-0222` x 1 (26.700).
- Total calculado desde el catálogo: **148.000**.
- Se crea una única venta con sus dos líneas y su vínculo con el comprobante.
- El inventario no se modifica.

Pruebas automatizadas: borrador incompleto, precio de catálogo, precio confirmado explícito, producto inexistente, naturaleza distinta de cobro, versionado del borrador, ejecución sin aprobación, ejecución incompleta, flujo completo, doble confirmación sin duplicar, persistencia tras reiniciar y rutas GET de propuesta/vínculo sin 500.

## Falla controlada

- Ejecutar una propuesta sin aprobación: se rechaza y no se escriben ventas.
- Confirmar dos veces la misma operación: devuelve el resultado existente y no duplica la venta.
- Borrador incompleto (sin fecha o sin líneas): permanece `pendiente` y no se puede ejecutar.

## Límites conocidos

- Las pruebas automatizadas usan un cliente de modelo simulado; no sustituyen una prueba real del proveedor.
- La recepción bancaria del dinero no se verifica en esta entrega; los pagos quedan como `no_verificado`.
- La selección de venta entre dos candidatos es siempre humana.
