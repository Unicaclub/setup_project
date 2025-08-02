from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..models import Tenant
from ..database import get_session
from ..auth import get_current_user
from typing import List

router = APIRouter(prefix="/tenants", tags=["tenants"])

@router.get("/", response_model=List[Tenant])
def list_tenants(session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    # Apenas admin pode listar todos os tenants
    if not current_user.is_admin:
        return [session.get(Tenant, current_user.tenant_id)]
    return session.exec(select(Tenant)).all()

@router.post("/", response_model=Tenant)
def create_tenant(tenant: Tenant, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Apenas admin pode criar tenants")
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant

@router.get("/{tenant_id}", response_model=Tenant)
def get_tenant(tenant_id: int, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    tenant = session.get(Tenant, tenant_id)
    if not tenant or (not current_user.is_admin and tenant.id != current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    return tenant

@router.delete("/{tenant_id}")
def delete_tenant(tenant_id: int, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Apenas admin pode deletar tenants")
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    session.delete(tenant)
    session.commit()
    return {"ok": True}
