import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

DATOS = RAIZ.parent / "datos" / "catalogo.csv"


@pytest.fixture
def agente(tmp_path, monkeypatch):
    from efy import config, db, seed
    from efy.agent import Agente

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "efy_test.db")
    monkeypatch.setattr(config, "CATALOGO", DATOS)
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    db.inicializar()
    seed.cargar()
    return Agente()
