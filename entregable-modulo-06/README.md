# Entregable - Módulo 6: Tu Agente Personal con Hermes

## Descripción

Este proyecto implementa un agente personal de Hermes que:
- ✅ Busca noticias sobre tecnología e inteligencia artificial cada mañana
- ✅ Envía un resumen personalizado a Telegram
- ✅ Conecta a Gmail usando Himalaya para revisar correos
- ✅ Programa tareas con cron para horarios automáticos

## Video de Demostración

📹 [Ver video demostración](https://github.com/dzaplopez-dot/curso-agentes-Daniela-Zapata/raw/main/entregable-modulo-06/video-demostracion.mp4)

El video muestra:
1. El agente en Hermes y su funcionamiento
2. El briefing de noticias enviado a Telegram
3. La conexión con Gmail vía Himalaya
4. Los cron jobs programados
5. El repositorio y estructura del proyecto

## Estructura del Proyecto

```
entregable-modulo-06/
├── README.md                          # Este archivo
├── news_final.py                      # Script de noticias personalizadas
├── email_summary.py                   # Script de resumen de correos
├── email_summary_gmail_api.py         # Alternativa con Gmail API
├── cron_jobs.json                     # Definición de tareas programadas
├── run_news_briefing.sh               # Script de ejecución
├── generate_video.py                  # Generador de video demo
├── narracion.aiff                     # Narración del video
└── video-demostracion.mp4             # Video demostración
```

## Configuración

### 1. Modelo de IA
- **Modelo**: `poolside/laguna-s-2.1:free` (gratuito)
- **Proveedor**: Nous Portal
- **Configuración**: `hermes config set model.default "poolside/laguna-s-2.1:free"`

### 2. Telegram
- **Bot**: `@Hermes_daniela_bot`
- **User ID autorizado**: `8877255183`
- **Token**: Configurado en `~/.hermes/.env`

### 3. Correo (Gmail via Himalaya)
- **Cliente**: Himalaya v2.2.1
- **Autenticación**: App Password
- **Configuración**: `~/.config/himalaya/config.toml`
- **Verificación**: `himalaya envelope list` ✅ (funcionando)

### 4. Horarios (Cron)
- **Noticias**: `0 8 * * *` → Briefing de noticias a las 8:00 AM
- **Correos**: `0 9 * * *` → Resumen de correos a las 9:00 AM
- **Zona horaria**: America/Argentina/Buenos_Aires

## Funcionamiento

### Noticias Personalizadas
El agente busca las últimas noticias sobre tecnología e IA usando web search y envía un resumen formateado a Telegram.

```bash
python3 news_final.py
```

### Resumen de Correos
El agente usa Himalaya para revisar Gmail y mostrar un resumen de correos.

```bash
himalaya -c ~/.config/himalaya/config.toml envelope list
```

### Programación con Cron
```bash
hermes cron list
```

## Seguridad

- ✅ **Solo lectura**: El agente no envía, borra ni modifica correos
- ✅ **Credenciales protegidas**: App Password almacenado en archivos con permisos `chmod 600`
- ✅ **No comparte tokens**: Todo está configurado en archivos locales
- ✅ **Telegram**: Solo recibe mensajes del User ID autorizado

## Límites del Agente

- **Correo**: Solo lectura - no envía ni modifica correos
- **Telegram**: Solo envía resúmenes al usuario autorizado
- **Gmail**: Conexión IMAP de solo lectura

---

**Curso**: Desarrollo Agéntico para Pymes - Fundación Cognitus  
**Módulo**: 06 - Tu agente personal con Hermes  
**Fecha**: Octubre 2026  
**Autor**: Daniela Zapata (dzaplopez@gmail.com)
