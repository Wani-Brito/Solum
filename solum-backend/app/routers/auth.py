from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..schemas import LoginIn, MeiIn, PerfilIn, PreferenciasIn, RegistroIn, SenhaIn
from ..security import criar_token, hash_senha, usuario_atual, verificar_senha
from ..servicos import RegraNegocio, ServicoMei, ServicoTeto

router = APIRouter(tags=["Autenticação e perfil"])


def _usuario_out(u: m.Usuario) -> dict:
    return {"id_usuario": u.id_usuario, "nome": u.nome, "email": u.email, "telefone": u.telefone, "perfil": u.perfil}


@router.post("/auth/registro", status_code=201)
def registrar(d: RegistroIn, db: Session = Depends(get_db)):
    if db.query(m.Usuario).filter_by(email=d.email.lower()).first():
        raise HTTPException(409, "Este e-mail já está cadastrado.")
    u = m.Usuario(nome=d.nome, email=d.email.lower(), senha=hash_senha(d.senha), telefone=d.telefone, perfil="NORMAL")
    db.add(u)
    db.flush()
    db.add(m.PreferenciasUsuario(id_usuario=u.id_usuario))
    db.commit()
    return {"access_token": criar_token(u), "token_type": "bearer", "usuario": _usuario_out(u)}


@router.post("/auth/login")
def login(d: LoginIn, db: Session = Depends(get_db)):
    u = db.query(m.Usuario).filter_by(email=d.email.lower()).first()
    if u is None or not verificar_senha(d.senha, u.senha) or not u.ativo:
        raise HTTPException(401, "E-mail ou senha inválidos.")
    return {"access_token": criar_token(u), "token_type": "bearer", "usuario": _usuario_out(u)}


@router.get("/usuarios/me")
def eu(u: m.Usuario = Depends(usuario_atual)):
    return _usuario_out(u)


@router.put("/usuarios/me")
def atualizar_perfil(d: PerfilIn, u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    u.nome, u.telefone = d.nome, d.telefone
    db.commit()
    return _usuario_out(u)


@router.put("/usuarios/me/senha")
def trocar_senha(d: SenhaIn, u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    if not verificar_senha(d.senha_atual, u.senha):
        raise HTTPException(400, "Senha atual incorreta.")
    u.senha = hash_senha(d.nova_senha)
    db.commit()
    return {"mensagem": "Senha alterada."}


def _prefs(db, u) -> m.PreferenciasUsuario:
    p = db.get(m.PreferenciasUsuario, u.id_usuario)
    if p is None:
        p = m.PreferenciasUsuario(id_usuario=u.id_usuario)
        db.add(p)
        db.commit()
    return p


def _prefs_out(p, alerta):
    return {"tema": p.tema, "notif_das": p.notif_das, "notif_dasn": p.notif_dasn, "notif_saldo": p.notif_saldo, "notif_teto": p.notif_teto,
            "notif_fatura": p.notif_fatura, "saldo_minimo": p.saldo_minimo, "percentual_alerta": alerta}


@router.get("/usuarios/me/preferencias")
def ler_prefs(u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    from datetime import date
    cfg = db.query(m.ConfiguracaoMei).filter_by(id_usuario=u.id_usuario, ano=date.today().year).first()
    return _prefs_out(_prefs(db, u), cfg.percentual_alerta if cfg else 80)


@router.put("/usuarios/me/preferencias")
def salvar_prefs(d: PreferenciasIn, u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    from datetime import date
    p = _prefs(db, u)
    dados = d.model_dump(exclude_none=True)
    alerta = dados.pop("percentual_alerta", None)
    for k, v in dados.items():
        setattr(p, k, v)
    db.commit()
    if alerta is not None:
        ServicoTeto(db).definir_alerta(u, date.today().year, alerta)
    cfg = db.query(m.ConfiguracaoMei).filter_by(id_usuario=u.id_usuario, ano=date.today().year).first()
    return _prefs_out(p, cfg.percentual_alerta if cfg else 80)


@router.get("/mei")
def ler_mei(u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    mei = ServicoMei(db).obter(u)
    if mei is None:
        raise HTTPException(404, "Dados do MEI ainda não cadastrados.")
    return {c.name: getattr(mei, c.name) for c in mei.__table__.columns if c.name != "id_usuario"}


@router.put("/mei")
def salvar_mei(d: MeiIn, u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    mei = ServicoMei(db).salvar(u, d)
    return {c.name: getattr(mei, c.name) for c in mei.__table__.columns if c.name != "id_usuario"}
