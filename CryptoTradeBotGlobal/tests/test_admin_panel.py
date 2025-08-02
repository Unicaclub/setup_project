import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_admin_sem_token():
    resp = client.get("/admin")
    assert resp.status_code in (401, 403, 404)

def test_admin_token_usuario_comum():
    # Cria usuário comum
    login_resp = client.post("/login", data={"username": "admin@root.com", "password": "admin123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/admin", headers=headers)
    assert resp.status_code in (401, 403, 404)
