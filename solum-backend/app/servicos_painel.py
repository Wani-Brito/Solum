"""Dashboards: do MEI e do administrador (controle e vendas)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import distinct, extract, func
from sqlalchemy.orm import Session

from . import models as m
from .dominio.dinheiro import D, brl, q
from .dominio.teto import teto_proporcional
from .servicos import RepositorioTabelaDAS, ServicoFluxoCaixa, ServicoTeto, RegraNegocio


def _meses_atras(hoje: date, n: int = 6):
    out, a, mm = [], hoje.year, hoje.month
    for _ in range(n):
        out.append((a, mm))
        mm -= 1
        if mm == 0:
            a, mm = a - 1, 12
    return list(reversed(out))


def registrar_log(db: Session, admin: m.Usuario, acao: str, alvo: str | None = None) -> None:
    db.add(m.LogAdmin(id_admin=admin.id_usuario, acao=acao, alvo=alvo))
    db.commit()


class ServicoDashboardMei:
    def __init__(self, db: Session):
        self.db = db

    def resumo(self, usuario, hoje: date) -> dict:
        uid, ano, mes = usuario.id_usuario, hoje.year, hoje.month
        fluxo = ServicoFluxoCaixa(self.db).consolidar(uid, ano, mes)
        self.db.commit()
        ret = self.db.query(m.RetiradaMensal).filter_by(id_usuario=uid, ano=ano, mes=mes).first()
        reserva = self.db.query(m.ReservaEstabilizacao).filter_by(id_usuario=uid).first()
        try:
            teto = ServicoTeto(self.db).status(usuario, ano)
        except RegraNegocio:
            teto = None
        das = (self.db.query(m.ObrigacaoImposto).filter(m.ObrigacaoImposto.id_usuario == uid, m.ObrigacaoImposto.status != "PAGO",
               m.ObrigacaoImposto.descricao.like("DAS %")).order_by(m.ObrigacaoImposto.data_vencimento).first())
        serie = [{"ano": a, "mes": mm, "resultado": q(D(f.total_entradas) - D(f.total_saidas))}
                 for a, mm in _meses_atras(hoje) for f in [self.db.query(m.FluxoCaixa).filter_by(id_usuario=uid, ano=a, mes=mm).first()] if f]
        return {
            "usuario": {"nome": usuario.nome, "perfil": usuario.perfil},
            "salario_sintetico": {"valor": q(ret.valor) if ret and ret.status == "REALIZADA" else None, "desejado": q(ret.valor_desejado) if ret else None, "status": ret.status if ret else None},
            "reserva_estabilizacao": q(reserva.saldo) if reserva else Decimal("0.00"),
            "teto": teto,
            "proximo_das": {"descricao": das.descricao, "valor": q(das.valor), "vencimento": das.data_vencimento, "status": das.status} if das else None,
            "fluxo_mes": {"entradas": q(fluxo.total_entradas), "saidas": q(fluxo.total_saidas), "saldo_final": q(fluxo.saldo_final)},
            "serie_resultado": serie,
        }


class ServicoDashboardAdmin:
    def __init__(self, db: Session):
        self.db = db

    def _pct_teto(self, u: m.Usuario, ano: int):
        mei = self.db.query(m.DadosMei).filter_by(id_usuario=u.id_usuario).first()
        t = self.db.query(m.TabelaDAS).filter_by(ano=ano).first()
        if not mei or not t:
            return None
        teto = D(t.teto_caminhoneiro if mei.categoria == "CAMINHONEIRO" else t.teto_anual)
        if mei.data_abertura.year == ano:
            teto = teto_proporcional(teto, mei.data_abertura.month)
        acum = D(self.db.query(func.coalesce(func.sum(m.FaturamentoMei.valor), 0)).filter_by(id_usuario=u.id_usuario, ano=ano).scalar())
        return q(acum / teto * 100)

    def controle(self, hoje: date) -> dict:
        db, ano, mes = self.db, hoje.year, hoje.month
        comuns = db.query(m.Usuario).filter(m.Usuario.perfil != "ADMIN")
        total = comuns.count()
        cad = [{"ano": a, "mes": mm, "total": db.query(m.Usuario).filter(extract("year", m.Usuario.data_cadastro) == a, extract("month", m.Usuario.data_cadastro) == mm).count()} for a, mm in _meses_atras(hoje)]
        vol = [{"ano": a, "mes": mm, "total": q(db.query(func.coalesce(func.sum(m.Transacao.valor), 0)).filter(extract("year", m.Transacao.data) == a, extract("month", m.Transacao.data) == mm).scalar())} for a, mm in _meses_atras(hoje)]
        perto, atencao = 0, []
        for u in comuns.all():
            pct = self._pct_teto(u, ano)
            if pct is not None and pct >= 80:
                perto += 1
                if pct >= 90:
                    atencao.append({"usuario": u.nome, "motivo": "Teto", "detalhe": f"{str(pct).replace('.', ',')}% do teto anual"})
            atrasada = db.query(m.ObrigacaoImposto).filter(m.ObrigacaoImposto.id_usuario == u.id_usuario, m.ObrigacaoImposto.status != "PAGO", m.ObrigacaoImposto.data_vencimento < hoje).order_by(m.ObrigacaoImposto.data_vencimento).first()
            if atrasada:
                atencao.append({"usuario": u.nome, "motivo": "DAS atrasado", "detalhe": f"Venceu dia {atrasada.data_vencimento:%d/%m}"})
            ret = db.query(m.RetiradaMensal).filter_by(id_usuario=u.id_usuario, status="REALIZADA").order_by(m.RetiradaMensal.ano.desc(), m.RetiradaMensal.mes.desc()).first()
            if ret and D(ret.valor) < D(ret.valor_desejado):
                atencao.append({"usuario": u.nome, "motivo": "Reserva zerada", "detalhe": f"Faltou R$ {brl(D(ret.valor_desejado) - D(ret.valor))} no salário"})
        em_atraso = db.query(m.ObrigacaoImposto).filter(m.ObrigacaoImposto.status != "PAGO", m.ObrigacaoImposto.data_vencimento < hoje).count()
        sem_mei = comuns.filter(~m.Usuario.id_usuario.in_(db.query(m.DadosMei.id_usuario))).count()
        pend = []
        if hoje.month >= 10 and not RepositorioTabelaDAS(db).por_ano(ano + 1):
            pend.append({"texto": f"Tabela DAS {ano + 1} ainda não cadastrada", "nivel": "ATENCAO"})
        if not RepositorioTabelaDAS(db).por_ano(ano):
            pend.append({"texto": f"Tabela DAS {ano} não cadastrada", "nivel": "ATENCAO"})
        pend.append({"texto": "Usuários sem atividade do MEI informada", "nivel": "INFO", "quantidade": sem_mei})
        t = RepositorioTabelaDAS(db).por_ano(ano)
        if t:
            pend.append({"texto": "Última atualização da Tabela DAS", "nivel": "OK", "data": t.data_atualizacao})
        logs = db.query(m.LogAdmin, m.Usuario.nome).join(m.Usuario, m.Usuario.id_usuario == m.LogAdmin.id_admin).order_by(m.LogAdmin.data_hora.desc()).limit(5).all()
        return {
            "usuarios": total,
            "novos_no_mes": comuns.filter(extract("year", m.Usuario.data_cadastro) == ano, extract("month", m.Usuario.data_cadastro) == mes).count(),
            "transacoes_no_mes": db.query(m.Transacao).filter(extract("year", m.Transacao.data) == ano, extract("month", m.Transacao.data) == mes).count(),
            "perto_do_teto": perto, "obrigacoes_em_atraso": em_atraso,
            "cadastros_por_mes": cad, "volume_por_mes": vol,
            "perfis": {p: db.query(m.Usuario).filter_by(perfil=p).count() for p in ("NORMAL", "PREMIUM", "ADMIN")},
            "saude": {"api": "online", "versao": "1.0", "verificado_em": datetime.now().isoformat(timespec="seconds")},
            "atencao": atencao[:5], "pendencias": pend,
            "atividade_recente": [{"admin": nome, "acao": lg.acao, "alvo": lg.alvo, "data_hora": lg.data_hora} for lg, nome in logs],
        }

    def vendas(self, hoje: date) -> dict:
        db, ano, mes = self.db, hoje.year, hoje.month
        def receita(a, mm):
            return q(db.query(func.coalesce(func.sum(m.Pagamento.valor), 0)).filter(m.Pagamento.status == "PAGO", extract("year", m.Pagamento.data_pagamento) == a, extract("month", m.Pagamento.data_pagamento) == mm).scalar())
        comuns = db.query(m.Usuario).filter(m.Usuario.perfil != "ADMIN").count()
        assinantes = db.query(m.Assinatura).filter_by(status="ATIVA").count()
        cancel = db.query(m.Assinatura).filter(m.Assinatura.status == "CANCELADA", extract("year", m.Assinatura.data_fim) == ano, extract("month", m.Assinatura.data_fim) == mes).count()
        usaram = db.query(func.count(distinct(m.Transacao.id_usuario))).filter(extract("year", m.Transacao.data) == ano, extract("month", m.Transacao.data) == mes).scalar()
        ultimas = (db.query(m.Assinatura, m.Usuario.nome, m.Plano.nome, m.Plano.preco_mensal).join(m.Usuario, m.Usuario.id_usuario == m.Assinatura.id_usuario)
                   .join(m.Plano, m.Plano.id_plano == m.Assinatura.id_plano).order_by(m.Assinatura.data_inicio.desc(), m.Assinatura.id_assinatura.desc()).limit(5).all())
        return {
            "receita_mes": receita(ano, mes), "assinantes_premium": assinantes,
            "conversao_percentual": q(Decimal(assinantes) / comuns * 100) if comuns else Decimal("0.00"),
            "cancelamentos_mes": cancel,
            "receita_por_mes": [{"ano": a, "mes": mm, "total": receita(a, mm)} for a, mm in _meses_atras(hoje)],
            "funil": {"cadastrados": comuns, "cadastraram_mei": db.query(m.DadosMei).count(), "usaram_no_mes": usaram, "assinaram_premium": assinantes},
            "ultimas_assinaturas": [{"usuario": u, "plano": p, "valor": q(v), "data": a.data_inicio, "status": a.status} for a, u, p, v in ultimas],
        }
