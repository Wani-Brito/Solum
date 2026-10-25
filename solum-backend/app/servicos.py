"""Camada de serviços: orquestra o domínio (regras puras) e o banco."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from . import models as m
from .dominio import fatura as regras_fatura
from .dominio.chatbot import interpretar
from .dominio.das import ComposicaoDAS, ParametrosDAS, calcular_das
from .dominio.dinheiro import D, q
from .dominio.fluxo import FluxoCaixa as FluxoDominio
from .dominio.notificacao import gerar_notificacoes
from .dominio.precificacao import calcular_preco_minimo
from .dominio.reserva import ReservaEstabilizacao as ReservaDominio
from .dominio.suavizacao import ServicoSuavizacao
from .dominio.teto import StatusTeto, avaliar_teto, teto_proporcional
from .dominio.transacao import criar_transacao


class RegraNegocio(Exception):
    """Erro de regra de negócio. status: 404 (não encontrado), 409 (conflito) ou 422 (dado inválido)."""

    def __init__(self, mensagem: str, status: int = 422):
        super().__init__(mensagem)
        self.status = status


def _periodo(ano: int, mes: int):
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
    return date(ano, mes, 1), fim


# ---------------------------------------------------------------- repositórios
class RepositorioTabelaDAS:
    def __init__(self, db: Session):
        self.db = db

    def por_ano(self, ano: int) -> m.TabelaDAS | None:
        return self.db.query(m.TabelaDAS).filter_by(ano=ano).first()

    def parametros(self, ano: int) -> ParametrosDAS:
        t = self.por_ano(ano)
        if t is None:
            raise RegraNegocio(f"A Tabela DAS de {ano} ainda não foi cadastrada pelo administrador.", 422)
        return ParametrosDAS(t.ano, D(t.salario_minimo), D(t.perc_inss), D(t.perc_inss_caminhoneiro), D(t.valor_icms),
                             D(t.valor_iss), D(t.teto_anual), D(t.teto_caminhoneiro), t.fonte)


class RepositorioReserva:
    def __init__(self, db: Session):
        self.db = db

    def obter_ou_criar(self, id_usuario: int) -> m.ReservaEstabilizacao:
        r = self.db.query(m.ReservaEstabilizacao).filter_by(id_usuario=id_usuario).first()
        if r is None:
            r = m.ReservaEstabilizacao(id_usuario=id_usuario, saldo=0)
            self.db.add(r)
            self.db.flush()
        return r


def dono(db: Session, modelo, id_, usuario: m.Usuario, nome: str = "Registro"):
    obj = db.get(modelo, id_)
    if obj is None or getattr(obj, "id_usuario", usuario.id_usuario) != usuario.id_usuario:
        raise RegraNegocio(f"{nome} não encontrado.", 404)
    return obj


# ---------------------------------------------------------------------- MEI
class ServicoMei:
    def __init__(self, db: Session):
        self.db = db

    def obter(self, usuario) -> m.DadosMei | None:
        return self.db.query(m.DadosMei).filter_by(id_usuario=usuario.id_usuario).first()

    def exigir(self, usuario) -> m.DadosMei:
        mei = self.obter(usuario)
        if mei is None:
            raise RegraNegocio("Cadastre os dados do MEI (atividade, CNAE e categoria) primeiro.", 422)
        return mei

    def salvar(self, usuario, dados) -> m.DadosMei:
        cnae = "".join(c for c in dados.cnae if c.isdigit())
        if len(cnae) != 7:
            raise RegraNegocio("O CNAE deve ter 7 dígitos.", 422)
        if self.db.query(m.CnaeMei).count() > 0 and self.db.get(m.CnaeMei, cnae) is None:
            raise RegraNegocio("Este CNAE não está na lista de atividades permitidas ao MEI.", 422)
        mei = self.obter(usuario) or m.DadosMei(id_usuario=usuario.id_usuario)
        for campo, valor in dados.model_dump().items():
            setattr(mei, campo, cnae if campo == "cnae" else valor)
        self.db.add(mei)
        self.db.commit()
        return mei


# ------------------------------------------------------------- fluxo de caixa
class ServicoFluxoCaixa:
    def __init__(self, db: Session):
        self.db = db

    def _saldo_anterior(self, id_usuario, ano, mes) -> Decimal:
        f = (self.db.query(m.FluxoCaixa).filter(m.FluxoCaixa.id_usuario == id_usuario,
             or_(m.FluxoCaixa.ano < ano, and_(m.FluxoCaixa.ano == ano, m.FluxoCaixa.mes < mes)))
             .order_by(m.FluxoCaixa.ano.desc(), m.FluxoCaixa.mes.desc()).first())
        return D(f.saldo_final) if f else Decimal("0")

    def consolidar(self, id_usuario, ano, mes) -> m.FluxoCaixa:
        ini, fim = _periodo(ano, mes)
        trs = self.db.query(m.Transacao).filter(m.Transacao.id_usuario == id_usuario, m.Transacao.data >= ini, m.Transacao.data < fim).all()
        dom = FluxoDominio(self._saldo_anterior(id_usuario, ano, mes))
        for t in trs:
            dom.adicionar(criar_transacao(t.tipo, t.valor, t.data, t.descricao, t.ligada_atividade))
        f = self.db.query(m.FluxoCaixa).filter_by(id_usuario=id_usuario, ano=ano, mes=mes).first() or m.FluxoCaixa(id_usuario=id_usuario, ano=ano, mes=mes)
        f.saldo_inicial, f.total_entradas, f.total_saidas, f.saldo_final = dom.saldo_inicial, dom.total_entradas, dom.total_saidas, dom.saldo_final
        self.db.add(f)
        self.db.flush()
        return f

    def reconsolidar(self, id_usuario, ano, mes) -> None:
        existentes = self.db.query(m.FluxoCaixa.ano, m.FluxoCaixa.mes).filter_by(id_usuario=id_usuario).all()
        periodos = sorted({(a, mm) for a, mm in existentes if (a, mm) >= (ano, mes)} | {(ano, mes)})
        for a, mm in periodos:
            self.consolidar(id_usuario, a, mm)
        self.db.commit()

    def historico(self, id_usuario) -> list[m.FluxoCaixa]:
        return self.db.query(m.FluxoCaixa).filter_by(id_usuario=id_usuario).order_by(m.FluxoCaixa.ano, m.FluxoCaixa.mes).all()


class ServicoTransacoes:
    def __init__(self, db: Session):
        self.db = db

    def _validar(self, usuario, d):
        conta = dono(self.db, m.Conta, d.id_conta, usuario, "Conta")
        cat = dono(self.db, m.Categoria, d.id_categoria, usuario, "Categoria")
        if cat.tipo != d.tipo:
            raise RegraNegocio("A categoria escolhida é de outro tipo (entrada/saída).", 422)
        criar_transacao(d.tipo, d.valor, d.data, d.descricao, d.ligada_atividade)  # valida as regras de domínio (RN15)
        return conta

    def _efeitos(self, t: m.Transacao, sinal: int):
        conta = self.db.get(m.Conta, t.id_conta)
        delta = D(t.valor) * (1 if t.tipo == "ENTRADA" else -1) * sinal
        conta.saldo = q(D(conta.saldo) + delta)
        if sinal == -1:
            self.db.query(m.FaturamentoMei).filter_by(id_transacao=t.id_transacao).delete()
        elif t.tipo == "ENTRADA" and t.ligada_atividade:
            self.db.add(m.FaturamentoMei(id_usuario=t.id_usuario, id_transacao=t.id_transacao, ano=t.data.year, data=t.data, valor=t.valor))

    def criar(self, usuario, d) -> m.Transacao:
        self._validar(usuario, d)
        t = m.Transacao(id_usuario=usuario.id_usuario, **d.model_dump())
        self.db.add(t)
        self.db.flush()
        self._efeitos(t, +1)
        self.db.commit()
        ServicoFluxoCaixa(self.db).reconsolidar(usuario.id_usuario, t.data.year, t.data.month)
        return t

    def atualizar(self, usuario, id_, d) -> m.Transacao:
        t = dono(self.db, m.Transacao, id_, usuario, "Transação")
        self._validar(usuario, d)
        antigo = (t.data.year, t.data.month)
        self._efeitos(t, -1)
        for k, v in d.model_dump().items():
            setattr(t, k, v)
        self.db.flush()
        self._efeitos(t, +1)
        self.db.commit()
        for a, mm in sorted({antigo, (t.data.year, t.data.month)}):
            ServicoFluxoCaixa(self.db).reconsolidar(usuario.id_usuario, a, mm)
        return t

    def remover(self, usuario, id_) -> None:
        t = dono(self.db, m.Transacao, id_, usuario, "Transação")
        a, mm = t.data.year, t.data.month
        self._efeitos(t, -1)
        self.db.delete(t)
        self.db.commit()
        ServicoFluxoCaixa(self.db).reconsolidar(usuario.id_usuario, a, mm)

    def listar(self, usuario, ano=None, mes=None, tipo=None):
        q_ = self.db.query(m.Transacao).filter_by(id_usuario=usuario.id_usuario)
        if ano and mes:
            ini, fim = _periodo(ano, mes)
            q_ = q_.filter(m.Transacao.data >= ini, m.Transacao.data < fim)
        if tipo:
            q_ = q_.filter_by(tipo=tipo)
        return q_.order_by(m.Transacao.data.desc(), m.Transacao.id_transacao.desc()).all()

    def pelo_chatbot(self, usuario, dados):
        tipo, valor, descricao = interpretar(dados.mensagem)
        conta = dono(self.db, m.Conta, dados.id_conta, usuario, "Conta") if dados.id_conta else self.db.query(m.Conta).filter_by(id_usuario=usuario.id_usuario).first()
        if conta is None:
            raise RegraNegocio("Cadastre uma conta antes de lançar transações.", 422)
        if dados.id_categoria:
            cat = dono(self.db, m.Categoria, dados.id_categoria, usuario, "Categoria")
        else:
            cat = self.db.query(m.Categoria).filter_by(id_usuario=usuario.id_usuario, tipo=tipo).first()
            if cat is None:
                cat = m.Categoria(id_usuario=usuario.id_usuario, nome="Chatbot", tipo=tipo)
                self.db.add(cat)
                self.db.flush()
        from .schemas import TransacaoIn
        return self.criar(usuario, TransacaoIn(id_conta=conta.id_conta, id_categoria=cat.id_categoria, descricao=descricao, valor=valor, data=date.today(), tipo=tipo))


# -------------------------------------------------------------- impostos e teto
class ServicoImposto:
    def __init__(self, db: Session):
        self.db = db
        self.tabela = RepositorioTabelaDAS(db)

    def composicao(self, usuario, ano) -> tuple[ComposicaoDAS, m.DadosMei]:
        mei = ServicoMei(self.db).exigir(usuario)
        p = self.tabela.parametros(ano)
        return calcular_das(p, mei.tipo_atividade, mei.categoria == "CAMINHONEIRO"), mei

    def _imposto(self, usuario, nome, periodicidade, valor) -> m.Imposto:
        i = self.db.query(m.Imposto).filter_by(id_usuario=usuario.id_usuario, nome=nome).first()
        if i is None:
            i = m.Imposto(id_usuario=usuario.id_usuario, nome=nome, periodicidade=periodicidade, valor_estimado=valor, descricao=f"{nome} do MEI")
            self.db.add(i)
        i.valor_estimado = valor
        self.db.flush()
        return i

    def gerar_obrigacoes(self, usuario, ano) -> int:
        comp, _ = self.composicao(usuario, ano)
        das = self._imposto(usuario, "DAS", "MENSAL", comp.total)
        dasn = self._imposto(usuario, "DASN-SIMEI", "ANUAL", 0)
        criadas = 0
        itens = [(das, f"DAS {mes:02d}/{ano}", date(ano + (1 if mes == 12 else 0), mes % 12 + 1, 20), comp.total) for mes in range(1, 13)]
        itens.append((dasn, f"DASN-SIMEI {ano}", date(ano + 1, 5, 31), Decimal("0")))
        for imp, desc, venc, valor in itens:
            if not self.db.query(m.ObrigacaoImposto).filter_by(id_usuario=usuario.id_usuario, descricao=desc).first():
                self.db.add(m.ObrigacaoImposto(id_usuario=usuario.id_usuario, id_imposto=imp.id_imposto, descricao=desc, valor=valor, data_vencimento=venc))
                criadas += 1
        self.db.commit()
        return criadas

    def atualizar_atrasos(self, usuario, hoje: date) -> None:
        for o in self.db.query(m.ObrigacaoImposto).filter_by(id_usuario=usuario.id_usuario, status="PENDENTE").all():
            if o.data_vencimento < hoje:
                o.status = "ATRASADO"
        self.db.commit()

    def pagar(self, usuario, id_obrigacao) -> m.ObrigacaoImposto:
        o = dono(self.db, m.ObrigacaoImposto, id_obrigacao, usuario, "Obrigação")
        o.status = "PAGO"
        self.db.commit()
        return o

    def cota_mensal(self, usuario, ano, mes, hoje: date) -> dict:
        """Reserva fixa do DAS (RN01): idempotente, não soma de novo a cada chamada."""
        comp, mei = self.composicao(usuario, ano)
        self.gerar_obrigacoes(usuario, ano)
        self.atualizar_atrasos(usuario, hoje)
        imposto = self._imposto(usuario, "DAS", "MENSAL", comp.total)
        limite = hoje + timedelta(days=31)
        a_reservar = (self.db.query(func.coalesce(func.sum(m.ObrigacaoImposto.valor), 0))
                      .filter(m.ObrigacaoImposto.id_usuario == usuario.id_usuario, m.ObrigacaoImposto.id_imposto == imposto.id_imposto,
                              m.ObrigacaoImposto.status != "PAGO", m.ObrigacaoImposto.data_vencimento <= limite).scalar())
        fluxo = ServicoFluxoCaixa(self.db).consolidar(usuario.id_usuario, ano, mes)
        entradas = D(fluxo.total_entradas)
        reserva = self.db.query(m.ReservaImposto).filter_by(id_usuario=usuario.id_usuario, id_imposto=imposto.id_imposto).first() \
            or m.ReservaImposto(id_usuario=usuario.id_usuario, id_imposto=imposto.id_imposto)
        reserva.valor_reservado = q(a_reservar)
        reserva.percentual_reserva = q(reserva.valor_reservado / entradas * 100) if entradas > 0 else Decimal("0.00")
        reserva.status = "ATIVA"
        reserva.data_atualizacao = m.agora()
        self.db.add(reserva)
        self.db.commit()
        return {"ano": ano, "mes": mes, "das_total": comp.total, "esferas": {k: {"tributo": v["tributo"], "valor": v["valor"]} for k, v in comp.esferas().items()},
                "valor_reservado": reserva.valor_reservado, "faturamento_mes": q(entradas),
                "faturamento_liquido": q(max(Decimal("0"), entradas - comp.total)), "percentual_comprometido": reserva.percentual_reserva,
                "fonte": self.tabela.parametros(ano).fonte}


class ServicoTeto:
    def __init__(self, db: Session):
        self.db = db

    def status(self, usuario, ano: int) -> dict:
        mei = ServicoMei(self.db).exigir(usuario)
        p = RepositorioTabelaDAS(self.db).parametros(ano)
        teto = p.teto(mei.categoria == "CAMINHONEIRO")
        proporcional = mei.data_abertura.year == ano
        if proporcional:
            teto = teto_proporcional(teto, mei.data_abertura.month)
        cfg = self.db.query(m.ConfiguracaoMei).filter_by(id_usuario=usuario.id_usuario, ano=ano).first()
        if cfg is None:
            cfg = m.ConfiguracaoMei(id_usuario=usuario.id_usuario, ano=ano, teto_anual=teto, percentual_alerta=self._alerta_padrao())
            self.db.add(cfg)
        cfg.teto_anual = teto
        self.db.commit()
        acumulado = self.db.query(func.coalesce(func.sum(m.FaturamentoMei.valor), 0)).filter_by(id_usuario=usuario.id_usuario, ano=ano).scalar()
        s: StatusTeto = avaliar_teto(acumulado, teto, cfg.percentual_alerta)
        return {"ano": ano, "teto": s.teto, "acumulado": s.acumulado, "percentual": s.percentual, "restante": s.restante, "nivel": s.nivel,
                "mensagem": s.mensagem, "percentual_alerta": q(cfg.percentual_alerta), "teto_proporcional": proporcional}

    def _alerta_padrao(self):
        c = self.db.get(m.ConfiguracaoSistema, "percentual_alerta_padrao")
        return D(c.valor) if c else Decimal("80")

    def definir_alerta(self, usuario, ano, percentual):
        self.status(usuario, ano)
        cfg = self.db.query(m.ConfiguracaoMei).filter_by(id_usuario=usuario.id_usuario, ano=ano).first()
        cfg.percentual_alerta = percentual
        self.db.commit()


# ---------------------------------------------------------------- suavização
class ServicoFechamentoMensal:
    def __init__(self, db: Session):
        self.db = db

    def simular(self, d) -> dict:
        r = ServicoSuavizacao().fechar_mes(d.resultado_mes, d.salario_desejado, ReservaDominio(d.saldo_reserva))
        return r.__dict__

    def fechar(self, usuario, ano, mes, desejado) -> dict:
        existente = self.db.query(m.RetiradaMensal).filter_by(id_usuario=usuario.id_usuario, ano=ano, mes=mes).first()
        if existente and existente.status == "REALIZADA":
            raise RegraNegocio(f"O mês {mes:02d}/{ano} já foi fechado.", 409)
        comp, _ = ServicoImposto(self.db).composicao(usuario, ano)
        fluxo = ServicoFluxoCaixa(self.db).consolidar(usuario.id_usuario, ano, mes)
        resultado = q(D(fluxo.total_entradas) - D(fluxo.total_saidas) - comp.total)  # receita - despesas - DAS
        reserva = RepositorioReserva(self.db).obter_ou_criar(usuario.id_usuario)
        dom = ReservaDominio(reserva.saldo)
        r = ServicoSuavizacao().fechar_mes(resultado, desejado, dom, f"{mes:02d}/{ano}")
        reserva.saldo = dom.saldo
        reserva.data_atualizacao = m.agora()
        for mov in dom.movimentos:
            self.db.add(m.MovimentoReserva(id_reserva=reserva.id_reserva, id_usuario=usuario.id_usuario, ano=ano, mes=mes,
                                           tipo=mov.tipo, valor=mov.valor, saldo_apos=mov.saldo_apos, descricao=mov.descricao))
        ret = existente or m.RetiradaMensal(id_usuario=usuario.id_usuario, ano=ano, mes=mes)
        ret.valor_desejado, ret.valor, ret.status = q(desejado), r.retirada, "REALIZADA"
        self.db.add(ret)
        self.db.commit()
        out = r.__dict__.copy()
        out.update({"ano": ano, "mes": mes, "entradas": q(fluxo.total_entradas), "saidas": q(fluxo.total_saidas), "das": comp.total})
        return out


# ------------------------------------------------------------ clientes e faturas
class ServicoFaturas:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, usuario, d) -> m.Fatura:
        cliente = dono(self.db, m.Cliente, d.id_cliente, usuario, "Cliente")
        if cliente.bloqueado:
            raise RegraNegocio("Cliente bloqueado por inadimplência recorrente (RN13).", 409)
        if d.data_vencimento < d.data_emissao:
            raise RegraNegocio("O vencimento não pode ser anterior à emissão.", 422)
        if self.db.query(m.Fatura).filter_by(id_cliente=d.id_cliente, valor=d.valor, data_emissao=d.data_emissao).first():
            raise RegraNegocio("Fatura duplicada: mesmo cliente, valor e data (RN16).", 409)
        f = m.Fatura(id_usuario=usuario.id_usuario, id_cliente=d.id_cliente, descricao=d.descricao, valor=d.valor, data_emissao=d.data_emissao,
                     data_vencimento=d.data_vencimento, nota_solicitada=d.nota_solicitada,
                     nota_obrigatoria=regras_fatura.nota_obrigatoria(cliente.tipo_pessoa, d.nota_solicitada),
                     status=regras_fatura.status_por_vencimento("PENDENTE", d.data_vencimento, date.today()))
        self.db.add(f)
        self.db.commit()
        return f

    def atualizar_status(self, usuario_id: int | None, hoje: date) -> dict:
        q_ = self.db.query(m.Fatura)
        if usuario_id:
            q_ = q_.filter_by(id_usuario=usuario_id)
        atualizadas = 0
        for f in q_.all():
            novo = regras_fatura.status_por_vencimento(f.status, f.data_vencimento, hoje)
            if novo != f.status:
                f.status, atualizadas = novo, atualizadas + 1
        self.db.flush()
        bloqueados = 0
        cq = self.db.query(m.Cliente)
        if usuario_id:
            cq = cq.filter_by(id_usuario=usuario_id)
        for c in cq.all():
            n = self.db.query(m.Fatura).filter_by(id_cliente=c.id_cliente, status="ATRASADA").count()
            if regras_fatura.deve_bloquear(n) and not c.bloqueado:
                c.bloqueado, bloqueados = True, bloqueados + 1
        self.db.commit()
        return {"faturas_atualizadas": atualizadas, "clientes_bloqueados": bloqueados}

    def pagar(self, usuario, id_fatura, d) -> m.Fatura:
        f = dono(self.db, m.Fatura, id_fatura, usuario, "Fatura")
        if f.status == "PAGA":
            raise RegraNegocio("Esta fatura já está paga.", 409)
        f.status, f.data_pagamento = "PAGA", d.data_pagamento or date.today()
        self.db.commit()
        if d.id_conta and d.id_categoria:
            from .schemas import TransacaoIn
            ServicoTransacoes(self.db).criar(usuario, TransacaoIn(id_conta=d.id_conta, id_categoria=d.id_categoria, descricao=f"Fatura: {f.descricao}",
                                                                 valor=f.valor, data=f.data_pagamento, tipo="ENTRADA"))
        return f

    def emitir_nota(self, usuario, id_fatura) -> m.Fatura:
        f = dono(self.db, m.Fatura, id_fatura, usuario, "Fatura")
        f.nota_emitida = True
        self.db.commit()
        return f


# -------------------------------------------------------------- notificações
class ServicoNotificacoes:
    def __init__(self, db: Session):
        self.db = db

    def gerar(self, usuario, hoje: date) -> list[m.Notificacao]:
        pref = self.db.get(m.PreferenciasUsuario, usuario.id_usuario)
        prefs = {"das": True, "dasn": True, "saldo": True, "teto": True, "fatura": True}
        minimo = Decimal("100")
        if pref:
            prefs = {"das": pref.notif_das, "dasn": pref.notif_dasn, "saldo": pref.notif_saldo, "teto": pref.notif_teto, "fatura": pref.notif_fatura}
            minimo = D(pref.saldo_minimo)
        ServicoFaturas(self.db).atualizar_status(usuario.id_usuario, hoje)
        ServicoImposto(self.db).atualizar_atrasos(usuario, hoje)
        saldo = D(self.db.query(func.coalesce(func.sum(m.Conta.saldo), 0)).filter_by(id_usuario=usuario.id_usuario).scalar())
        obrig = [(o.descricao, o.data_vencimento, o.status) for o in self.db.query(m.ObrigacaoImposto).filter_by(id_usuario=usuario.id_usuario).all()]
        atrasadas = [(f.id_fatura, f.descricao) for f in self.db.query(m.Fatura).filter_by(id_usuario=usuario.id_usuario, status="ATRASADA").all()]
        status_teto = None
        try:
            s = ServicoTeto(self.db).status(usuario, hoje.year)
            status_teto = avaliar_teto(s["acumulado"], s["teto"], s["percentual_alerta"])
        except RegraNegocio:
            pass
        novas = []
        for n in gerar_notificacoes(hoje, saldo, minimo, obrig, atrasadas, status_teto, prefs):
            if not self.db.query(m.Notificacao).filter_by(id_usuario=usuario.id_usuario, chave=n.chave).first():
                row = m.Notificacao(id_usuario=usuario.id_usuario, chave=n.chave, tipo=n.tipo, mensagem=n.mensagem)
                self.db.add(row)
                novas.append(row)
        self.db.commit()
        return novas


# ---------------------------------------------------------------- precificação
class ServicoPrecificacao:
    def __init__(self, db: Session):
        self.db = db

    def calcular(self, usuario, d, ano: int) -> dict:
        servico = dono(self.db, m.Servico, d.id_servico, usuario, "Serviço")
        comp, _ = ServicoImposto(self.db).composicao(usuario, ano)
        r = calcular_preco_minimo(servico.horas_trabalho, d.custo_hora, servico.custo_materiais, servico.outros_custos, d.margem_lucro, comp.total, d.servicos_por_mes)
        p = self.db.query(m.Precificacao).filter_by(id_servico=servico.id_servico).first() or m.Precificacao(id_servico=servico.id_servico)
        p.margem_lucro, p.custo_hora, p.servicos_por_mes, p.valor_custo, p.valor_sugerido = d.margem_lucro, d.custo_hora, d.servicos_por_mes, r.ponto_equilibrio, r.preco_minimo
        self.db.add(p)
        self.db.commit()
        return {"id_servico": servico.id_servico, "das_mensal": comp.total, **r.__dict__}


# ------------------------------------------------------------------ investimentos
RECOMENDACOES = {
    "CONSERVADOR": ("Tesouro Selic e CDB com liquidez diária", "TESOURO", "Baixo", Decimal("100"), "Reserva de emergência e metas de curto prazo."),
    "MODERADO": ("CDB, LCI/LCA e fundos de renda fixa", "RENDA_FIXA", "Médio", Decimal("110"), "Equilíbrio entre segurança e rentabilidade."),
    "ARROJADO": ("Fundos multimercado e ETFs de renda variável", "RENDA_VARIAVEL", "Alto", None, "Maior risco de oscilação; só com a reserva já formada."),
}


class ServicoInvestimentos:
    def __init__(self, db: Session):
        self.db = db

    def cdi(self) -> Decimal:
        c = self.db.get(m.CotacaoCache, "CDI")
        return D(c.valor) if c else Decimal("0")

    def recomendar(self, usuario, d) -> m.PropostaInvestimento:
        nome, _tipo, risco, pct_cdi, texto = RECOMENDACOES[d.perfil_risco]
        rent = q(self.cdi() * pct_cdi / 100) if pct_cdi and self.cdi() > 0 else None
        p = m.PropostaInvestimento(id_usuario=usuario.id_usuario, nome=nome, descricao=texto + " Indicação informativa, sem compra real.",
                                   valor_sugerido=d.valor_disponivel, risco=risco, rentabilidade_estimada=rent)
        self.db.add(p)
        self.db.commit()
        return p

    def carteira(self, usuario) -> m.CarteiraInvestimentos:
        c = self.db.query(m.CarteiraInvestimentos).filter_by(id_usuario=usuario.id_usuario).first()
        if c is None:
            c = m.CarteiraInvestimentos(id_usuario=usuario.id_usuario)
            self.db.add(c)
            self.db.commit()
        return c

    def atualizar_cotacoes(self) -> bool:
        """Busca CDI e Selic no Banco Central; se falhar, mantém o cache (risco 'API indisponível')."""
        from .config import settings
        if not settings.cotacoes_online:
            return False
        try:
            import httpx
            for simbolo, desc, serie in (("CDI", "CDI (% a.a.)", 4389), ("SELIC", "Selic meta (% a.a.)", 432)):
                r = httpx.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados/ultimos/1?formato=json", timeout=5)
                r.raise_for_status()
                valor = Decimal(r.json()[0]["valor"])
                c = self.db.get(m.CotacaoCache, simbolo) or m.CotacaoCache(simbolo=simbolo, descricao=desc, valor=valor, fonte="Banco Central (SGS)")
                c.valor, c.fonte, c.atualizado_em = valor, "Banco Central (SGS)", m.agora()
                self.db.add(c)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False


# ------------------------------------------------------------------ metas
class ServicoMetas:
    def __init__(self, db: Session):
        self.db = db

    def aportar(self, usuario, id_meta, valor) -> m.MetaFinanceira:
        meta = dono(self.db, m.MetaFinanceira, id_meta, usuario, "Meta")
        if meta.status != "ATIVA":
            raise RegraNegocio("Só é possível aportar em metas ativas.", 409)
        meta.valor_atual = q(D(meta.valor_atual) + D(valor))
        if meta.valor_atual >= meta.valor_objetivo:
            meta.status = "CONCLUIDA"
        self.db.commit()
        return meta


# ------------------------------------------------------------ planos e vendas
class ServicoAssinaturas:
    def __init__(self, db: Session):
        self.db = db

    def assinar(self, usuario, nome_plano: str) -> m.Assinatura:
        plano = self.db.query(m.Plano).filter_by(nome=nome_plano, ativo=True).first()
        if plano is None:
            raise RegraNegocio("Plano indisponível.", 404)
        if self.db.query(m.Assinatura).filter_by(id_usuario=usuario.id_usuario, status="ATIVA").first():
            raise RegraNegocio("Você já possui uma assinatura ativa.", 409)
        hoje = date.today()
        a = m.Assinatura(id_usuario=usuario.id_usuario, id_plano=plano.id_plano, data_inicio=hoje, status="ATIVA")
        self.db.add(a)
        self.db.flush()
        self.db.add(m.Pagamento(id_assinatura=a.id_assinatura, valor=plano.preco_mensal, data_pagamento=hoje, status="PAGO", metodo="SIMULADO"))
        if usuario.perfil == "NORMAL":
            usuario.perfil = "PREMIUM"
        self.db.commit()
        return a

    def cancelar(self, usuario) -> m.Assinatura:
        a = self.db.query(m.Assinatura).filter_by(id_usuario=usuario.id_usuario, status="ATIVA").first()
        if a is None:
            raise RegraNegocio("Você não tem assinatura ativa.", 404)
        a.status, a.data_fim = "CANCELADA", date.today()
        if usuario.perfil == "PREMIUM":
            usuario.perfil = "NORMAL"
        self.db.commit()
        return a


    def cobrar_mensalidades(self, hoje: date) -> int:
        """Cobrança mensal simulada: gera o pagamento do mês de cada assinatura ativa (e dos meses anteriores que faltarem)."""
        criados = 0
        for a in self.db.query(m.Assinatura).filter_by(status="ATIVA").all():
            plano = self.db.get(m.Plano, a.id_plano)
            ano, mes = a.data_inicio.year, a.data_inicio.month
            while (ano, mes) <= (hoje.year, hoje.month):
                existe = (self.db.query(m.Pagamento).filter(m.Pagamento.id_assinatura == a.id_assinatura,
                          func.extract("year", m.Pagamento.data_pagamento) == ano, func.extract("month", m.Pagamento.data_pagamento) == mes).first())
                if not existe:
                    dia = min(a.data_inicio.day, 28)
                    self.db.add(m.Pagamento(id_assinatura=a.id_assinatura, valor=plano.preco_mensal, data_pagamento=date(ano, mes, dia), status="PAGO", metodo="SIMULADO"))
                    criados += 1
                ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        self.db.commit()
        return criados
