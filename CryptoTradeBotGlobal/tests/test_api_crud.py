import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_crud_usuario():
    # Exemplo: criar, buscar, deletar usuário (mock ou seed)
    pass

def test_crud_plano():
    pass

def test_crud_assinatura():
    pass

def test_crud_tenant():
    pass
