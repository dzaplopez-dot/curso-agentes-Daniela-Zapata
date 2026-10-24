#!/usr/bin/env python3
"""
📧 Resumen de Correos Importantes (Versión Gmail API)
Lee correos de Gmail usando la API y envía un resumen a Telegram.
"""

import os
import sys
import json
import base64
import subprocess
from datetime import datetime, timedelta
from email.mime.text import MIMText

# Configuración de Telegram
BOT_TOKEN = "8808347101:AAHA6ITZ3_hyo9XSwDblqpfGoHen_THNXT8"
CHAT_ID = "8877255183"

def send_to_telegram(message):
    """Envía un mensaje a Telegram directamente."""
    import urllib.request
    import urllib.parse
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }).encode()
    
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return True
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return False

def get_gmail_credentials():
    """Obtiene credenciales OAuth para Gmail."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None
    
    # Verificar si existe token
    token_path = os.path.expanduser("~/.config/hermes/gmail_token.json")
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # Si no hay credenciales válidas, hacer login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets_path = os.path.expanduser("~/.config/hermes/gmail_credentials.json")
            if not os.path.exists(client_secrets_path):
                print("❌ No se encuentran credenciales OAuth. Configura primero.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardar token
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def get_unread_emails():
    """Obtiene los últimos 20 correos no leídos de Gmail."""
    try:
        from googleapiclient.discovery import build
        
        creds = get_gmail_credentials()
        if not creds:
            return []
        
        service = build('gmail', 'v1', credentials=creds)
        
        # Buscar correos no leídos
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=10  # Máximo 10 para mantenerlo breve
        ).execute()
        
        messages = results.get('messages', [])
        
        emails = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = msg_data.get('payload', {}).get('headers', [])
            email_info = {}
            for header in headers:
                if header['name'] == 'From':
                    email_info['from'] = header['value']
                elif header['name'] == 'Subject':
                    email_info['subject'] = header['value']
                elif header['name'] == 'Date':
                    email_info['date'] = header['value']
            
            email_info['id'] = msg['id']
            emails.append(email_info)
        
        return emails
        
    except Exception as e:
        print(f"❌ Error obteniendo correos: {e}")
        return []

def main():
    today = datetime.now().strftime("%d/%m/%Y")
    print(f"📧 Buscando correos no leídos para {today}...")
    
    emails = get_unread_emails()
    
    if not emails:
        message = f"📭 **Resumen de Correos • {today}**\n\nNo tenés correos no leídos pendientes. ¡Todo está al día! ✅"
        send_to_telegram(message)
        print("✅ No hay correos no leídos")
        return
    
    # Construir resumen
    summary = f"📭 **Resumen de Correos • {today}**\n\n"
    summary += f"Tenés **{len(emails)} correo(s) no leído(s)**:\n\n"
    
    for i, email in enumerate(emails[:5], 1):
        subject = email.get('subject', '(sin asunto)')[:80]
        sender = email.get('from', 'Desconocido')[:50]
        date = email.get('date', 'fecha desconocida')
        
        summary += f"{i}. **{subject}**\n"
        summary += f"   👤 {sender}\n"
        summary += f"   📅 {date}\n\n"
    
    summary += "\n_Puedes conversar con tu agente sobre estos correos._"
    
    send_to_telegram(summary)
    print("✅ Resumen enviado a Telegram")

if __name__ == "__main__":
    main()
