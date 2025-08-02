import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def get_jwt_token():
    # Login com seed admin
    resp = client.post("/login", data={"username": "admin@root.com", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_crud_usuario():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Criar usuário
    usuario = {"email": "novo@user.com", "nome": "Novo User", "senha_hash": "senha123", "tenant_id": 1}
    resp = client.post("/usuarios/", json=usuario, headers=headers)
    assert resp.status_code == 200
    user_id = resp.json()["id"]
    # Buscar usuário
    resp = client.get(f"/usuarios/{user_id}", headers=headers)
    assert resp.status_code == 200
    # Atualizar usuário (não implementado, mas exemplo)
    # Deletar usuário
    resp = client.delete(f"/usuarios/{user_id}", headers=headers)
    assert resp.status_code == 200

def test_crud_plano():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Criar plano
    plano = {"nome": "Pro", "preco": 99.9, "descricao": "Plano Pro", "tenant_id": 1}
    resp = client.post("/planos/", json=plano, headers=headers)
    assert resp.status_code == 200
    plano_id = resp.json()["id"]
    # Buscar plano
    resp = client.get(f"/planos/{plano_id}", headers=headers)
    assert resp.status_code == 200
    # Deletar plano
    resp = client.delete(f"/planos/{plano_id}", headers=headers)
    assert resp.status_code == 200

def test_crud_assinatura():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Criar plano para assinatura
    plano = {"nome": "Assinatura Teste", "preco": 10, "descricao": "Teste", "tenant_id": 1}
    resp = client.post("/planos/", json=plano, headers=headers)
    plano_id = resp.json()["id"]
    # Criar usuário
    usuario = {"email": "assinatura@user.com", "nome": "Assinatura User", "senha_hash": "senha123", "tenant_id": 1}
    resp = client.post("/usuarios/", json=usuario, headers=headers)
    usuario_id = resp.json()["id"]
    # Criar assinatura
    assinatura = {"usuario_id": usuario_id, "plano_id": plano_id, "tenant_id": 1, "status": "ATIVA", "data_inicio": "2025-01-01T00:00:00"}
    resp = client.post("/assinaturas/", json=assinatura, headers=headers)
    assert resp.status_code == 200
    assinatura_id = resp.json()["id"]
    # Buscar assinatura
    resp = client.get(f"/assinaturas/{assinatura_id}", headers=headers)
    assert resp.status_code == 200
    # Deletar assinatura
    resp = client.delete(f"/assinaturas/{assinatura_id}", headers=headers)
    assert resp.status_code == 200
