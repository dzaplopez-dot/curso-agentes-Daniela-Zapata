# Planeación · Bot de pedidos EFY

Proyecto final · Módulo 10 · Fundación Cognitus
Entrega y Demo Day: miércoles 2 de diciembre de 2026.

---

## 1. Problema y beneficio

**Usuario.** Cliente de EFY que escribe por redes sociales (hoy WhatsApp 314 684 9558 e
Instagram/Facebook `@efyperfumeria`) pidiendo un perfume "parecido a" una marca conocida, y
el asesor que responde a mano cada consulta.

**Necesidad.** El catálogo tiene 80 referencias identificadas por *inspirado en*, *familia
olfativa* y *casa*, pero el cliente no conoce esa estructura: recuerda marcas ("Sauvage",
"Chance", "212") y no códigos. El asesor repite las mismas búsquedas, transcribe pedidos y
no queda registro consultable de qué se vendió ni de qué stock queda.

**Cómo se resuelve hoy.** Conversación manual en WhatsApp, con el PDF del catálogo abierto.
El pedido se anota aparte y el stock se controla de memoria.

**Beneficio que se va a comprobar.**

1. El cliente obtiene opciones **reales** del catálogo (con código, familia, precio y stock)
   a partir de lo que recuerda, sin que nadie transcriba nada.
2. Menos preguntas repetidas al asesor para el mismo caso.
3. Todo pedido queda registrado y consultable en un panel, con stock descontado solo al
   confirmar.

**Indicador observable para la demo:** una consulta como "algo como Sauvage para hombre"
produce dos referencias válidas y un pedido confirmado, con el stock bajando de 10 a 9.

---

## 2. Diagrama de flujo

Archivo editable: `diagramas/flujo.mmd` · Imagen: `diagramas/flujo.png`

```
Cliente → ¿trae código? → no → interpretar preferencias
                                → ¿hay filtros? → no → preguntar género y familia
                                                → sí → buscar en catálogo
                       → resultados 0 + inspirado → ofrecer misma familia
                                     → sin alternativas → decir que no se maneja
                       → 1 resultado → borrador
                       → varios → listar y pedir código
        borrador → ¿confirma? → NO → cancelar sin descontar stock
                              → SÍ → descontar stock y guardar
                                   → resumen + panel
```

**Qué ocurre cuando falta un dato.** El agente no adivina: si no hay filtros pide género y
familia; si el término no existe en el catálogo lo dice y ofrece familias; si una referencia
no tiene familia olfativa cargada, no se clasifica a ojo y queda fuera de las búsquedas por
familia (documentado en `datos/revision_datos.md`).

---

## 3. Diagrama técnico

Archivo editable: `diagramas/arquitectura.mmd` · Imagen: `diagramas/arquitectura.png`

| Componente | Implementación | Qué información pasa |
|---|---|---|
| Canal | Telegram (python-telegram-bot) | texto del cliente + `message_id` |
| NLU | reglas en `nlu.py`; LLM opcional | texto → `{inspirado, casa, familia, genero, cantidad}` |
| Agente | `agent.py`, máquina de estados | filtros → herramienta → respuesta en español |
| Herramientas | `repository.py` | `buscar_perfume`, `ver_stock`, `crear_borrador`, `confirmar_pedido` |
| Datos | SQLite local o Supabase/Postgres con `EFY_BACKEND` | `perfumes`, `pedidos`, `sesiones` |
| Salida | `panel.py` → HTML estático | pedidos, stock bajo, familias y casas más pedidas |

**Qué interpreta la IA y qué ejecuta el código.** El modelo (o las reglas, si no hay API key)
solo traduce el mensaje a filtros. El precio, el stock y la existencia del código **siempre**
los resuelve la base de datos. El agente nunca afirma que un perfume está disponible sin
consultarlo.

---

## 4. Alcance y plan

**Lo que sí construye esta primera versión**

- Catálogo de 80 referencias cargado desde el PDF de 2024, normalizado a CSV.
- Búsqueda por `inspirado_en`, `casa`, `familia_base` y `genero`.
- Manejo de ambigüedad (Sauvage / Sauvage Elixir, Chance / Chance Eau Tendre, Light Blue
  femenino y masculino, 212).
- Borrador con confirmación explícita y descuento de stock transaccional.
- Idempotencia por `(chat_id, msg_id)` para no duplicar pedidos.
- Panel HTML con pedidos, stock bajo y ranking de familias y casas.
- 16 pruebas automatizadas (flujo del agente + capa de backend).

**Fuera de alcance (siguiente etapa)**

- Medios de pago y pasarela.
- WhatsApp (Telegram es el canal del ejercicio).
- Presentaciones distintas de 100 ml y precios distintos de $40.000.
- Notas olfativas y búsqueda semántica (el PDF no las trae).
- Nómina, facturación electrónica, envíos.

**Tareas y responsables**

| Tarea | Responsable |
|---|---|
| Extracción y normalización del catálogo | por asignar |
| Agente, herramientas y pruebas | por asignar |
| Panel y evidencias | por asignar |
| Guion del Demo Day | por asignar |

**Dudas por validar con mentores y con EFY**

1. `PRECICE TERNATIONAL` (ref. 764) y `JEAN PAUL GAUTIER`: ¿son errores del catálogo impreso?
2. ¿El stock real se maneja hoy? El ejercicio simula 10 unidades por referencia.
3. ¿Se usa Supabase para la entrega (panel en vivo y acceso por usuario) o se queda SQLite
   como respaldo de la demo?
4. ¿Se permite decir "inspirado en X" con el nombre de la marca original en el chat?

---

## 5. Qué cambió frente al primer plan y por qué

| Primer plan | Plan actual | Motivo |
|---|---|---|
| Precio por referencia y filtros por rango de precio | Precio único $40.000 en columna con default | El catálogo no trae precios; EFY confirmó un solo precio |
| Recomendar "la alternativa más barata" | Recomendar por familia olfativa en otra casa | Sin variación de precio, el eje útil es el perfil olfativo |
| Presentaciones variables (50/100 ml) | Solo 100 ml, pero `ml` queda como columna | No hay información de otras presentaciones; el esquema no se rompe cuando lleguen |
| Supabase como base obligatoria | Selector `EFY_BACKEND=sqlite|postgres` | Permite probar y demostrar sin credenciales; Supabase queda disponible con el mismo esquema y las mismas pruebas |
| LLM obligatorio para entender el mensaje | LLM opcional, reglas deterministas como respaldo | Las pruebas y la demo deben correr sin API key ni costo |
| "Igual al original" como argumento de venta | El bot dice "inspirado en" y no certifica similitud | Evita afirmaciones que EFY no puede respaldar |

---

## 6. Riesgos y reglas del agente

1. **No inventar referencias.** Si el término no existe, se responde que no se maneja.
2. **No confirmar disponibilidad sin consultar.** Toda consulta de stock pasa por la base.
3. **No descontar stock antes de la confirmación.** El borrador no toca inventario.
4. **No duplicar.** Un `msg_id` repetido devuelve el pedido existente.
5. **No prometer equivalencia con la marca original.** El catálogo vende inspirados.
6. **No clasificar por olfato.** Si falta `familia_olfativa`, la referencia queda pendiente.
