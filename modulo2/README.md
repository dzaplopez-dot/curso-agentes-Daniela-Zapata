# Módulo 2 — De conversaciones a datos útiles

**Participante:** Daniela Zapata López
**Skill:** `.opencode/skills/conversaciones-a-datos/SKILL.md`
**Ruta elegida:** A · Taskmaster-1 reservas (`restaurant-table-1 + 2`, muestra 200)

## Estructura

```
modulo2/
├── README.md (este archivo)
├── preguntas.md        # P1 demanda, P2 cierre, P3 fricción
├── esquema.md          # 1 fila = 1 reserva (conversation_id, restaurante, zona, fecha_hora, personas, seating, estado)
├── datos/
│   ├── original/self-dialogs.json  # original intacto 63 MB, 7708 convs (no modificar)
│   └── procesado/      # muestra.csv + datos.csv + pendientes.csv (generados)
├── scripts/
│   └── procesar.py     # filtra restaurant-table-1/2, muestra 200 seed 7, extrae con anotaciones
├── informe.md          # 3 respuestas + evidencia + límites + recomendación
└── dashboard/
    └── index.html      # dashboard estático
```

## Reproducir

```bash
python3 modulo2/scripts/procesar.py --n 200 --seed 7
```

## Lista de comprobación

- [x] Original conservado sin cambios
- [x] Skill con instrucciones completas
- [x] 100–300 conversaciones procesadas (200)
- [x] Salida CSV + pendientes separados
- [x] Cada registro conserva conversation_id
- [x] Conteos reconcilian (200 filas + 167 pendientes por campo)
- [x] 3 preguntas con respuesta verificable (informe.md)
- [x] Dashboard estático (dashboard/index.html)
