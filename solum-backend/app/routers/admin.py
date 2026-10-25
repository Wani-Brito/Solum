from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..schemas import AdminUsuarioIn, AdminUsuarioPatch, CnaeIn, ConfigSistemaIn, TabelaDASIn
from ..security import exige_admin, hash_senha
from ..servicos import RegraNegocio, ServicoAssinaturas
from ..servicos_painel import ServicoDashboardAdmin, registrar_log
from ..util import linha

router = APIRouter(prefix="/admin", tags=["Administração"])


@router.get("/dashboard")
def dashboard(a=Depends(exige_admin), db: Session = Depends(get_db)):
    return ServicoDashboardAdmin(db).controle(date.today())


@router.get("/vendas")
def vendas(a=Depends(exige_admin), db: Session = Depends(get_db)):
    return ServicoDashboardAdmin(db).vendas(date.today())


@router.get("/usuarios")
def listar_usuarios(busca: str | None = None, perfil: str | None = None, a=Depends(exige_admin), db: Session = Depends(get_db)):
    q = db.query(m.Usuario)
    if busca:
        q = q.filter(m.Usuario.nome.ilike(f"%{busca}%") | m.Usuario.email.ilike(f"%{busca}%"))
    if perfil:
        q = q.filter_by(perfil=perfil)
    return [linha(u) for u in q.order_by(m.Usuario.data_cadastro.desc())]


@router.post("/usuarios", status_code=201)
def criar_usuario(d: AdminUsuarioIn, a=Depends(exige_admin), db: Session = Depends(get_db)):
    if db.query(m.Usuario).filter_by(email=d.email.lower()).first():
        raise HTTPException(409, "Este e-mail já está cadastrado.")
    u = m.Usuario(nome=d.nome, email=d.email.lower(), senha=hash_senha(d.senha), perfil=d.perfil)
    db.add(u)
    db.flush()
    db.add(m.PreferenciasUsuario(id_usuario=u.id_usuario))
    db.commit()
    registrar_log(db, a, f"Criou o usuário {u.nome}", u.email)
    return linha(u)


@router.patch("/usuarios/{id_usuario}")
def alterar_usuario(id_usuario: int, d: AdminUsuarioPatch, a=Depends(exige_admin), db: Session = Depends(get_db)):
    u = db.get(m.Usuario, id_usuario)
    if u is None:
        raise RegraNegocio("Usuário não encontrado.", 404)
    if u.id_usuario == a.id_usuario and (d.perfil not in (None, "ADMIN") or d.ativo is False):
        raise RegraNegocio("Você não pode remover seu próprio acesso de administrador.", 409)
    if d.perfil is not None:
        u.perfil = d.perfil
    if d.ativo is not None:
        u.ativo = d.ativo
    db.commit()
    registrar_log(db, a, f"Alterou o usuário {u.nome}", u.email)
    return linha(u)


@router.get("/tabela-das")
def listar_tabelas(a=Depends(exige_admin), db: Session = Depends(get_db)):
    return [linha(t) for t in db.query(m.TabelaDAS).order_by(m.TabelaDAS.ano.desc())]


@router.put("/tabela-das/{ano}")
def salvar_tabela(ano: int, d: TabelaDASIn, a=Depends(exige_admin), db: Session = Depends(get_db)):
    t = db.query(m.TabelaDAS).filter_by(ano=ano).first() or m.TabelaDAS(ano=ano)
    for k, v in d.model_dump().items():
        setattr(t, k, v)
    t.data_atualizacao = m.agora()
    db.add(t)
    db.commit()
    registrar_log(db, a, f"Editou a Tabela DAS {ano}", str(ano))
    return linha(t)


@router.get("/configuracoes")
def ler_config(a=Depends(exige_admin), db: Session = Depends(get_db)):
    base = {"percentual_alerta_padrao": "80", "dias_aviso_das": "3", "dias_aviso_dasn": "30"}
    base.update({c.chave: c.valor for c in db.query(m.ConfiguracaoSistema).all()})
    return base


@router.put("/configuracoes")
def salvar_config(d: ConfigSistemaIn, a=Depends(exige_admin), db: Session = Depends(get_db)):
    for chave, valor in d.model_dump().items():
        c = db.get(m.ConfiguracaoSistema, chave) or m.ConfiguracaoSistema(chave=chave, valor="")
        c.valor = str(valor)
        db.add(c)
    db.commit()
    registrar_log(db, a, "Alterou as configurações gerais")
    return ler_config(a, db)


@router.post("/cnaes", status_code=201)
def importar_cnaes(itens: list[CnaeIn], a=Depends(exige_admin), db: Session = Depends(get_db)):
    n = 0
    for i in itens:
        cod = "".join(ch for ch in i.cnae if ch.isdigit())
        if len(cod) != 7:
            raise RegraNegocio(f"CNAE inválido: {i.cnae}", 422)
        c = db.get(m.CnaeMei, cod) or m.CnaeMei(cnae=cod, descricao=i.descricao, tipo_atividade=i.tipo_atividade)
        c.descricao, c.tipo_atividade = i.descricao, i.tipo_atividade
        db.add(c)
        n += 1
    db.commit()
    registrar_log(db, a, f"Importou {n} CNAEs permitidos ao MEI")
    return {"importados": n}


@router.get("/logs")
def logs(a=Depends(exige_admin), db: Session = Depends(get_db)):
    return [linha(x) for x in db.query(m.LogAdmin).order_by(m.LogAdmin.data_hora.desc()).limit(100)]


@router.post("/assinaturas/cobrar")
def cobrar_mensalidades(a=Depends(exige_admin), db: Session = Depends(get_db)):
    """Cobrança mensal simulada das assinaturas ativas."""
    n = ServicoAssinaturas(db).cobrar_mensalidades(date.today())
    registrar_log(db, a, f"Cobrança mensal simulada: {n} pagamentos")
    return {"pagamentos_criados": n}
