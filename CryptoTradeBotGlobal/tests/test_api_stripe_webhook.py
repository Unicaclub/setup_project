import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import json

client = TestClient(app)

def test_stripe_webhook_success(monkeypatch):
    # Simula evento Stripe válido
    payload = {"type": "checkout.session.completed", "data": {"object": {"id": "sess_123"}}}
    headers = {"stripe-signature": "test"}
    monkeypatch.setattr("stripe.Webhook.construct_event", lambda p, s, k: payload)
    resp = client.post("/stripe/webhook", data=json.dumps(payload), headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

def test_stripe_webhook_fail(monkeypatch):
    # Simula falha de verificação
    monkeypatch.setattr("stripe.Webhook.construct_event", lambda p, s, k: (_ for _ in ()).throw(Exception("fail")))
    resp = client.post("/stripe/webhook", data="{}", headers={"stripe-signature": "test"})
    assert resp.status_code == 400
