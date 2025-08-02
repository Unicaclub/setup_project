from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    usuarios: List["Usuario"] = Relationship(back_populates="tenant")
    planos: List["Plano"] = Relationship(back_populates="tenant")
    assinaturas: List["Assinatura"] = Relationship(back_populates="tenant")

class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    nome: str
    senha_hash: str
    tenant_id: int = Field(foreign_key="tenant.id")
    is_admin: bool = False
    usuarios: Optional["Tenant"] = Relationship(back_populates="usuarios")
    assinaturas: List["Assinatura"] = Relationship(back_populates="usuario")

class Plano(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    preco: float
    descricao: Optional[str]
    stripe_id: Optional[str]
    tenant_id: int = Field(foreign_key="tenant.id")
    tenant: Optional["Tenant"] = Relationship(back_populates="planos")
    assinaturas: List["Assinatura"] = Relationship(back_populates="plano")

class Assinatura(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id")
    plano_id: int = Field(foreign_key="plano.id")
    tenant_id: int = Field(foreign_key="tenant.id")
    status: str
    data_inicio: datetime
    data_fim: Optional[datetime]
    stripe_subscription_id: Optional[str]
    usuario: Optional["Usuario"] = Relationship(back_populates="assinaturas")
    plano: Optional["Plano"] = Relationship(back_populates="assinaturas")
    tenant: Optional["Tenant"] = Relationship(back_populates="assinaturas")
