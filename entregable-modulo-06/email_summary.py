#!/usr/bin/env python3
"""
📧 Resumen de Correos Importantes
Usa Himalaya para leer tu Gmail y enviar un resumen a Telegram.
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta

def main():
    today = datetime.now().strftime("%d/%m/%Y")

    print(f"⏳ Buscando correos importantes para {today}...")

    try:
        # Usar Himalaya para listar correos no leídos de las últimas 24 horas
        result = subprocess.run(
            ["himalaya", "-o", "json", "--unread", "--limit", "20"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"❌ Error de Himalaya: {result.stderr}")
            os.system(f'hermes send --to telegram "⚠️ Error al conectar con Gmail. Verifica la configuración de Himalaya."')
            return

        emails = []
        try:
            data = json.loads(result.stdout)
            emails = data if isinstance(data, list) else data.get("messages", [])
        except json.JSONDecodeError:
            emails = []

    except FileNotFoundError:
        print("❌ Himalaya no está instalado")
        os.system(f'hermes send --to telegram "⚠️ Himalaya no está instalado. Configura la conexión de correo."')
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        os.system(f'hermes send --to telegram "⚠️ Error al procesar correos. Intenta más tarde."')
        return

    # Filtrar correos de las últimas 24 horas y no leídos
    recent_unread = [e for e in emails if not e.get("read", False)]

    if not recent_unread:
        message = f"📭 **Resumen de Correos • {today}**\n\nNo tenés correos no leídos pendientes. ¡Todo está al día! ✅"
        os.system(f'hermes send --to telegram "{message}"')
        print("✅ No hay correos no leídos")
        return

    # Construir el resumen
    summary = f"📭 **Resumen de Correos • {today}**\n\n"
    summary += f"Tenés **{len(recent_unread)} correo(s) no leído(s)** de las últimas 24 horas:\n\n"

    for i, email in enumerate(recent_unread[:10], 1):
        subject = email.get("subject", "(sin asunto)")[:80]
        sender = email.get("from", "Desconocido")
        date = email.get("date", "fecha desconocida")

        # Extraer nombre del remitente
        if "<" in sender:
            sender_name = sender.split("<")[0].strip()
        else:
            sender_name = sender

        summary += f"{i}. **{subject}**\n"
        summary += f"   👤 {sender_name}\n"
        summary += f"   📅 {date}\n\n"

    summary += "\n_Puedes conversar con tu agente sobre estos correos o pedirle que prepare borradores._"

    print("✅ Resumen generado")
    safe_message = summary.replace('"', '\\"')
    os.system(f'hermes send --to telegram "{safe_message}"')
    print("📤 Resumen enviado a Telegram")

if __name__ == "__main__":
    main()
