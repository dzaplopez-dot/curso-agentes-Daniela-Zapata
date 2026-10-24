#!/bin/bash
# Script de grabación para video demostración del módulo 6

# Configuración
VIDEO_DIR="/Users/carcila/curso-agentes-Daniela-Zapata/entregable-modulo-06"
SCRIPT_DIR="$VIDEO_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VIDEO_FILE="$VIDEO_DIR/video-demostracion.mp4"

export PATH="$HOME/.local/bin:$PATH"

echo "🎬 Iniciando grabación del video demostración..."

# Crear archivo de notas para la demo
cat > "$VIDEO_DIR/demo_notes.txt" << 'EOF'
=== NOTAS PARA LA DEMO ===

1. Bienvenida del agente
2. Funcionamiento del script de noticias
3. Recepción en Telegram
4. Configuración de cron
5. Estructura del repositorio
EOF

# Iniciar grabación con ffmpeg
# Usando captura de pantalla completa
ffmpeg -y -f avfoundation -i "1:none" \
  -c:v libx264 -preset ultrafast -crf 18 \
  -c:a aac -b:a 128k \
  -t 120 \
  "$VIDEO_FILE" 2>&1 | while read -r line; do
    echo "$line"
    # Hacer pausa para permitir interacción
  done &
FFMPEG_PID=$!

echo "⏺️ Grabación iniciada (PID: $FFMPEG_PID)"
echo "📁 Video se guardará en: $VIDEO_FILE"
echo ""
echo "=== PASOS DE LA DEMO ==="
echo "1. Mostrando estructura del proyecto..."
ls -la "$VIDEO_DIR"
echo ""
echo "2. Mostrando configuración de Telegram..."
grep "TELEGRAM" ~/.hermes/.env | head -3
echo ""
echo "3. Mostrando modelo configurado..."
hermes config get model.default 2>/dev/null || echo "Modelo: poolside/laguna-s-2.1:free"
echo ""
echo "4. Mostrando configuración de cron..."
cat ~/.hermes/cron/jobs.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
for job_name in data:
    job = data[job_name]
    print(f'  📅 {job_name}: {job[\"schedule\"]} - {job[\"title\"]}')
" 2>/dev/null || cat "$VIDEO_DIR/../cron_jobs.txt" 2>/dev/null
echo ""
echo "5. Ejecutando script de noticias..."
python3 "$SCRIPT_DIR/news_briefing_v2.py" 2>&1
echo ""
echo "6. Mostrando script de correo..."
head -15 "$SCRIPT_DIR/email_summary.py"
echo ""
echo "7. Estructura final del repositorio..."
find "$VIDEO_DIR" -type f | head -20
echo ""
echo "✅ Demo completada"

# Detener grabación
sleep 2
kill $FFMPEG_PID 2>/dev/null
wait $FFMPEG_PID 2>/dev/null

echo ""
echo "🎥 Video grabado en: $VIDEO_FILE"
