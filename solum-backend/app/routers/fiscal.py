from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models as m
from ..database import get_db
from ..schemas import (AporteIn, AplicacaoIn, AssinarIn, ClienteIn, FaturaIn, MetaIn, PagarFaturaIn, PrecificarIn,
                       RecomendacaoIn, ServicoIn, StatusPropostaIn)
from ..security import exige_premium, usuario_atual
from ..servicos import (RegraNegocio, ServicoAssinaturas, ServicoFaturas, ServicoImposto, ServicoInvestimentos, ServicoMetas,
                        ServicoNotificacoes, ServicoPrecificacao, ServicoTeto, dono)
from ..util import linha

router = APIRouter(tags=["Impostos, clientes, planejamento e planos"])


# ---- impostos e teto
@router.get("/impostos/das")
def das(ano: int | None = None, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    ano = ano or date.today().year
    comp, mei = ServicoImposto(db).composicao(u, ano)
    return {"ano": ano, "tipo_atividade": mei.tipo_atividade, "categoria": mei.categoria, "total": comp.total,
            "esferas": {k: {"tributo": v["tributo"], "valor": v["valor"]} for k, v in comp.esferas().items()}}


@router.post("/impostos/cota-mensal")
def cota_mensal(ano: int | None = None, mes: int | None = None, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    hoje = date.today()
    return ServicoImposto(db).cota_mensal(u, ano or hoje.year, mes or hoje.month, hoje)


@router.post("/impostos/obrigacoes/gerar")
def gerar_obrigacoes(ano: int | None = None, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return {"criadas": ServicoImposto(db).gerar_obrigacoes(u, ano or date.today().year)}


@router.get("/impostos/obrigacoes")
def obrigacoes(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    ServicoImposto(db).atualizar_atrasos(u, date.today())
    return [linha(o) for o in db.query(m.ObrigacaoImposto).filter_by(id_usuario=u.id_usuario).order_by(m.ObrigacaoImposto.data_vencimento)]


@router.patch("/impostos/obrigacoes/{id_obrigacao}/pagar")
def pagar_obrigacao(id_obrigacao: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoImposto(db).pagar(u, id_obrigacao))


@router.get("/teto")
def teto(ano: int | None = None, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return ServicoTeto(db).status(u, ano or date.today().year)


# ---- clientes e faturas
@router.get("/clientes")
def listar_clientes(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(c) for c in db.query(m.Cliente).filter_by(id_usuario=u.id_usuario).order_by(m.Cliente.nome)]


@router.post("/clientes", status_code=201)
def criar_cliente(d: ClienteIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    c = m.Cliente(id_usuario=u.id_usuario, **d.model_dump())
    db.add(c)
    db.commit()
    return linha(c)


@router.put("/clientes/{id_cliente}")
def editar_cliente(id_cliente: int, d: ClienteIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    c = dono(db, m.Cliente, id_cliente, u, "Cliente")
    for k, v in d.model_dump().items():
        setattr(c, k, v)
    db.commit()
    return linha(c)


@router.patch("/clientes/{id_cliente}/desbloquear")
def desbloquear(id_cliente: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    c = dono(db, m.Cliente, id_cliente, u, "Cliente")
    c.bloqueado = False
    db.commit()
    return linha(c)


@router.get("/faturas")
def listar_faturas(status: str | None = None, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    ServicoFaturas(db).atualizar_status(u.id_usuario, date.today())
    q = db.query(m.Fatura).filter_by(id_usuario=u.id_usuario)
    if status:
        q = q.filter_by(status=status)
    return [linha(f) for f in q.order_by(m.Fatura.data_vencimento.desc())]


@router.post("/faturas", status_code=201)
def criar_fatura(d: FaturaIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoFaturas(db).criar(u, d))


@router.patch("/faturas/{id_fatura}/pagar")
def pagar_fatura(id_fatura: int, d: PagarFaturaIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoFaturas(db).pagar(u, id_fatura, d))


@router.patch("/faturas/{id_fatura}/nota")
def emitir_nota(id_fatura: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoFaturas(db).emitir_nota(u, id_fatura))


@router.post("/faturas/atualizar-status")
def atualizar_status(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return ServicoFaturas(db).atualizar_status(u.id_usuario, date.today())


# ---- notificações
@router.post("/notificacoes/gerar")
def gerar_notificacoes(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(n) for n in ServicoNotificacoes(db).gerar(u, date.today())]


@router.get("/notificacoes")
def listar_notificacoes(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(n) for n in db.query(m.Notificacao).filter_by(id_usuario=u.id_usuario).order_by(m.Notificacao.data_criacao.desc(), m.Notificacao.id_notificacao.desc())]


@router.patch("/notificacoes/{id_notificacao}/lida")
def marcar_lida(id_notificacao: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    n = dono(db, m.Notificacao, id_notificacao, u, "Notificação")
    n.lida = True
    db.commit()
    return linha(n)


# ---- serviços e precificação
@router.get("/servicos")
def listar_servicos(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    rows = db.query(m.Servico).filter_by(id_usuario=u.id_usuario).order_by(m.Servico.nome).all()
    out = []
    for s in rows:
        p = db.query(m.Precificacao).filter_by(id_servico=s.id_servico).first()
        out.append({**linha(s), "precificacao": linha(p) if p else None})
    return out


@router.post("/servicos", status_code=201)
def criar_servico(d: ServicoIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    s = m.Servico(id_usuario=u.id_usuario, **d.model_dump())
    db.add(s)
    db.commit()
    return linha(s)


@router.post("/precificacao/calcular")
def precificar(d: PrecificarIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return ServicoPrecificacao(db).calcular(u, d, date.today().year)


# ---- metas
@router.get("/metas")
def listar_metas(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return [linha(x) for x in db.query(m.MetaFinanceira).filter_by(id_usuario=u.id_usuario).order_by(m.MetaFinanceira.prazo)]


@router.post("/metas", status_code=201)
def criar_meta(d: MetaIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    meta = m.MetaFinanceira(id_usuario=u.id_usuario, **d.model_dump())
    db.add(meta)
    db.commit()
    return linha(meta)


@router.post("/metas/{id_meta}/aporte")
def aportar(id_meta: int, d: AporteIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoMetas(db).aportar(u, id_meta, d.valor))


@router.delete("/metas/{id_meta}", status_code=204)
def excluir_meta(id_meta: int, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    meta = dono(db, m.MetaFinanceira, id_meta, u, "Meta")
    db.delete(meta)
    db.commit()


# ---- investimentos (Premium)
@router.get("/investimentos/carteira")
def carteira(u=Depends(exige_premium), db: Session = Depends(get_db)):
    c = ServicoInvestimentos(db).carteira(u)
    itens = db.query(m.Investimento).filter_by(id_carteira=c.id_carteira).all()
    total = sum((i.valor_atual for i in itens), 0)
    media = round(sum(i.valor_atual * i.rentabilidade for i in itens) / total, 2) if total else 0
    return {"carteira": linha(c), "total": total, "rentabilidade_media": media, "investimentos": [linha(i) for i in itens]}


@router.post("/investimentos/aplicacoes", status_code=201)
def aplicar(d: AplicacaoIn, u=Depends(exige_premium), db: Session = Depends(get_db)):
    c = ServicoInvestimentos(db).carteira(u)
    i = m.Investimento(id_carteira=c.id_carteira, **d.model_dump())
    db.add(i)
    db.commit()
    return linha(i)


@router.get("/investimentos/propostas")
def propostas(u=Depends(exige_premium), db: Session = Depends(get_db)):
    return [linha(p) for p in db.query(m.PropostaInvestimento).filter_by(id_usuario=u.id_usuario).order_by(m.PropostaInvestimento.id_proposta.desc())]


@router.post("/investimentos/recomendacao", status_code=201)
def recomendar(d: RecomendacaoIn, u=Depends(exige_premium), db: Session = Depends(get_db)):
    return linha(ServicoInvestimentos(db).recomendar(u, d))


@router.patch("/investimentos/propostas/{id_proposta}")
def decidir_proposta(id_proposta: int, d: StatusPropostaIn, u=Depends(exige_premium), db: Session = Depends(get_db)):
    p = dono(db, m.PropostaInvestimento, id_proposta, u, "Proposta")
    if p.status != "DISPONIVEL":
        raise RegraNegocio("Esta proposta já foi respondida.", 409)
    p.status = d.status
    db.commit()
    return linha(p)


@router.get("/investimentos/cotacoes")
def cotacoes(u=Depends(exige_premium), db: Session = Depends(get_db)):
    atualizadas = ServicoInvestimentos(db).atualizar_cotacoes()
    return {"atualizadas_agora": atualizadas, "cotacoes": [linha(c) for c in db.query(m.CotacaoCache).order_by(m.CotacaoCache.simbolo)]}


# ---- planos e assinatura (pagamento simulado)
@router.get("/planos")
def planos(db: Session = Depends(get_db)):
    return [linha(p) for p in db.query(m.Plano).filter_by(ativo=True).order_by(m.Plano.preco_mensal)]


@router.post("/assinaturas", status_code=201)
def assinar(d: AssinarIn, u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoAssinaturas(db).assinar(u, d.nome_plano))


@router.delete("/assinaturas/minha")
def cancelar(u=Depends(usuario_atual), db: Session = Depends(get_db)):
    return linha(ServicoAssinaturas(db).cancelar(u))
