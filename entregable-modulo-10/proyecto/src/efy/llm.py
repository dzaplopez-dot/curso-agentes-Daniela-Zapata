import json
import urllib.error
import urllib.request

from . import config

SISTEMA = (
    "Eres el intérprete de un bot de perfumería. Devuelve SOLO un objeto JSON con las claves "
    "inspirado, casa, familia, genero y cantidad. Usa null cuando no se pueda deducir con certeza. "
    "genero debe ser 'F', 'M' o 'U'. familia debe ser una de: FLORAL, MADEROSA, ORIENTAL, "
    "AROMATICA, CITRICA, CHIPRE, AMBARADA. No inventes marcas ni perfumes que no estén en el texto."
)


def _peticion(payload):
    req = urllib.request.Request(
        f"{config.LLM_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.LLM_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extraer(texto, nombres=(), casas=()):
    if not config.LLM_API_KEY:
        return None
    contexto = (
        f"Perfumes inspirados disponibles: {', '.join(nombres[:80])}. "
        f"Casas disponibles: {', '.join(casas[:60])}."
    )
    payload = {
        "model": config.LLM_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": f"{contexto}\n\nMensaje del cliente: {texto}"},
        ],
    }
    try:
        data = _peticion(payload)
        contenido = data["choices"][0]["message"]["content"]
        salida = json.loads(contenido)
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError, OSError):
        return None
    if not isinstance(salida, dict):
        return None
    return {
        "inspirado": salida.get("inspirado") or None,
        "casa": salida.get("casa") or None,
        "familia": (salida.get("familia") or None),
        "genero": (salida.get("genero") or None),
        "cantidad": salida.get("cantidad") or None,
    }
