import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_login_fail():
    resp = client.post("/login", data={"username": "fail@fail.com", "password": "fail"})
    assert resp.status_code == 400

def test_signup_and_login(monkeypatch):
    # Simula criação de usuário e login
    pass  # Implementação completa depende do fluxo de signup
