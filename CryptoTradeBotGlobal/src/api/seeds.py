from .database import engine
from .models import SQLModel, Tenant, Usuario, Plano
from sqlmodel import Session
from .auth import get_password_hash

def seed():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Criar tenant demo
        tenant = Tenant(nome="Demo Tenant")
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        # Criar admin root
        admin = Usuario(email="admin@root.com", nome="Admin Root", senha_hash=get_password_hash("admin123"), tenant_id=tenant.id, is_admin=True)
        session.add(admin)
        # Criar plano demo
        plano = Plano(nome="Demo", preco=0, descricao="Plano Demo", tenant_id=tenant.id)
        session.add(plano)
        session.commit()
        print("Seeds criados com sucesso!")

if __name__ == "__main__":
    seed()
