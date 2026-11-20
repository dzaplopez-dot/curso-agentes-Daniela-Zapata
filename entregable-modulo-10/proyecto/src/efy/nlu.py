import re

from . import config, llm
from .texto import contiene, normalizar

CONFIRMAR = {"SI", "S", "CONFIRMO", "CONFIRMAR", "DALE", "OK", "OKAY", "LISTO", "CLARO", "1"}
CANCELAR = {"NO", "N", "CANCELAR", "CANCELA", "CANCELO", "NADA", "0"}
SALUDOS = ("HOLA", "BUENAS", "BUEN DIA", "BUENOS DIAS", "BUENAS TARDES", "BUENAS NOCHES", "HEY")

PALABRAS_FAMILIA = {
    "FLORAL": ("FLORAL", "FLORES", "FLOR"),
    "MADEROSA": ("MADERA", "MADEROSA", "MADEROSO", "AMADERADO", "AMADERADA", "MADERABLE"),
    "ORIENTAL": ("ORIENTAL", "VAINILLA", "VANILLA", "AMBAR", "AMBER"),
    "AROMATICA": ("AROMATICO", "AROMATICA", "FOUGERE", "HERBAL"),
    "CITRICA": ("CITRICO", "CITRICA", "CITRICOS", "LIMON"),
    "CHIPRE": ("CHIPRE", "CHYPRE"),
    "AMBARADA": ("AMBARADO", "AMBARADA"),
}

SINONIMOS_FAMILIA = {"FRUTAL": "FLORAL", "FRUTAS": "FLORAL", "FLORAL FRUTAL": "FLORAL"}

PALABRAS_GENERO = {
    "M": ("HOMBRE", "HOMBRES", "MASCULINO", "CABALLERO", "PARA EL", "PARA HOMBRE"),
    "F": ("MUJER", "MUJERES", "FEMENINO", "DAMA", "PARA ELLA", "PARA MUJER"),
    "U": ("UNISEX", "PARA TODOS", "AMBOS"),
}

NUMEROS = {"UN": 1, "UNO": 1, "DOS": 2, "TRES": 3, "CUATRO": 4, "CINCO": 5}

VACIAS = {
    "ALGO", "RICO", "RICA", "PERFUME", "PERFUMES", "QUIERO", "QUISIERA", "BUSCO", "BUSCAR",
    "NECESITO", "RECOMIENDAME", "RECOMIENDA", "UN", "UNA", "UNOS", "UNAS", "PARA", "DE",
    "DEL", "LA", "EL", "LOS", "LAS", "CON", "Y", "O", "QUE", "ME", "MI", "GUSTARIA",
    "TENGO", "HAY", "ALGUN", "ALGUNA", "BUENO", "BUENA", "NUEVO", "NUEVA", "OLOR", "AROMA",
    "FRAGANCIA", "HOMBRE", "MUJER", "UNISEX", "UNIDAD", "UNIDADES", "FRASCO", "FRASCOS",
    "BOTELLA", "BOTELLAS", "COMPRAR", "PEDIR", "PRECIO", "CUANTO", "VALE", "COMO", "TIPO",
    "INSPIRADO", "PARECIDO", "SIMILAR", "POR", "FAVOR", "GRACIAS", "HOLA",
}


def _termino_libre(texto_norm):
    palabras = [p for p in texto_norm.split() if p not in VACIAS and not p.isdigit()]
    if len(palabras) >= 2:
        return " ".join(palabras[:4])
    return None



def _familia(texto_norm):
    for familia, palabras in PALABRAS_FAMILIA.items():
        for palabra in palabras:
            if contiene(texto_norm, palabra):
                return familia
    for palabra, familia in SINONIMOS_FAMILIA.items():
        if contiene(texto_norm, palabra):
            return familia
    return None


def _genero(texto_norm):
    for genero, palabras in PALABRAS_GENERO.items():
        for palabra in palabras:
            if contiene(texto_norm, palabra):
                return genero
    return None


def _inspirado(texto_norm, nombres):
    mejor = None
    for nombre in nombres:
        if contiene(texto_norm, nombre):
            if mejor is None or len(nombre) > len(mejor):
                mejor = nombre
    return mejor


def _casa(texto_norm, casas):
    mejor = None
    for casa in casas:
        if contiene(texto_norm, casa):
            if mejor is None or len(casa) > len(mejor):
                mejor = casa
    return mejor


def _cantidad(texto_norm):
    m = re.search(r"\b(\d+)\s*(?:UNIDAD|UNIDADES|FRASCO|FRASCOS|BOTELLA|BOTELLAS)\b", texto_norm)
    if m:
        return max(1, int(m.group(1)))
    for palabra, valor in NUMEROS.items():
        if contiene(texto_norm, palabra):
            return valor
    return 1


def _codigo(texto_norm):
    m = re.search(r"\b(\d{3,4})\b", texto_norm)
    return m.group(1) if m else None


def _reglas(texto, nombres, casas):
    texto_norm = normalizar(texto)
    palabras = texto_norm.split()
    intencion = "buscar"
    if texto_norm in CONFIRMAR or (len(palabras) <= 3 and palabras and palabras[0] in CONFIRMAR):
        intencion = "confirmar"
    elif texto_norm in CANCELAR or (len(palabras) <= 3 and palabras and palabras[0] in CANCELAR):
        intencion = "cancelar"
    elif texto_norm.startswith(SALUDOS):
        intencion = "saludo"
    salida = {
        "intencion": intencion,
        "codigo": _codigo(texto_norm),
        "cantidad": _cantidad(texto_norm),
        "inspirado": _inspirado(texto_norm, nombres),
        "casa": _casa(texto_norm, casas),
        "familia": _familia(texto_norm),
        "genero": _genero(texto_norm),
        "texto": texto,
    }
    if (
        intencion == "buscar"
        and not salida["codigo"]
        and not salida["inspirado"]
        and not salida["casa"]
        and not salida["familia"]
        and not salida["genero"]
    ):
        salida["inspirado"] = _termino_libre(texto_norm)
    return salida


def interpretar(texto, nombres=(), casas=()):
    salida = _reglas(texto, nombres, casas)
    if config.LLM_API_KEY and salida["intencion"] == "buscar":
        extra = llm.extraer(texto, nombres=nombres, casas=casas)
        if extra:
            for clave in ("inspirado", "casa", "familia", "genero"):
                if extra.get(clave) and not salida.get(clave):
                    salida[clave] = extra[clave]
            if extra.get("cantidad"):
                salida["cantidad"] = max(1, int(extra["cantidad"]))
    return salida
