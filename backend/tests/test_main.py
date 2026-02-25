from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to Online Paper Reader API",
        "version": "2.2.0",
    }


def test_health_check():
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
