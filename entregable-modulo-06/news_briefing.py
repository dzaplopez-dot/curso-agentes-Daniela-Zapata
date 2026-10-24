#!/usr/bin/env python3
"""
🤖 Agente de Noticias Personalizado para Hermes
Busca noticias sobre tecnología e IA y envía un resumen matutino a Telegram.
"""

import subprocess
import os
import sys
from datetime import datetime

def main():
    today = datetime.now().strftime("%d/%m/%Y")

    # Prompt para que Hermes busque noticias y formatee un briefing
    prompt = f"""
Buscá las últimas noticias (de hoy o de los últimos 2 días) sobre tecnología e inteligencia artificial. Incluí:
1. Noticias sobre IA generativa, modelos de lenguaje, o desarrollos de OpenAI, Google DeepMind, Anthropic o similares.
2. Innovaciones tecnológicas recientes (computación cuántica, chips, hardware, etc.).
3. Noticias locales de tecnología si aparecen.

Para cada noticia incluí:
- Título
- Fuente
- Enlace
- Una línea explicando por qué es relevante para quien sigue el rubro tech/IA

Generá un resumen breve con fechas, fuentes, enlaces y por qué son relevantes.
Formatealo como un mensaje de Telegram con emojis y separadores claros.
Usá español.
"""

    print(f"⏳ Buscando noticias de tecnología e IA para {today}...")

    try:
        # Usar hermes chat para buscar y resumir noticias
        result = subprocess.run(
            ["hermes", "chat", "-q", prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        briefing = result.stdout.strip()
    except Exception as e:
        print(f"❌ Error al buscar noticias: {e}")
        # Enviar mensaje de error a Telegram
        os.system(f'hermes send --to telegram "⚠️ Error al generar el briefing de noticias. Revisa la configuración del agente."')
        return

    if not briefing:
        print("❌ No se obtuvo respuesta del agente.")
        os.system(f'hermes send --to telegram "⚠️ No se pudieron obtener noticias hoy. Intenta más tarde."')
        return

    # Agregar encabezado personalizado
    header = f"📰 **Tu Brief de Noticias • {today}**\n"
    header += f"Temas: Tecnología e Inteligencia Artificial\n\n"

    full_message = header + briefing
    print("✅ Briefing generado:")
    print(full_message[:500] + "...")

    # Enviar a Telegram
    # Escapar caracteres para shell seguro
    safe_message = full_message.replace('"', '\\"')
    os.system(f'hermes send --to telegram "{safe_message}"')
    print("📤 Mensaje enviado a Telegram")

if __name__ == "__main__":
    main()
