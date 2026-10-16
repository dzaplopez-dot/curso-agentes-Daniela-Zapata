# Ferricentro ERP — extensión local Manifest V3 (Módulo 4 v0.2.0)

Lee catálogo visible de Ferricentro solo tras clic y exporta CSV revisables. Sin dependencias, sin telemetría, sin código remoto.

## Archivos
`manifest.json, popup.html, popup.css, popup.js, extractor.js`

## Instalación
1. `chrome://extensions` (o `edge://extensions`) → Modo desarrollador.
2. Cargar sin comprimir → `extension/`.
3. Abrir `https://ferricentro.com/`, scroll a portafolio.
4. Analizar → revisar previa/avisos → Descargar catálogo / excepciones.

## Permisos
`activeTab` (leer tras clic), `scripting` (inyectar extractor), `downloads` (guardar CSV), `host_permissions: https://ferricentro.com/*` solo dominio autorizado.

## Contrato (12 col)
`proveedor,sku_proveedor,nombre,marca,precio_cop,inventario,activo,fuente_url,fecha_consulta,estado_revision,sku_pos,disponibilidad`
- sku tal como aparece, vacío si no; precio especial o último $; inventario siempre vacío (vacío≠cero); activo true=visible; fecha Bogota -05:00; estado verificado/requiere_revision; sku_pos/disponibilidad vacíos sin tabla validada.

Salidas: `catalogo_proveedor.csv` (12 col), `excepciones.csv` (6 col). `actualizacion_pos.csv` se arma en revisión manual solo con equivalencias validadas (por eso la extensión no la inventa).
