import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from efy import config, db, panel, seed
from efy.agent import AYUDA, Agente
from efy.texto import formatear_precio

CONVERSACION = [
    ("hola", "consulta"),
    ("busco algo como sauvage para hombre", "consulta"),
    ("3859", "eleccion"),
    ("si", "confirmacion"),
    ("quiero baccarat rouge", "sin coincidencia"),
    ("algo rico", "dato faltante"),
    ("floral para mujer", "consulta"),
    ("390", "eleccion"),
    ("si", "confirmacion"),
    ("unisex floral", "categoria limitada"),
]


def preparar(reiniciar):
    if reiniciar and config.DB_PATH.exists():
        config.DB_PATH.unlink()
    db.inicializar()
    total = seed.cargar()
    print(f"Catálogo cargado: {total} referencias · base {config.DB_PATH}")


def correr():
    agente = Agente()
    chat_id = f"demo-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    lineas = ["Conversación de demostración · bot EFY", "=" * 60, ""]
    for i, (texto, etiqueta) in enumerate(CONVERSACION, start=1):
        respuesta = agente.responder(chat_id, texto, f"msg-{i}")
        bloque = f"[{etiqueta}] Cliente: {texto}\nEFY: {respuesta}\n"
        print("-" * 60)
        print(bloque)
        lineas.append(bloque)
    return lineas


def main():
    parser = argparse.ArgumentParser(description="Demo del bot EFY sin Telegram")
    parser.add_argument("--reiniciar", action="store_true", help="borra la base y la vuelve a sembrar")
    args = parser.parse_args()

    preparar(args.reiniciar)
    lineas = correr()

    salida = config.RAIZ_ENTREGABLE / "evidencias" / "conversacion_demo.txt"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(lineas), encoding="utf-8")
    print("=" * 60)
    print(f"Transcripción guardada en {salida}")

    ruta_panel = panel.generar()
    print(f"Panel generado en {ruta_panel}")
    print(f"Precio base: {formatear_precio(config.PRECIO_DEFECTO)} · {config.ML_DEFECTO} ml")


if __name__ == "__main__":
    main()
