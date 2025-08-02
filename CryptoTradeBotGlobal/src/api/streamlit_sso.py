import streamlit as st
import jwt
import requests
import os

# Exemplo de integração SSO JWT com Streamlit
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.title("Painel Streamlit Multi-Tenant")

token = st.text_input("Cole seu JWT aqui:")
if token:
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        st.write("Usuário:", payload)
        # Buscar dados do tenant
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{API_URL}/usuarios/me", headers=headers)
        st.write("Dados do usuário:", r.json())
    except Exception as e:
        st.error(f"Token inválido: {e}")
