"""Cliente backend para OpenAI Responses API. Solo se usa al implementar el ejercicio 1.
Lee configuración privada (.env) únicamente en el backend. Nunca revela la clave.
"""
from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Cargar configuración privada solo en el backend. No se lee ni se revela la clave aquí.
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_OCR_MODEL = os.getenv("OPENAI_OCR_MODEL", "gpt-5.6-luna")

RESPONSES_URL = "https://api.openai.com/v1/responses"


class OCRClientError(Exception):
    """Error controlado del cliente de reconocimiento."""

    def __init__(self, mensaje: str, codigo_http: int | None = None, reintentable: bool = False):
        super().__init__(mensaje)
        self.codigo_http = codigo_http
        self.reintentable = reintentable


def _quitar_additional_properties_anidados(nodo: dict[str, Any]) -> dict[str, Any]:
    """Elimina additionalProperties: false de objetos anidados para compatibilidad con json_schema de OpenAI."""
    resultado = dict(nodo)
    if resultado.get("type") == "object" and "properties" in resultado:
        props = {}
        for clave, valor in resultado["properties"].items():
            if isinstance(valor, dict):
                props[clave] = _quitar_additional_properties_anidados(valor)
            else:
                props[clave] = valor
        resultado["properties"] = props
        resultado.pop("additionalProperties", None)
    return resultado


def adaptar_schema_para_api(schema: dict[str, Any]) -> dict[str, Any]:
    """Devuelve el esquema para la API vigente sin perder campos ni reglas.

    OpenAI Responses API con json_schema strict no admite additionalProperties: false
    en objetos anidados profundos ni ciertas uniones de tipos. Se adapta el esquema
    eliminando restricciones que la API rechaza, conservando todos los campos y reglas
    semánticas.
    """
    adaptado = copy.deepcopy(schema)
    adaptado = _quitar_additional_properties_anidados(adaptado)
    return adaptado


def _extraer_texto_salida(datos: dict[str, Any]) -> str:
    """Extrae el texto de salida de la respuesta de Responses API probando varios caminos."""
    salida = datos.get("output", [])
    if isinstance(salida, list):
        for elemento in salida:
            if not isinstance(elemento, dict):
                continue
            if elemento.get("type") == "message":
                for contenido in elemento.get("content", []):
                    if isinstance(contenido, dict) and contenido.get("type") == "output_text":
                        texto = contenido.get("text")
                        if texto:
                            return texto
            if isinstance(elemento.get("content"), str) and elemento["content"]:
                return elemento["content"]
    if isinstance(datos.get("output_text"), str) and datos["output_text"]:
        return datos["output_text"]
    return ""


def extraer_con_openai(
    path_imagen: str | Path,
    prompt: str,
    schema: dict[str, Any],
    max_reintentos: int = 2,
) -> dict[str, Any]:
    """Envía la imagen al modelo y devuelve la extracción estructurada validada."""
    if not OPENAI_API_KEY:
        raise OCRClientError(
            "Falta OPENAI_API_KEY en la configuración privada del backend.",
            codigo_http=401,
            reintentable=False,
        )

    api_schema = adaptar_schema_para_api(schema)
    path = Path(path_imagen)
    if not path.exists():
        raise OCRClientError("No se encontró el archivo de soporte.", codigo_http=404, reintentable=False)

    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")

    body: dict[str, Any] = {
        "model": OPENAI_OCR_MODEL,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"},
                    {"type": "input_text", "text": prompt},
                ],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "extraccion_v1",
                "schema": api_schema,
                "strict": False,
            }
        },
    }

    ultimo_error: Exception | None = None
    for intento in range(max_reintentos + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)) as cliente:
                respuesta = cliente.post(
                    RESPONSES_URL,
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )

            if respuesta.status_code == 401:
                raise OCRClientError("Clave de API inválida o rechazada (401).", codigo_http=401, reintentable=False)
            if respuesta.status_code == 403:
                raise OCRClientError("Acceso prohibido a la API (403).", codigo_http=403, reintentable=False)
            if respuesta.status_code == 429:
                raise OCRClientError(
                    "Límite de velocidad excedido (429). Vuelve a intentarlo más tarde.",
                    codigo_http=429,
                    reintentable=True,
                )
            if 500 <= respuesta.status_code < 600 and intento < max_reintentos:
                raise OCRClientError(
                    f"Error del servidor ({respuesta.status_code}).",
                    codigo_http=respuesta.status_code,
                    reintentable=True,
                )
            respuesta.raise_for_status()

            datos = respuesta.json()
            texto = _extraer_texto_salida(datos)
            if not texto:
                raise OCRClientError(
                    "La respuesta de la API no contiene texto extraído.",
                    codigo_http=502,
                    reintentable=False,
                )
            return json.loads(texto)

        except httpx.TimeoutException as exc:
            ultimo_error = exc
            if intento >= max_reintentos:
                raise OCRClientError(
                    "Tiempo de espera agotado al contactar la API de reconocimiento.",
                    codigo_http=504,
                    reintentable=True,
                ) from exc
        except httpx.HTTPStatusError as exc:
            detalle = ""
            try:
                cuerpo = exc.response.json()
                if isinstance(cuerpo, dict) and "error" in cuerpo:
                    err = cuerpo["error"]
                    mensaje_err = err.get("message", "") if isinstance(err, dict) else str(err)
                    tipo_err = err.get("type", "") if isinstance(err, dict) else ""
                    detalle = f" [{tipo_err}] {mensaje_err}"
            except Exception:
                detalle = f" {exc.response.text[:200]}"
            raise OCRClientError(
                f"Error de la API de reconocimiento: {exc.response.status_code}{detalle}",
                codigo_http=exc.response.status_code,
                reintentable=False,
            ) from exc
        except json.JSONDecodeError as exc:
            raise OCRClientError(
                "La respuesta de la API no es JSON válido.",
                codigo_http=502,
                reintentable=False,
            ) from exc
        except OCRClientError:
            raise
        except Exception as exc:
            ultimo_error = exc
            if intento >= max_reintentos:
                raise OCRClientError(
                    f"Error inesperado contactando la API: {exc}",
                    codigo_http=500,
                    reintentable=False,
                ) from exc

    raise OCRClientError(str(ultimo_error) or "Error desconocido", codigo_http=500, reintentable=False)
