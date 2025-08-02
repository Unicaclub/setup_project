from fastapi import FastAPI, Depends
from fastapi_admin.app import app as admin_app
from fastapi_admin.providers.login import UsernamePasswordProvider
from .models import Usuario
from .database import get_session

# Exemplo de painel admin usando fastapi-admin
# (Requer configuração extra, veja README)

def mount_admin(app: FastAPI):
    app.mount("/admin", admin_app)
    admin_app.add_login_provider(UsernamePasswordProvider(
        admin_model=Usuario,
        get_session=get_session
    ))
