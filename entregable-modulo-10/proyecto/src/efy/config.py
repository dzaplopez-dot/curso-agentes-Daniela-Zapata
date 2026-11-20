import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parents[2]
RAIZ_ENTREGABLE = BASE_DIR.parent

DB_PATH = Path(os.getenv("EFY_DB_PATH", str(BASE_DIR / "efy.db")))
CATALOGO = Path(os.getenv("EFY_CATALOGO", str(RAIZ_ENTREGABLE / "datos" / "catalogo.csv")))

BACKEND = os.getenv("EFY_BACKEND", "sqlite").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

STOCK_INICIAL = int(os.getenv("EFY_STOCK_INICIAL", "10"))
PRECIO_DEFECTO = int(os.getenv("EFY_PRECIO_DEFECTO", "40000"))
ML_DEFECTO = int(os.getenv("EFY_ML_DEFECTO", "100"))
STOCK_BAJO = int(os.getenv("EFY_STOCK_BAJO", "5"))
