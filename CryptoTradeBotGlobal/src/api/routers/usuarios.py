from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..models import Usuario
from ..database import get_session
from ..auth import get_current_user, get_password_hash
from typing import List

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

@router.get("/me", response_model=Usuario)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user

@router.get("/", response_model=List[Usuario])
def list_usuarios(session: Session = Depends(get_session), current_user: Usuario = Depends(get_current_user)):
    return session.exec(select(Usuario).where(Usuario.tenant_id == current_user.tenant_id)).all()

@router.post("/", response_model=Usuario)
def create_usuario(usuario: Usuario, session: Session = Depends(get_session), current_user: Usuario = Depends(get_current_user)):
    usuario.senha_hash = get_password_hash(usuario.senha_hash)
    usuario.tenant_id = current_user.tenant_id
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario

@router.get("/{usuario_id}", response_model=Usuario)
def get_usuario(usuario_id: int, session: Session = Depends(get_session), current_user: Usuario = Depends(get_current_user)):
    usuario = session.get(Usuario, usuario_id)
    if not usuario or usuario.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario

@router.delete("/{usuario_id}")
def delete_usuario(usuario_id: int, session: Session = Depends(get_session), current_user: Usuario = Depends(get_current_user)):
    usuario = session.get(Usuario, usuario_id)
    if not usuario or usuario.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    session.delete(usuario)
    session.commit()
    return {"ok": True}
