# Revisión del catálogo EFY (PDF 2024)

Fuente: `Listado de EFY terminado para imprimir 2024.pdf` (escaneado, 6 páginas).
Extracción: render a PNG 300 dpi + lectura visual (el PDF no tiene capa de texto).
Salida: `datos/catalogo.csv`.

## Totales

| Métrica | Valor |
|---|---|
| Referencias | 80 |
| Códigos únicos | 80 (sin duplicados) |
| Femeninas | 37 |
| Masculinas | 40 |
| Unisex | 3 |
| Casas distintas | 40 |
| Familias (texto impreso) | 32 variantes |
| Familias (base normalizada) | 7 |

Distribución por familia base: FLORAL 29 · MADEROSA 19 · ORIENTAL 15 · AROMATICA 11 ·
CHIPRE 2 · CITRICA 2 · AMBARADA 2.

## Campos ausentes en el catálogo

- **Precio**: no aparece. Se asume $40.000 en `precio` (default de columna).
- **Presentación**: no aparece. Se asume 100 ml.
- **Stock**: no existe. Se siembra con 10 unidades editables.
- **Notas olfativas**: no existen → no se puede hacer búsqueda semántica todavía.
- **Fotos**: el PDF solo trae tabla, sin imágenes de producto.

## Inconsistencias de escritura (familia olfativa)

Se conserva el texto original en `familia_raw` y se agrega `familia_base` para filtrar.
Corregir en origen cuando se digitalice:

| Variantes encontradas | Familia correcta |
|---|---|
| `MADEROSA`, `MADEROSO`, `AMADERADO` | Madera / Amaderada |
| `FOUGERE`, `FOUGÉRE` | Fougère |
| `AROMÁTICA`, `AROMATICA` | Aromática |
| `FLORAL-MADEROSA`, `FLORAL MADEROSA` | Floral amaderada |
| `CÍTRICA`, `CÍTRICO` | Cítrica |

## Inconsistencias de CASA

| Como aparece | Acción |
|---|---|
| `VICTORIA"S SECRET` (comilla recta) | Normalizado a `VICTORIA'S SECRET` |
| `ARMANI` y `GIORGIO ARMANI` | Misma casa con dos nombres → unificar |
| `PRECICE TERNATIONAL` (ref. 764 SWISS ARMY) | DudosO; probablemente `PRESTIGE INTERNATIONAL`. **No corregido sin confirmar.** |
| `JEAN PAUL GAUTIER` | La marca real es `GAULTIER`. **No corregido sin confirmar.** |

## Ambigüedades reales útiles para las pruebas

Estas no son errores: son casos donde el bot **debe preguntar** en vez de adivinar.

| Consulta del cliente | Referencias candidatas |
|---|---|
| "Sauvage" | 3859 SAUVAGE · 2069 SAUVAGE ELIXIR POUR |
| "Chance" | 893 CHANCE · 3647 CHANCE EAU TENDRE |
| "Light Blue" | 757 LIGHT BLUE (F) · 1962 LIGHT BLUE MEN (M) |
| "212" | 2206 · 2134 · 3603 · 2940 |
| "Diesel Zero Plus" | 1823 (F) · 1835 (M) |
| "Amber Oud" | 1841 AMBER OUD GD UNISEX · 2097 AMBER OUD ROUGE |

## Observaciones

1. La tabla de **Unisex está prácticamente vacía** (3 filas y 6 renglones en blanco en el PDF).
   El bot necesita un plan para consultas unisex: caer a familia olfativa y avisar que el
   catálogo unisex es limitado.
2. No hay marca "EFY" propia en el nombre: el cliente reconoce el perfume por `inspirado_en`
   y `casa`, no por un nombre comercial. La búsqueda debe priorizar esos dos campos.
3. `2759 DOLCE & GABBANA` usa la casa como nombre del perfume (misma cadena). No es error,
   pero la búsqueda por `casa` devolverá coincidencias de nombre y de marca.
4. Los códigos tienen 3 y 4 dígitos; deben tratarse como **texto** para no perder el cero
   a la izquierda si algún día aparece.
