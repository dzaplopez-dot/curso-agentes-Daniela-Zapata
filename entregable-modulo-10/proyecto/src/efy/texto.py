import re
import unicodedata


def normalizar(texto):
    if not texto:
        return ""
    base = unicodedata.normalize("NFD", str(texto))
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    base = base.upper()
    base = re.sub(r"[^A-Z0-9]+", " ", base)
    return re.sub(r"\s+", " ", base).strip()


def contiene(texto_normalizado, aguja):
    n = normalizar(aguja)
    if not n:
        return False
    return f" {n} " in f" {texto_normalizado} "


def formatear_precio(valor):
    return f"${int(round(float(valor))):,}".replace(",", ".")


def titulo(texto):
    return " ".join(p.capitalize() for p in str(texto or "").split())
