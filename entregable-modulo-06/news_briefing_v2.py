#!/usr/bin/env python3
"""
🤖 Agente de Noticias Personalizado para Hermes
Busca noticias sobre tecnología e IA y envía un resumen matutino a Telegram.
"""

import subprocess
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime

# Configuración
BOT_TOKEN = "8808347101:AAHA6ITZ3_hyo9XSwDblqpfGoHen_THNXT8"
CHAT_ID = "8877255183"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_to_telegram(message):
    """Envía un mensaje a Telegram directamente."""
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(API_URL, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = response.read().decode()
            return True
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return False

def get_news_briefing():
    """Genera un briefing de noticias usando Hermes chat."""
    prompt = f"""
    Busca las últimas noticias sobre tecnología e inteligencia artificial de hoy. Incluye:
    1. Noticias sobre IA generativa, modelos de lenguaje, OpenAI, Google DeepMind, Anthropic.
    2. Innovaciones tecnológicas (chips, computación cuántica, hardware).
    
    Para cada noticia: título, fuente, enlace, breve explicación de relevancia.
    Formato: mensaje de Telegram con emojis. Usa español.
    """

    print("🔍 Buscando noticias sobre tecnología e IA...")
    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", prompt],
            capture_output=True,
            text=True,
            timeout=300,  # Aumentado a 5 minutos
            env={**os.environ}
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "❌ Error: La búsqueda tomó demasiado tiempo. Intenta más tarde."
    except Exception as e:
        return f"❌ Error: {e}"

def main():
    today = datetime.now().strftime("%d/%m/%Y")

    # Mensaje de encabezado
    header = f"📰 **Tu Brief de Noticias • {today}**\n"
    header += f"Temas: Tecnología e Inteligencia Artificial\n\n"

    # Obtener noticias
    briefing = get_news_briefing()
    full_message = header + briefing

    # Enviar a Telegram
    print("📤 Enviando a Telegram...")
    if send_to_telegram(full_message):
        print("✅ Mensaje enviado correctamente")
    else:
        print("❌ No se pudo enviar a Telegram")

    # También imprimir para logs
    print("\n--- Briefing generado ---")
    print(full_message[:500])

if __name__ == "__main__":
    main()
