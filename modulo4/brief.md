# Brief — Módulo 4: Ferricentro → propuesta revisable POS

## 1. Fuente autorizada
- Proveedor: Ferricentro
- URL base: https://ferricentro.com/
- Páginas exactas: home `https://ferricentro.com/` y categorías `https://ferricentro.com/productos/...`
- Tipo: página pública, sin login. Solo lectura de pestaña abierta por la persona.

## 2. Acción permitida
- Clic explícito en "Analizar página actual" → inyectar `extractor.js` vía `chrome.scripting`.
- Leer texto visible: línea "MARCA CÓDIGO", título/enlace, bloque "Precio normal / Precio especial", URL slug.
- No hacer: login, comprar, añadir al carrito, enviar formularios, evadir CAPTCHA/bloqueos, escribir en ERP/POS, publicar en stores.

## 3. Campos de salida (12, UTF-8 coma RFC-4180)
`proveedor, sku_proveedor, nombre, marca, precio_cop, inventario, activo, fuente_url, fecha_consulta, estado_revision, sku_pos, disponibilidad`

Reglas:
- `sku_proveedor`: tal como aparece (ej. 10953/YMF). Vacío si no visible, jamás inventado.
- `precio_cop`: entero sin $ ni puntos. Precio especial si existe, si no último $ del bloque. Vacío si no verificable.
- `inventario`: siempre vacío (tarjeta no publica unidades; "Añadir al carrito" no prueba stock). Vacío ≠ cero.
- `activo`: `true` = publicado y visible (regla documentada y revisable).
- `fuente_url`: slug producto `https://ferricentro.com/<slug-ff-codigo>` deduplicada.
- `fecha_consulta`: `YYYY-MM-DDTHH:MM:SS-05:00` America/Bogota.
- `estado_revision`: `verificado` si tiene sku + precio, si no `requiere_revision`.
- `sku_pos`, `disponibilidad`: vacíos sin tabla validada. Sin coincidencia → excepciones.
- Precio proveedor no es precio de venta. Sin regla impuestos/margen no hay propuesta.

## 4. Condición de parada
- Detenerse y no generar CSV engañoso si: URL no es `ferricentro.com/*`, cero slugs `-ff-`, DOM ilegible, login/CAPTCHA/bloqueo.
- Página no compatible → mensaje visible, sin descarga.
- Cero resultados → estado vacío, pedir scroll a "Explora nuestro portafolio" y reintentar.
- Estructura inesperada → detenerse, registrar en excepciones.

## 5. Salidas
- `salida/catalogo_proveedor.csv`: 20 filas observadas 2026-09-26 (17 verificado, 3 requiere_revision).
- `salida/actualizacion_pos.csv`: vacía (0 propuestas) — sin tabla equivalencias SKU_POS validada ni regla precio aprobada.
- `salida/excepciones.csv`: 3 faltantes sku + 20 sin_equivalencia + 2 avisos generales.
