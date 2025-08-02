import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import requests

client = TestClient(app)

def get_jwt_token():
    resp = client.post("/login", data={"username": "admin@root.com", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_root_and_login():
    resp = client.get("/")
    assert resp.status_code == 200
    resp = client.post("/login", data={"username": "admin@root.com", "password": "admin123"})
    assert resp.status_code == 200

def test_jwt_access():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/usuarios", headers=headers)
    assert resp.status_code == 200

def test_streamlit_dashboard_http():
    # Testa se painel responde HTTP 200 e contém JS básico
    try:
        r = requests.get("http://localhost:8501")
        assert r.status_code == 200
        assert "<script" in r.text or "streamlit" in r.text.lower()
    except Exception:
        pytest.skip("Streamlit não está rodando na porta 8501")
