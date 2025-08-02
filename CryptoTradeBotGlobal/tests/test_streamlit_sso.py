import pytest
import streamlit_dashboard
import jwt

def test_token_invalido(monkeypatch):
    # Token inválido deve gerar erro
    with pytest.raises(Exception):
        jwt.decode("token_invalido", options={"verify_signature": False})

# Testes de integração completos dependem de ambiente Streamlit rodando
