from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..models import Plano
from ..database import get_session
from ..auth import get_current_user
from typing import List

router = APIRouter(prefix="/planos", tags=["planos"])

@router.get("/", response_model=List[Plano])
def list_planos(session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    return session.exec(select(Plano).where(Plano.tenant_id == current_user.tenant_id)).all()

@router.post("/", response_model=Plano)
def create_plano(plano: Plano, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    plano.tenant_id = current_user.tenant_id
    session.add(plano)
    session.commit()
    session.refresh(plano)
    return plano

@router.get("/{plano_id}", response_model=Plano)
def get_plano(plano_id: int, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    plano = session.get(Plano, plano_id)
    if not plano or plano.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    return plano

@router.delete("/{plano_id}")
def delete_plano(plano_id: int, session: Session = Depends(get_session), current_user=Depends(get_current_user)):
    plano = session.get(Plano, plano_id)
    if not plano or plano.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    session.delete(plano)
    session.commit()
    return {"ok": True}
