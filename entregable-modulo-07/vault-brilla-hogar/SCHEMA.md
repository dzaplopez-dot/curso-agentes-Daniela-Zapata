# Esquema · Bóveda Brilla Hogar

## Estructura de notas
- notas/caso-*.md : explicación de un caso revisado (qué pasó, regla, error/excepción, fuentes, qué hacer).
- notas/cliente-*.md : ficha del cliente, preferencias y casos vinculados.
- notas/regla-*.md : regla de negocio aplicable con source_id, fecha de vigencia y owner.
- notas/acuerdo-*.md : acuerdos particulares de cliente (para contrastar con la regla general).
- fuentes/*.md : extractos de conversaciones y documentos recuperados con RAG, con citación de mensaje/documento.

## Campos mínimos de una nota de caso
1. ¿Qué pasó? (decisión, fecha, actores)
2. ¿Qué regla aplicaba? (documento, fecha de vigencia, acuerdo particular)
3. ¿Hubo error o excepción autorizada? (cálculo, quién aprobó)
4. ¿Qué mensajes y documentos respaldan la respuesta? (enlaces a fuentes)

## Convención de enlaces
Las notas se enlazan entre sí con enlaces relativos de Obsidian (`[texto](./ruta.md)`). Se conserva el historial en log.md y no se modifican los originales.
