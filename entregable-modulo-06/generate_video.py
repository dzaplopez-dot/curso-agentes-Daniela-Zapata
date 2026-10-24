#!/usr/bin/env python3
"""
Generador de video para modulo 6 - ESPAÑOL, mostrando flujo REAL
"""

import subprocess
import os
import sys
from datetime import datetime

VIDEO_DIR = "/Users/carcila/curso-agentes-Daniela-Zapata/entregable-modulo-06"
FFMPEG = "/Users/carcila/.hermes/tools/ffmpeg-9.0.1-darwin-x64/ffmpeg"
FONT = "/System/Library/Fonts/SFNS.ttf"
OUTPUT = os.path.join(VIDEO_DIR, "video-demostracion.mp4")
AUDIO = os.path.join(VIDEO_DIR, "narracion_es.aiff")

# Narración en español
NARRACION_ES = """
Hola! En este video voy a mostrarte mi agente personal con Hermes. Soy Daniela Zapata y esta es mi entrega del modulo 6 del curso de agentes de Cognitus.

Comencemos con la configuracion. Estoy usando el modelo poole laguna s dos punto uno free, gratuito a traves del portal de Nous Research. Mi bot de Telegram es Hermes underscore daniela bot y funciona correctamente.

El primer componente es el briefing de noticias. Cada mañana busco noticias sobre tecnologia e inteligencia artificial. Aqui tienes las noticias de hoy.

Recibo noticias sobre GPT-5, chips de Google, alianza de NVIDIA y Microsoft, Claude de Anthropic, y el centro de IA de Meta en Madrid. Cada noticia con su fuente y enlace.

El segundo componente conecta Gmail usando Himalaya. Puede leer correos pero nunca envia ni borra. Usa App Password.

Mis tareas estan programadas con cron: a las 8 recibo noticias y a las 9 resumen de correos. Zona horaria Buenos Aires.

Todo el codigo esta en GitHub en la carpeta entregable menos modulo 6.

Este es mi agente personal con Hermes. ¡Gracias!
"""

slides = [
    ("Modulo 6 - Agente Hermes", 4, [
        "Curso: Desarrollo Agentico Pymes",
        "Fundacion Cognitus",
        "Por: Daniela Zapata"
    ]),
    ("Modelo de IA Gratuito", 4, [
        "Modelo: poole/laguna-s-2.1:free",
        "Proveedor: Nous Portal"
    ]),
    ("Telegram Conectado", 4, [
        "Bot: @Hermes_daniela_bot",
        "ID: 8877255183"
    ]),
    ("Briefing de Noticias", 6, [
        "1. OpenAI - GPT-5",
        "2. Google - Chips TPU v5p",
        "3. NVIDIA + Microsoft",
        "4. Anthropic - Claude 4",
        "5. Meta - IA Madrid"
    ]),
    ("Gmail via Himalaya", 5, [
        "Himalaya v2.2.1",
        "App Password",
        "IMAP - Solo lectura"
    ]),
    ("Cron Jobs Programados", 5, [
        "8:00 AM - Noticias",
        "9:00 AM - Correos",
        "Buenos Aires UTC-3"
    ]),
    ("Codigo en GitHub", 5, [
        "dzaplopez-dot/curso-agentes",
        "carpeta: entregable-modulo-06",
        "video-demostracion.mp4"
    ]),
    ("¡Gracias!", 3, [
        "Modulo 6 completado",
        "Octubre 2026"
    ]),
]

def generate_audio():
    print("Generando narracion en español...")
    if os.path.exists(AUDIO):
        os.remove(AUDIO)
    subprocess.run(["say", "-v", "Monica", NARRACION_ES, "-r", "180", "-o", AUDIO], check=True)
    print(f"Audio creado: {AUDIO}")
    return os.path.exists(AUDIO)

def create_slides():
    print("Creando slides...")
    slide_files = []
    total_dur = 0
    for i, (title, duration, lines) in enumerate(slides):
        slide_file = os.path.join(VIDEO_DIR, f"slide_{i}.mp4")
        vf_parts = []
        y = 120
        safe_title = title.replace("'", "\\'")
        vf_parts.append(f"drawtext=fontfile={FONT}:text='{safe_title}':fontsize=40:fontcolor=white:x=(w-text_w)/2:y={y}")
        y += 70
        for line in lines:
            safe_line = line.replace("'", "\\'").replace(":", "\\:")
            vf_parts.append(f"drawtext=fontfile={FONT}:text='{safe_line}':fontsize=24:fontcolor=0xcccccc:x=250:y={y}")
            y += 36
        vf = ",".join(vf_parts)
        cmd = [FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=0x1a1a2e:s=1280x720:d={duration}:rate=30",
               "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", slide_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            slide_files.append(slide_file)
            total_dur += duration
            print(f"  Slide {i+1}: {title}")
        else:
            print(f"  Error slide {i+1}: {result.stderr[:150]}")
    return slide_files, total_dur

def combine_with_audio(slide_files):
    print("Combinando slides + audio...")
    concat_list = os.path.join(VIDEO_DIR, "slides_list.txt")
    with open(concat_list, "w") as f:
        for s in slide_files:
            f.write(f"file '{s}'\n")
    combined = os.path.join(VIDEO_DIR, "video_combined.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", combined],
                   capture_output=True, text=True, timeout=60)
    result = subprocess.run([FFMPEG, "-y", "-i", combined, "-i", AUDIO,
                             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", OUTPUT],
                            capture_output=True, text=True, timeout=60)
    for f in [combined, concat_list] + slide_files:
        if os.path.exists(f):
            os.remove(f)
    if result.returncode == 0:
        size = os.path.getsize(OUTPUT) / (1024*1024)
        print(f"Video: {OUTPUT} - {size:.1f} MB")
        return True
    print(f"Error: {result.stderr[:200]}")
    return False

def main():
    print("Generando video ESPAÑOL...")
    if not generate_audio():
        print("ERROR: audio")
        return 1
    slide_files, total_dur = create_slides()
    if not slide_files:
        return 1
    print(f"Total: {len(slide_files)} slides, {total_dur}s")
    if combine_with_audio(slide_files):
        print("COMPLETADO")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
