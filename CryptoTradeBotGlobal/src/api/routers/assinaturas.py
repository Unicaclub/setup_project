from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..models import Assinatura
from ..database import get_session
from ..auth import get_current_user
from typing import List

router = APIRouter(prefix="/assinaturas", tags=["assinaturas"])

@router.get("/", response_model=List[Assinatura])
def list_assinaturas(session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return session.exec(select(Assinatura).where(Assinatura.tenant_id == current_user.tenant_id)).all()

@router.post("/", response_model=Assinatura)
def create_assinatura(assinatura: Assinatura, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    assinatura.tenant_id = current_user.tenant_id
    session.add(assinatura)
    session.commit()
    session.refresh(assinatura)
    return assinatura

@router.get("/{assinatura_id}", response_model=Assinatura)
def get_assinatura(assinatura_id: int, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    assinatura = session.get(Assinatura, assinatura_id)
    if not assinatura or assinatura.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    return assinatura

@router.delete("/{assinatura_id}")
def delete_assinatura(assinatura_id: int, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    assinatura = session.get(Assinatura, assinatura_id)
    if not assinatura or assinatura.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    session.delete(assinatura)
    session.commit()
    return {"ok": True}
