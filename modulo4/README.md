# Módulo 4 — Del catálogo del proveedor al ERP/POS (Ferricentro)

Extensión local Manifest V3 que lee el catálogo visible de Ferricentro y prepara propuesta revisable para ERP/POS. No compra, no modifica el proveedor, no publica en tiendas, no inventa stock.

## Estructura

```
entregable-modulo-04/
├── extension/ (manifest.json, popup.html/css/js, extractor.js)
├── evidencia/ (proceso-extension-proveedor.txt, pruebas.md, video-demo.txt)
├── salida/ (catalogo_proveedor.csv, actualizacion_pos.csv, excepciones.csv)
├── brief.md
└── README.md
```

Fuente: https://ferricentro.com/ (pública, sin login). Ver `brief.md`.

## Instalación (local, sin tienda)

1. `chrome://extensions` o `edge://extensions` → Modo desarrollador.
2. Cargar descomprimida → `extension/`.
3. Abrir `https://ferricentro.com/` (o `/productos/...`), scroll a "Explora nuestro portafolio".
4. Clic icono → Analizar → revisar conteo/previa/avisos → Descargar catálogo / Descargar excepciones.

Demo base 2026-09-26: 20 productos (ej. YALE 10953/YMF $2.161.250).

## Permisos (mínimos)

| Permiso | Uso |
|---|---|
| `activeTab` | Leer pestaña solo tras clic Analizar |
| `scripting` | Inyectar `extractor.js` tras ese clic |
| `downloads` | Guardar CSV tras clic Descargar |
| `host_permissions: https://ferricentro.com/*` | Solo dominio autorizado, sin `<all_urls>` |

Sin red externa, sin cookies, sin telemetría, sin código remoto.

## Contrato datos (12 col, UTF-8 con BOM, coma RFC-4180)

`proveedor,sku_proveedor,nombre,marca,precio_cop,inventario,activo,fuente_url,fecha_consulta,estado_revision,sku_pos,disponibilidad`

- `sku_proveedor` tal como aparece, vacío si no visible.
- `precio_cop` entero sin $: especial si existe, si no último $. Vacío si no verificable.
- `inventario` siempre vacío (tarjeta no publica unidades; vacío ≠ cero).
- `activo=true` = publicado y visible (regla revisable).
- `fecha_consulta` America/Bogota `-05:00`.
- `estado_revision`: verificado (17) / requiere_revision (3 sin sku).
- `sku_pos, disponibilidad` vacíos sin tabla validada → a excepciones.
- Precio proveedor ≠ precio venta. Sin regla impuestos/margen no hay propuesta.

## Salidas (revisadas 2026-09-26)

- `salida/catalogo_proveedor.csv`: 20 filas (17 verificado, 3 requiere_revision).
- `salida/actualizacion_pos.csv`: vacía (0 filas) — sin equivalencias SKU_POS validadas ni regla precio aprobada. Correcto no inventar.
- `salida/excepciones.csv`: 25 filas (3 faltante sku + 20 sin_equivalencia + 2 avisos inventario/precio).

## Pruebas y límites

Ver `evidencia/pruebas.md`. Cubre: compatible, no compatible (sin CSV engañoso), cero resultados, campo ausente, selectores cambiados, CSV, permisos, Chrome y Edge, red/privacidad. No escribe en ERP/POS.

## Video

Ver `evidencia/video-demo.txt`. PENDIENTE: pegar enlace Loom público. Sin video no está "Terminado" según lista final.

## Privacidad

Solo datos visibles. Sin credenciales, cookies, datos personales, sesiones privadas.
