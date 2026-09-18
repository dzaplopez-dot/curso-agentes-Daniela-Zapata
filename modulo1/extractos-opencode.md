# Extractos de OpenCode — Módulo 1

**Participante:** Daniela Zapata López
**Modelo de análisis de los 10 casos (registrado en el Excel):** Muse Spark 1.3 Free OpenCode Zen
**Fecha análisis de casos:** 10 de septiembre de 2026
**Modelo de apoyo para el repositorio (esta sesión):** muse-spark-1.3-contributor-free
**Fecha paquete en repo:** 18 de septiembre de 2026

## Dónde está la evidencia principal

La evidencia completa del análisis caso por caso está dentro del Excel:

`modulo1/actividad-individual-10-casos-Daniela-Zapata-Lopez.xlsx`

- Hoja `Principal`, columnas D–I: ruta elegida, justificación, riesgo, condición de cambio, revisión personal de OpenCode y referencia a evidencia.
- Hoja `Casos`: necesidad completa y contexto de cada caso (P1, P2, I1, I2, V1, V2, R1, R2, C1, C2).
- El archivo pesa ~14 MB porque contiene las capturas/extractos incrustados.

## Prompt base usado para cada uno de los 10 casos

> Estoy realizando de forma individual la primera actividad del Módulo 1. Ayúdame a evaluar la ruta mínima para un caso de Comercial La Esquina. Trabaja en Plan y limita tu intervención al análisis en esta conversación.
>
> Caso: [código]. Necesidad: [texto del Excel]. Contexto: [texto del Excel]. Mi clasificación provisional y motivo: [mi propuesta].
>
> Compara respuesta directa, regla, flujo, agente limitado y no automatizar todavía. Identifica información disponible, fuentes necesarias y cambios de estado. Si falta un dato, indícalo sin inventar. Propón una ruta, cuestiona mi propuesta e indica una alternativa, el riesgo principal y una condición concreta para cambiar de ruta.
>
> No construyas la aplicación, no modifiques archivos ni ejecutes las acciones descritas.

Se aplicó igual a P1, P2, I1, I2, V1, V2, R1, R2, C1, C2, cambiando solo `[código]`, `[texto del Excel]` y `[mi propuesta]`. Las respuestas caso por caso quedaron registradas en el Excel, hoja `Principal` columnas E–H, con capturas incrustadas.

## Extractos de la sesión de apoyo con OpenCode (repo)

**1. Prompt:** "Necesito crear esta estructura del proyecto curso agentes..."
**Respuesta aceptada:** creación de `modulo1/`, `modulo2/`, `modulo3/` con sus `README.md` y `README.md` raíz con el árbol del proyecto.

**2. Prompt:** `git commit -m "Crear estructura inicial del curso" / git push origin main`
**Respuesta aceptada:** `git add` selectivo + `commit b1273fd` + `push origin main` exitoso (`1394348..b1273fd main -> main`).

**3. Prompt:** "necesito compartir el repo con Pablo: pablo@cognitus.org / William: desarrollo@sdl.com.co"
**Respuesta ajustada:** no había sesión en `gh`, así que se entregó la guía manual (`settings/access → Add people`) + comandos `gh api .../invitations -f email=...` para ejecutar tras `gh auth login`. Pendiente de login del usuario para ejecutar las invitaciones.

**4. Prompt:** "debo entregar esto: EN TU REPOSITORIO Paquete de entrega... ya tengo el excel completo"
**Respuesta aceptada:** localización del Excel completo en `~/Downloads/actividad_individual_10_casos-2.xlsx` (14 MB, con nombre Daniela Zapata López) y copia a `modulo1/` con nombre final + creación de este archivo y `decisiones.md`.

## Capturas

- Las capturas del análisis de los 10 casos están incrustadas en el Excel.
- Si se piden archivos sueltos adicionales, guardarlos en `modulo1/capturas/`.
