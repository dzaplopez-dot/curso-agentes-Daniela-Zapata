#!/usr/bin/env python3
"""
Generador SIMPLE de video demostración para el Módulo 6.
Usa ffmpeg con comandos simples por slide (sin filtros complejos).
"""

import subprocess
import os
import sys
from datetime import datetime

VIDEO_DIR = "/Users/carcila/curso-agentes-Daniela-Zapata/entregable-modulo-06"
FFMPEG = "/Users/carcila/.hermes/tools/ffmpeg-9.0.1-darwin-x64/ffmpeg"
FONT = "/System/Library/Fonts/SFNS.ttf"
OUTPUT = os.path.join(VIDEO_DIR, "video-demostracion.mp4")
AUDIO = os.path.join(VIDEO_DIR, "narracion.aiff")

# Mensajes para cada slide (texto simple, sin caracteres especiales que rompan ffmpeg)
slides_text = [
    # Slide 0: Intro (5s)
    ("Modulo 6 - Agente Personal con Hermes", 5, [
        "Curso: Desarrollo Agéntico para Pymes",
        "Fundacion Cognitus"
    ]),
    # Slide 1: Config (8s)
    ("Configuracion del Sistema", 8, [
        "Modelo: poolside/laguna-s-2.1:free",
        "Proveedor: Nous Portal",
        "Telegram: @Hermes_daniela_bot",
        "User ID: 8877255183"
    ]),
    # Slide 2: Noticias (8s)
    ("Noticias Personalizadas", 8, [
        "Temas: Tecnologia e IA",
        "IA generativa y modelos de lenguaje",
        "Innovaciones: chips, computacion cuantica"
    ]),
    # Slide 3: Telegram (8s)
    ("Telegram Funciona", 8, [
        "Bot conectado correctamente",
        "Mensajes enviados a User ID 8877255183",
        "Verificado: recibido en Telegram"
    ]),
    # Slide 4: Cron (8s)
    ("Cron Jobs Programados", 8, [
        "0 8 * * * - Briefing de noticias",
        "0 9 * * * - Resumen de correos",
        "Zona horaria: Buenos Aires"
    ]),
    # Slide 5: GitHub (8s)
    ("Repositorio en GitHub", 8, [
        "dzaplopez-dot/curso-agentes",
        "Carpeta: entregable-modulo-06/",
        "Video: video-demostracion.mp4"
    ]),
]

def create_slides():
    """Crear un video con todos los slides concatenados usando textos simples."""
    print("🎨 Creando slides visuales...")
    
    slide_files = []
    total_duration = 0
    
    for i, (title, duration, lines) in enumerate(slides_text):
        slide_file = os.path.join(VIDEO_DIR, f"slide_{i}.mp4")
        
        # Usar drawtext con textos simples (escapar caracteres problemáticos)
        # Dividir los drawtext en un solo filtro separado
        vf_parts = []
        y = 120
        
        # Título principal
        vf_parts.append(
            f"drawtext=fontfile={FONT}:text='{title}':fontsize=36:fontcolor=white:x=(w-text_w)/2:y={y}"
        )
        y += 70
        
        # Líneas de contenido
        for line in lines:
            # Escapar caracteres especiales para ffmpeg
            safe_line = line.replace("'", "\\'").replace(":", "\\:")
            vf_parts.append(
                f"drawtext=fontfile={FONT}:text='{safe_line}':fontsize=22:fontcolor=0xcccccc:x=200:y={y}"
            )
            y += 40
        
        vf = ",".join(vf_parts)
        
        cmd = [
            FFMPEG, "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x1a1a2e:s=1280x720:d={duration}:rate=30",
            "-vf", vf,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            slide_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            slide_files.append(slide_file)
            total_duration += duration
            print(f"✅ Slide {i+1}: '{title}' ({duration}s)")
        else:
            # Debug: imprimir el error real
            error_lines = result.stderr.split('\n')
            for line in error_lines:
                if 'Error' in line or 'error' in line.lower():
                    print(f"❌ Slide {i+1} error: {line.strip()[:100]}")
            print(f"   Comando: {' '.join(cmd)[:200]}...")
    
    return slide_files, total_duration

def combine_with_audio(slide_files):
    """Concatenar slides y añadir audio."""
    print("\n🎬 Combinando slides con audio...")
    
    # Concatenar
    concat_list = os.path.join(VIDEO_DIR, "slides_list.txt")
    with open(concat_list, "w") as f:
        for slide in slide_files:
            f.write(f"file '{slide}'\n")
    
    combined = os.path.join(VIDEO_DIR, "video_combined.mp4")
    result = subprocess.run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", combined],
        capture_output=True, text=True, timeout=60
    )
    
    if result.returncode != 0:
        print(f"❌ Error concatenando: {result.stderr[:300]}")
        return False
    
    # Añadir audio
    result = subprocess.run(
        [FFMPEG, "-y", "-i", combined, "-i", AUDIO,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", OUTPUT],
        capture_output=True, text=True, timeout=60
    )
    
    # Limpiar
    for f in [combined, concat_list] + slide_files:
        if os.path.exists(f):
            os.remove(f)
    
    if result.returncode == 0:
        size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
        print(f"✅ Video final: {OUTPUT}")
        print(f"   Tamaño: {size_mb:.1f} MB")
        return True
    else:
        print(f"❌ Error con audio: {result.stderr[:300]}")
        return False

def main():
    print("🎥 Generando video demostración...")
    print("=" * 50)
    
    slide_files, total_duration = create_slides()
    
    if not slide_files:
        print("\n❌ No se pudieron crear los slides")
        return 1
    
    print(f"\n📊 Total: {len(slide_files)} slides, {total_duration}s")
    
    if combine_with_audio(slide_files):
        print("\n✅ Video demostración completado")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
