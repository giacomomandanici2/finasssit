from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_live():
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_score_ok():
    payload = {
        "id": "TXN000001",
        "importo": "1000.00",
        "descrizione": "bonifico_sepa",
        "timestamp": "2026-01-01T10:00:00",
    }

    response = client.post("/api/v1/score", json=payload)

    assert response.status_code == 200
    assert "score" in response.json()
    assert "fascia" in response.json()


def test_score_validation_error():
    payload = {
        "id": "WRONG",
        "iban": "IT60X0542811101000000123456",
        "importo": -100,
        "descrizione": "test",
        "timestamp": "2026-01-01T10:00:00",
    }

    response = client.post("/api/v1/score", json=payload)

    assert response.status_code == 422


def test_recent():
    response = client.get("/api/v1/recent")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# def test_score_transaction_valida():
#     payload = {
#         "id": "TXN000001",
#         "importo": "100.50",
#         "causale": "bonifico_sepa",
#         "data": "2026-04-22T10:00:00",
#     }
#     response = client.post("/transactions/score", json=payload)
#     assert response.status_code == 200
#     body = response.json()
#     assert body["transazione"]["id"] == "TXN000001"
#     assert body["fascia"] in ("LOW", "MEDIUM", "HIGH")
#     assert 0 <= body["score"] <= 100


# def test_score_transaction_id_invalido():
#     payload = {
#         "id": "abc",   # non rispetta il pattern
#         "importo": "100.00",
#         "causale": "bonifico_sepa",
#         "data": "2026-04-22T10:00:00",
#     }
#     response = client.post("/transactions/score", json=payload)
#     assert response.status_code == 422   # validation error di FastAPI/Pydantic


# def test_score_bonifico_estero_senza_contropartita():
#     payload = {
#         "id": "TXN000099",
#         "importo": "-15000.00",
#         "causale": "bonifico_estero",
#         "data": "2026-04-22T10:00:00",
#     }
#     response = client.post("/transactions/score", json=payload)
#     assert response.status_code == 400
#     body = response.json()
#     assert body["code"] == "TRANSAZIONE_INVALIDA"
