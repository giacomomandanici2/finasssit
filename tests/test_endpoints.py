from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_transaction_valida():
    payload = {
        "id": "TXN000001",
        "importo": "100.50",
        "causale": "bonifico_sepa",
        "data": "2026-04-22T10:00:00",
    }
    response = client.post("/transactions/score", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["transazione"]["id"] == "TXN000001"
    assert body["fascia"] in ("LOW", "MEDIUM", "HIGH")
    assert 0 <= body["score"] <= 100


def test_score_transaction_id_invalido():
    payload = {
        "id": "abc",   # non rispetta il pattern
        "importo": "100.00",
        "causale": "bonifico_sepa",
        "data": "2026-04-22T10:00:00",
    }
    response = client.post("/transactions/score", json=payload)
    assert response.status_code == 422   # validation error di FastAPI/Pydantic


def test_score_bonifico_estero_senza_contropartita():
    payload = {
        "id": "TXN000099",
        "importo": "-15000.00",
        "causale": "bonifico_estero",
        "data": "2026-04-22T10:00:00",
    }
    response = client.post("/transactions/score", json=payload)
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "TRANSAZIONE_INVALIDA"