import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def get_jwt_token():
    resp = client.post("/login", data={"username": "admin@root.com", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_post_bot_start():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/bot/start", headers=headers)
    assert resp.status_code in (200, 400)

def test_post_bot_stop():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/bot/stop", headers=headers)
    assert resp.status_code in (200, 400)

def test_get_ordens():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/ordens", headers=headers)
    assert resp.status_code in (200, 404)

def test_get_performance():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/performance", headers=headers)
    assert resp.status_code in (200, 404)
