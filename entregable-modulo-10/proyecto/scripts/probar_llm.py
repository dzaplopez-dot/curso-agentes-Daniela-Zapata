"""Prueba de una sola llamada al LLM para verificar la API key.

Uso:
    $env:LLM_API_KEY = "sk-..."
    python scripts/probar_llm.py
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from efy import config, db, repository, seed

MENSAJE = "busco algo como sauvage para hombre, dos unidades"


def main():
    if not config.LLM_API_KEY:
        raise SystemExit(
            "Falta LLM_API_KEY. Defínela en .env o con $env:LLM_API_KEY = 'sk-...'"
        )

    db.inicializar()
    seed.cargar()
    nombres = repository.nombres_conocidos()
    casas = repository.casas_conocidas()

    print(f"Modelo: {config.LLM_MODEL}")
    print(f"Endpoint: {config.LLM_BASE_URL}/chat/completions")
    print(f"Key: {config.LLM_API_KEY[:7]}...{config.LLM_API_KEY[-4:]}")
    print(f"Mensaje de prueba: {MENSAJE}\n")

    payload = {
        "model": config.LLM_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Devuelve SOLO un objeto JSON con las claves inspirado, casa, familia, "
                    "genero y cantidad. Usa null cuando no se deduzca. genero: F, M o U. "
                    "familia: FLORAL, MADEROSA, ORIENTAL, AROMATICA, CITRICA, CHIPRE o AMBARADA."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Perfumes disponibles: {', '.join(nombres[:80])}. "
                    f"Casas: {', '.join(casas[:60])}.\n\n{MENSAJE}"
                ),
            },
        ],
    }

    req = urllib.request.Request(
        f"{config.LLM_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.LLM_API_KEY}",
        },
        method="POST",
    )

    inicio = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        cuerpo = exc.read().decode("utf-8", errors="replace")[:600]
        print(f"ERROR HTTP {exc.code}")
        print(cuerpo)
        motivos = {
            401: "La key es inválida o fue revocada.",
            403: "La key no tiene permiso para este modelo.",
            404: "El modelo no existe; prueba otro en LLM_MODEL.",
            429: "Sin cuota o demasiadas solicitudes.",
        }
        print(motivos.get(exc.code, "Revisa el mensaje de arriba."))
        raise SystemExit(1)
    except urllib.error.URLError as exc:
        print(f"No hubo conexión: {exc.reason}")
        raise SystemExit(1)

    duracion = (time.time() - inicio) * 1000
    contenido = data["choices"][0]["message"]["content"]
    uso = data.get("usage", {})
    print(f"Respuesta ({duracion:.0f} ms):")
    print(contenido)
    print(
        f"\nTokens: {uso.get('prompt_tokens', '?')} entrada · "
        f"{uso.get('completion_tokens', '?')} salida"
    )
    print("Si ves un JSON con inspirado='SAUVAGE', genero='M' y cantidad=2, funciona.")


if __name__ == "__main__":
    main()
