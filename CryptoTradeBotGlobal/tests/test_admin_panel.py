import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_admin_sem_token():
    resp = client.get("/admin")
    assert resp.status_code in (401, 403, 404)

def test_admin_token_usuario_comum(monkeypatch):
    # Simula token de usuário comum
    pass  # Implementação depende do fluxo de autenticação/admin
