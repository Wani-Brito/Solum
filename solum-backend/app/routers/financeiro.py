from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..schemas import (CategoriaIn, ChatbotIn, ContaIn, FecharMesIn, PlanejarRetiradaIn, SimularIn, TransacaoIn)
from ..security import usuario_atual
from ..servicos import (RegraNegocio, ServicoFechamentoMensal, ServicoFluxoCaixa, ServicoTransacoes, dono)
from ..servicos_painel import ServicoDashboardMei
from ..util import linha

router = APIRouter(tags=["Financeiro do MEI"])


# ---- contas e categorias
@router.get("/contas")
def listar_contas(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(c) for c in db.query(m.Conta).filter_by(id_usuario=u.id_usuario).order_by(m.Conta.id_conta)]


@router.post("/contas", status_code=201)
def criar_conta(d: ContaIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    c = m.Conta(id_usuario=u.id_usuario, **d.model_dump())
    db.add(c)
    db.commit()
    return linha(c)


@router.put("/contas/{id_conta}")
def editar_conta(id_conta: int, d: ContaIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    c = dono(db, m.Conta, id_conta, u, "Conta")
    c.nome, c.banco = d.nome, d.banco
    db.commit()
    return linha(c)


@router.delete("/contas/{id_conta}", status_code=204)
def excluir_conta(id_conta: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    c = dono(db, m.Conta, id_conta, u, "Conta")
    if db.query(m.Transacao).filter_by(id_conta=id_conta).count():
        raise RegraNegocio("A conta tem transações e não pode ser excluída.", 409)
    db.delete(c)
    db.commit()


@router.get("/categorias")
def listar_categorias(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(c) for c in db.query(m.Categoria).filter_by(id_usuario=u.id_usuario).order_by(m.Categoria.tipo, m.Categoria.nome)]


@router.post("/categorias", status_code=201)
def criar_categoria(d: CategoriaIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    if db.query(m.Categoria).filter_by(id_usuario=u.id_usuario, nome=d.nome, tipo=d.tipo).first():
        raise RegraNegocio("Categoria já existe.", 409)
    c = m.Categoria(id_usuario=u.id_usuario, **d.model_dump())
    db.add(c)
    db.commit()
    return linha(c)


@router.delete("/categorias/{id_categoria}", status_code=204)
def excluir_categoria(id_categoria: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    c = dono(db, m.Categoria, id_categoria, u, "Categoria")
    if db.query(m.Transacao).filter_by(id_categoria=id_categoria).count():
        raise RegraNegocio("A categoria tem transações e não pode ser excluída.", 409)
    db.delete(c)
    db.commit()


# ---- transações
@router.get("/transacoes")
def listar_transacoes(ano: int | None = None, mes: int | None = Query(default=None, ge=1, le=12), tipo: str | None = None,
                      u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(t) for t in ServicoTransacoes(db).listar(u, ano, mes, tipo)]


@router.post("/transacoes", status_code=201)
def criar_transacao(d: TransacaoIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoTransacoes(db).criar(u, d))


@router.put("/transacoes/{id_transacao}")
def editar_transacao(id_transacao: int, d: TransacaoIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoTransacoes(db).atualizar(u, id_transacao, d))


@router.delete("/transacoes/{id_transacao}", status_code=204)
def excluir_transacao(id_transacao: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    ServicoTransacoes(db).remover(u, id_transacao)


@router.post("/chatbot/registrar-transacao", status_code=201)
def chatbot(d: ChatbotIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoTransacoes(db).pelo_chatbot(u, d))


# ---- fluxo de caixa
@router.get("/fluxo-caixa/historico")
def historico(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(f) for f in ServicoFluxoCaixa(db).historico(u.id_usuario)]


@router.get("/fluxo-caixa/{ano}/{mes}")
def fluxo_do_mes(ano: int, mes: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    if not 1 <= mes <= 12:
        raise RegraNegocio("Mês inválido.", 422)
    f = ServicoFluxoCaixa(db).consolidar(u.id_usuario, ano, mes)
    db.commit()
    return linha(f)


# ---- suavização de renda, reserva e retiradas
@router.post("/suavizacao/simular")
def simular(d: SimularIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return ServicoFechamentoMensal(db).simular(d)


@router.post("/suavizacao/fechar-mes")
def fechar_mes(d: FecharMesIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return ServicoFechamentoMensal(db).fechar(u, d.ano, d.mes, d.salario_desejado)


@router.get("/reserva")
def reserva(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    r = db.query(m.ReservaEstabilizacao).filter_by(id_usuario=u.id_usuario).first()
    movs = db.query(m.MovimentoReserva).filter_by(id_usuario=u.id_usuario).order_by(m.MovimentoReserva.id_movimento.desc()).all()
    return {"saldo": r.saldo if r else 0, "movimentos": [linha(x) for x in movs]}


@router.get("/retiradas")
def retiradas(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(r) for r in db.query(m.RetiradaMensal).filter_by(id_usuario=u.id_usuario).order_by(m.RetiradaMensal.ano, m.RetiradaMensal.mes)]


@router.put("/retiradas/planejar")
def planejar_retirada(d: PlanejarRetiradaIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    r = db.query(m.RetiradaMensal).filter_by(id_usuario=u.id_usuario, ano=d.ano, mes=d.mes).first()
    if r and r.status == "REALIZADA":
        raise RegraNegocio("Este mês já foi fechado; o salário não pode mais ser alterado.", 409)
    r = r or m.RetiradaMensal(id_usuario=u.id_usuario, ano=d.ano, mes=d.mes, valor=0)
    r.valor_desejado, r.status = d.valor_desejado, "PLANEJADA"
    db.add(r)
    db.commit()
    return linha(r)


@router.get("/dashboard")
def dashboard(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return ServicoDashboardMei(db).resumo(u, date.today())
