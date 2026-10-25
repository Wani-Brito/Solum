"""Autenticação por token (JWT) e controle de acesso por perfil."""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models as m
from .config import settings
from .database import get_db

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


def hash_senha(senha: str) -> str:
    return _pwd.hash(senha)


def verificar_senha(senha: str, hash_: str) -> bool:
    try:
        return _pwd.verify(senha, hash_)
    except Exception:
        return False


def criar_token(usuario: m.Usuario) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.token_minutos)
    return jwt.encode({"sub": str(usuario.id_usuario), "exp": exp}, settings.secret_key, algorithm="HS256")


def usuario_atual(cred: HTTPAuthorizationCredentials = Depends(_bearer), db: Session = Depends(get_db)) -> m.Usuario:
    if cred is None:
        raise HTTPException(401, "Não autenticado.")
    try:
        dados = jwt.decode(cred.credentials, settings.secret_key, algorithms=["HS256"])
        usuario = db.get(m.Usuario, int(dados["sub"]))
    except Exception:
        raise HTTPException(401, "Token inválido ou expirado.")
    if usuario is None or not usuario.ativo:
        raise HTTPException(401, "Usuário inexistente ou desativado.")
    return usuario


def exige_premium(usuario: m.Usuario = Depends(usuario_atual)) -> m.Usuario:
    if usuario.perfil not in ("PREMIUM", "ADMIN"):
        raise HTTPException(403, "Recurso exclusivo do plano Premium.")
    return usuario


def exige_admin(usuario: m.Usuario = Depends(usuario_atual)) -> m.Usuario:
    if usuario.perfil != "ADMIN":
        raise HTTPException(403, "Acesso restrito a administradores.")
    return usuario
