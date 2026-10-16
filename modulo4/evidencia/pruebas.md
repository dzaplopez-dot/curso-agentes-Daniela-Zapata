# Pruebas — Módulo 4 Ferricentro (extensión local 0.2.0)

Fecha: 2026-10-16 | Zona: America/Bogota | Equipo: Chrome + Edge (pendiente re-ejecución en navegador real para video)

## 1. Página compatible
- Pasos: `chrome://extensions` modo dev → Cargar descomprimida `extension/` → abrir `https://ferricentro.com/` → scroll a portafolio → clic Analizar.
- Esperado: conteo 20, previa 10 filas, avisos (regla activo, inventario vacío, 3 sin sku).
- Resultado base 2026-09-26: OK (productos_erp 20 filas). Re-verificar en video.

## 2. Página no compatible
- Pasos: abrir `https://example.com` o `https://listado.mercadolibre.com.co/...` → Analizar.
- Esperado: "Página no compatible. Abre https://ferricentro.com/. No se genera CSV."
- Estado: implementado en `popup.js` + `extractor.js` (UNSUPPORTED_URL). Pendiente captura.

## 3. Cero resultados
- Pasos: abrir home sin scroll (fuera de portafolio) → Analizar.
- Esperado: "Cero productos... Haz scroll... y reintenta." Sin CSV engañoso.
- Estado: implementado (ZERO_RESULTS). Pendiente captura.

## 4. Campo ausente
- Casos reales: 3 filas sin `sku_proveedor` (Cerradura Digital Manija, Cerrad Auxiliar..., Barra Antipánico...).
- Esperado: vacío + `requiere_revision` + fila en `excepciones.csv` tipo faltante.
- Resultado: OK en `salida/catalogo_proveedor.csv` (3 requiere_revision) y `excepciones.csv` (3 faltante).

## 5. Selectores cambiados
- Simulación: quitar `-ff-` del discriminador o cambiar `li` → debe caer a ZERO_RESULTS y detenerse.
- Prueba estática: discriminador probado contra 20 slugs reales vs `/productos/`, `/ofertas`, `/combos` → OK.
- Pendiente: captura con DOM modificado.

## 6. CSV correcto
- `catalogo_proveedor.csv`: 20 filas + cabecera 12 col, UTF-8 con BOM, coma, sin `;`, escape RFC-4180. Validar apertura en Excel/Sheets.
- `actualizacion_pos.csv`: solo cabecera, 0 filas (sin tabla validada → propuesta vacía, correcto).
- `excepciones.csv`: 25 filas (3 faltante + 20 sin_equivalencia + 2 avisos). UTF-8.
- Comando: `python3 -c "import csv; print(len(list(open('salida/catalogo_proveedor.csv'))))"` → 21 líneas.

## 7. Permisos
- `manifest.json`: `activeTab, scripting, downloads` + `host_permissions: https://ferricentro.com/*`. Sin `<all_urls>`, sin cookies, sin remote code.
- Solo actúa tras clic Analizar/Descargar. Verificado en código.

## 8. Chrome y Edge
- Instalación idéntica `chrome://extensions` y `edge://extensions`.
- Pendiente: tabla resultado Chrome vs Edge + diferencias (anotar en video).

## 9. Red y privacidad
- Sin fetch/XHR, sin telemetría, sin envío a terceros. Solo `chrome.downloads` local.
- No incluye credenciales/cookies/datos personales en CSV ni capturas.

## Registro para video
1. Mostrar manifest sin errores.
2. Analizar → conteo 20 → previa → avisos.
3. Descargar `catalogo_proveedor.csv` y `excepciones.csv`, abrirlos.
4. Mostrar `actualizacion_pos.csv` vacía y explicar: sin equivalencias no hay propuesta.
5. Demostrar límite: página no compatible o fila sin sku.
