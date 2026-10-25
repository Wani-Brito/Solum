"""Modelos SQLAlchemy = tabelas do PostgreSQL (ver schema.sql, gerado a partir daqui)."""
from datetime import datetime, timezone

from sqlalchemy import (Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey,
                        Index, Integer, Numeric, String, Text, UniqueConstraint)
from sqlalchemy.orm import declarative_base

Base = declarative_base()
Dinheiro = Numeric(12, 2)


def agora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _in(coluna, valores):
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"



class Usuario(Base):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False, unique=True)
    senha = Column(String(255), nullable=False)  # hash bcrypt
    telefone = Column(String(20))
    perfil = Column(String(10), nullable=False, default="NORMAL")
    ativo = Column(Boolean, nullable=False, default=True)
    data_cadastro = Column(DateTime, nullable=False, default=agora)
    __table_args__ = (CheckConstraint(_in("perfil", ["NORMAL", "PREMIUM", "ADMIN"]), name="ck_usuarios_perfil"),)


class PreferenciasUsuario(Base):
    __tablename__ = "preferencias_usuario"
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), primary_key=True)
    tema = Column(String(10), nullable=False, default="ESCURO")
    notif_das = Column(Boolean, nullable=False, default=True)
    notif_dasn = Column(Boolean, nullable=False, default=True)
    notif_saldo = Column(Boolean, nullable=False, default=True)
    notif_teto = Column(Boolean, nullable=False, default=True)
    notif_fatura = Column(Boolean, nullable=False, default=True)
    saldo_minimo = Column(Dinheiro, nullable=False, default=100)
    __table_args__ = (CheckConstraint(_in("tema", ["ESCURO", "CLARO", "SISTEMA"]), name="ck_pref_tema"),)


class DadosMei(Base):
    __tablename__ = "dados_mei"
    id_dados = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, unique=True)
    cnpj = Column(String(18))
    nome_fantasia = Column(String(100))
    tipo_atividade = Column(String(10), nullable=False)
    categoria = Column(String(15), nullable=False, default="PADRAO")
    cnae = Column(String(10), nullable=False)
    data_abertura = Column(Date, nullable=False)
    cidade = Column(String(80))
    uf = Column(String(2))
    __table_args__ = (
        CheckConstraint(_in("tipo_atividade", ["COMERCIO", "SERVICO", "AMBOS"]), name="ck_mei_atividade"),
        CheckConstraint(_in("categoria", ["PADRAO", "CAMINHONEIRO"]), name="ck_mei_categoria"),
    )


class CnaeMei(Base):
    __tablename__ = "cnaes_mei"
    cnae = Column(String(10), primary_key=True)
    descricao = Column(String(200), nullable=False)
    tipo_atividade = Column(String(10), nullable=False, default="SERVICO")


class TabelaDAS(Base):
    __tablename__ = "tabela_das"
    id_tabela = Column(Integer, primary_key=True)
    ano = Column(Integer, nullable=False, unique=True)
    salario_minimo = Column(Dinheiro, nullable=False)
    perc_inss = Column(Numeric(5, 2), nullable=False, default=5)
    perc_inss_caminhoneiro = Column(Numeric(5, 2), nullable=False, default=12)
    valor_icms = Column(Dinheiro, nullable=False, default=1)
    valor_iss = Column(Dinheiro, nullable=False, default=5)
    teto_anual = Column(Dinheiro, nullable=False)
    teto_caminhoneiro = Column(Dinheiro, nullable=False)
    fonte = Column(String(200), nullable=False)
    data_atualizacao = Column(DateTime, nullable=False, default=agora)
    __table_args__ = (CheckConstraint("salario_minimo > 0 AND teto_anual > 0", name="ck_das_positivos"),)


class Conta(Base):
    __tablename__ = "contas"
    id_conta = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    nome = Column(String(60), nullable=False)
    banco = Column(String(60))
    saldo = Column(Dinheiro, nullable=False, default=0)


class Categoria(Base):
    __tablename__ = "categorias"
    id_categoria = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    nome = Column(String(60), nullable=False)
    tipo = Column(String(10), nullable=False)
    __table_args__ = (CheckConstraint(_in("tipo", ["ENTRADA", "SAIDA"]), name="ck_categoria_tipo"),
                      UniqueConstraint("id_usuario", "nome", "tipo", name="uq_categoria"))


class Transacao(Base):
    __tablename__ = "transacoes"
    id_transacao = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_conta = Column(Integer, ForeignKey("contas.id_conta"), nullable=False)
    id_categoria = Column(Integer, ForeignKey("categorias.id_categoria"), nullable=False)
    descricao = Column(String(150), nullable=False)
    valor = Column(Dinheiro, nullable=False)
    data = Column(Date, nullable=False)
    tipo = Column(String(10), nullable=False)
    ligada_atividade = Column(Boolean, nullable=False, default=True)
    __table_args__ = (CheckConstraint("valor > 0", name="ck_transacao_valor"),
                      CheckConstraint(_in("tipo", ["ENTRADA", "SAIDA"]), name="ck_transacao_tipo"),
                      Index("ix_transacoes_usuario_data", "id_usuario", "data"))


class FluxoCaixa(Base):
    __tablename__ = "fluxos_caixa"
    id_fluxo_caixa = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    saldo_inicial = Column(Dinheiro, nullable=False, default=0)
    total_entradas = Column(Dinheiro, nullable=False, default=0)
    total_saidas = Column(Dinheiro, nullable=False, default=0)
    saldo_final = Column(Dinheiro, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("id_usuario", "ano", "mes", name="uq_fluxo_periodo"),
                      CheckConstraint("mes BETWEEN 1 AND 12", name="ck_fluxo_mes"))


class RetiradaMensal(Base):
    __tablename__ = "retiradas_mensais"
    id_retirada = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    valor_desejado = Column(Dinheiro, nullable=False)
    valor = Column(Dinheiro, nullable=False, default=0)
    status = Column(String(12), nullable=False, default="PLANEJADA")
    __table_args__ = (UniqueConstraint("id_usuario", "ano", "mes", name="uq_retirada_periodo"),
                      CheckConstraint(_in("status", ["PLANEJADA", "REALIZADA", "CANCELADA"]), name="ck_retirada_status"))


class ReservaEstabilizacao(Base):
    __tablename__ = "reservas_estabilizacao"
    id_reserva = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, unique=True)
    saldo = Column(Dinheiro, nullable=False, default=0)
    data_atualizacao = Column(DateTime, nullable=False, default=agora)
    __table_args__ = (CheckConstraint("saldo >= 0", name="ck_reserva_saldo"),)


class MovimentoReserva(Base):
    """Log auditável de toda movimentação da reserva (RN09.3)."""
    __tablename__ = "movimentos_reserva"
    id_movimento = Column(Integer, primary_key=True)
    id_reserva = Column(Integer, ForeignKey("reservas_estabilizacao.id_reserva", ondelete="CASCADE"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    tipo = Column(String(10), nullable=False)
    valor = Column(Dinheiro, nullable=False)
    saldo_apos = Column(Dinheiro, nullable=False)
    descricao = Column(String(150), nullable=False)
    data_hora = Column(DateTime, nullable=False, default=agora)
    __table_args__ = (CheckConstraint(_in("tipo", ["APORTE", "RETIRADA"]), name="ck_mov_tipo"),
                      CheckConstraint("valor > 0", name="ck_mov_valor"))


class ConfiguracaoMei(Base):
    __tablename__ = "configuracoes_mei"
    id_configuracao = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    ano = Column(Integer, nullable=False)
    teto_anual = Column(Dinheiro, nullable=False)
    percentual_alerta = Column(Numeric(5, 2), nullable=False, default=80)
    __table_args__ = (UniqueConstraint("id_usuario", "ano", name="uq_config_mei"),
                      CheckConstraint("percentual_alerta > 0 AND percentual_alerta <= 100", name="ck_config_alerta"))


class FaturamentoMei(Base):
    __tablename__ = "faturamentos_mei"
    id_faturamento = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_transacao = Column(Integer, ForeignKey("transacoes.id_transacao", ondelete="CASCADE"), unique=True)
    ano = Column(Integer, nullable=False)
    data = Column(Date, nullable=False)
    valor = Column(Dinheiro, nullable=False)
    __table_args__ = (CheckConstraint("valor > 0", name="ck_fat_valor"),)


class Imposto(Base):
    __tablename__ = "impostos"
    id_imposto = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    nome = Column(String(40), nullable=False)
    descricao = Column(Text)
    periodicidade = Column(String(10), nullable=False, default="MENSAL")
    valor_estimado = Column(Dinheiro, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("id_usuario", "nome", name="uq_imposto_usuario_nome"),)


class ReservaImposto(Base):
    __tablename__ = "reservas_imposto"
    id_reserva_imposto = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_imposto = Column(Integer, ForeignKey("impostos.id_imposto", ondelete="CASCADE"), nullable=False)
    valor_reservado = Column(Dinheiro, nullable=False, default=0)
    percentual_reserva = Column(Numeric(5, 2), nullable=False, default=0)
    status = Column(String(12), nullable=False, default="ATIVA")
    data_atualizacao = Column(DateTime, nullable=False, default=agora)
    __table_args__ = (UniqueConstraint("id_usuario", "id_imposto", name="uq_reserva_imposto"),
                      CheckConstraint(_in("status", ["ATIVA", "UTILIZADA", "FINALIZADA"]), name="ck_resimp_status"))


class ObrigacaoImposto(Base):
    __tablename__ = "obrigacoes_imposto"
    id_obrigacao = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_imposto = Column(Integer, ForeignKey("impostos.id_imposto", ondelete="CASCADE"), nullable=False)
    descricao = Column(String(80), nullable=False)
    valor = Column(Dinheiro, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    status = Column(String(10), nullable=False, default="PENDENTE")
    __table_args__ = (UniqueConstraint("id_usuario", "descricao", name="uq_obrigacao"),
                      CheckConstraint(_in("status", ["PENDENTE", "PAGO", "ATRASADO"]), name="ck_obrig_status"))


class Servico(Base):
    __tablename__ = "servicos"
    id_servico = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    horas_trabalho = Column(Numeric(7, 2), nullable=False)
    custo_materiais = Column(Dinheiro, nullable=False, default=0)
    outros_custos = Column(Dinheiro, nullable=False, default=0)
    __table_args__ = (CheckConstraint("horas_trabalho > 0", name="ck_servico_horas"),)


class Precificacao(Base):
    __tablename__ = "precificacoes"
    id_precificacao = Column(Integer, primary_key=True)
    id_servico = Column(Integer, ForeignKey("servicos.id_servico", ondelete="CASCADE"), nullable=False, unique=True)
    margem_lucro = Column(Numeric(5, 2), nullable=False)
    custo_hora = Column(Dinheiro, nullable=False)
    servicos_por_mes = Column(Integer, nullable=False, default=1)
    valor_custo = Column(Dinheiro, nullable=False)
    valor_sugerido = Column(Dinheiro, nullable=False)
    __table_args__ = (CheckConstraint("margem_lucro >= 0 AND margem_lucro < 100", name="ck_preco_margem"),)


class CarteiraInvestimentos(Base):
    __tablename__ = "carteiras_investimentos"
    id_carteira = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False, unique=True)
    nome = Column(String(80), nullable=False, default="Minha carteira")


class Investimento(Base):
    __tablename__ = "investimentos"
    id_investimento = Column(Integer, primary_key=True)
    id_carteira = Column(Integer, ForeignKey("carteiras_investimentos.id_carteira", ondelete="CASCADE"), nullable=False)
    nome = Column(String(80), nullable=False)
    tipo = Column(String(15), nullable=False)
    valor_atual = Column(Dinheiro, nullable=False)
    rentabilidade = Column(Numeric(7, 2), nullable=False, default=0)
    prazo = Column(String(30))
    data_aplicacao = Column(Date, nullable=False)
    __table_args__ = (CheckConstraint(_in("tipo", ["RENDA_FIXA", "RENDA_VARIAVEL", "FUNDOS", "TESOURO", "OUTROS"]), name="ck_inv_tipo"),
                      CheckConstraint("valor_atual > 0", name="ck_inv_valor"))


class PropostaInvestimento(Base):
    __tablename__ = "propostas_investimento"
    id_proposta = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    nome = Column(String(80), nullable=False)
    descricao = Column(Text)
    valor_sugerido = Column(Dinheiro, nullable=False)
    risco = Column(String(15), nullable=False)
    rentabilidade_estimada = Column(Numeric(7, 2))
    status = Column(String(12), nullable=False, default="DISPONIVEL")
    data_criacao = Column(DateTime, nullable=False, default=agora)
    __table_args__ = (CheckConstraint(_in("status", ["DISPONIVEL", "ACEITA", "RECUSADA"]), name="ck_prop_status"),)


class CotacaoCache(Base):
    __tablename__ = "cotacao_cache"
    simbolo = Column(String(20), primary_key=True)
    descricao = Column(String(80), nullable=False)
    valor = Column(Numeric(12, 4), nullable=False)
    fonte = Column(String(80), nullable=False)
    atualizado_em = Column(DateTime, nullable=False, default=agora)


class MetaFinanceira(Base):
    __tablename__ = "metas_financeiras"
    id_meta = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    nome = Column(String(80), nullable=False)
    descricao = Column(Text)
    valor_objetivo = Column(Dinheiro, nullable=False)
    valor_atual = Column(Dinheiro, nullable=False, default=0)
    prazo = Column(Date, nullable=False)
    status = Column(String(12), nullable=False, default="ATIVA")
    __table_args__ = (CheckConstraint("valor_objetivo > 0 AND valor_atual >= 0", name="ck_meta_valores"),
                      CheckConstraint(_in("status", ["ATIVA", "CONCLUIDA", "CANCELADA"]), name="ck_meta_status"))


class Cliente(Base):
    __tablename__ = "clientes"
    id_cliente = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    tipo_pessoa = Column(String(2), nullable=False, default="PF")
    documento = Column(String(18))
    email = Column(String(120))
    bloqueado = Column(Boolean, nullable=False, default=False)
    data_cadastro = Column(DateTime, nullable=False, default=agora)
    __table_args__ = (CheckConstraint(_in("tipo_pessoa", ["PF", "PJ"]), name="ck_cliente_tipo"),)


class Fatura(Base):
    __tablename__ = "faturas"
    id_fatura = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"), nullable=False)
    descricao = Column(String(150), nullable=False)
    valor = Column(Dinheiro, nullable=False)
    data_emissao = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    status = Column(String(10), nullable=False, default="PENDENTE")
    nota_obrigatoria = Column(Boolean, nullable=False, default=False)
    nota_solicitada = Column(Boolean, nullable=False, default=False)
    nota_emitida = Column(Boolean, nullable=False, default=False)
    data_pagamento = Column(Date)
    __table_args__ = (CheckConstraint("valor > 0", name="ck_fatura_valor"),
                      CheckConstraint(_in("status", ["PENDENTE", "PAGA", "ATRASADA"]), name="ck_fatura_status"),
                      CheckConstraint("data_vencimento >= data_emissao", name="ck_fatura_datas"),
                      UniqueConstraint("id_cliente", "valor", "data_emissao", name="uq_fatura_duplicada"))


class Notificacao(Base):
    __tablename__ = "notificacoes"
    id_notificacao = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    chave = Column(String(80), nullable=False)
    tipo = Column(String(20), nullable=False)
    mensagem = Column(String(200), nullable=False)
    lida = Column(Boolean, nullable=False, default=False)
    data_criacao = Column(DateTime, nullable=False, default=agora)
    __table_args__ = (UniqueConstraint("id_usuario", "chave", name="uq_notificacao_chave"),)


class Plano(Base):
    __tablename__ = "planos"
    id_plano = Column(Integer, primary_key=True)
    nome = Column(String(20), nullable=False, unique=True)
    preco_mensal = Column(Dinheiro, nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)
    __table_args__ = (CheckConstraint("preco_mensal >= 0", name="ck_plano_preco"),)


class Assinatura(Base):
    __tablename__ = "assinaturas"
    id_assinatura = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    id_plano = Column(Integer, ForeignKey("planos.id_plano"), nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date)
    status = Column(String(10), nullable=False, default="ATIVA")
    __table_args__ = (CheckConstraint(_in("status", ["ATIVA", "PENDENTE", "CANCELADA"]), name="ck_assin_status"),)


class Pagamento(Base):
    __tablename__ = "pagamentos"
    id_pagamento = Column(Integer, primary_key=True)
    id_assinatura = Column(Integer, ForeignKey("assinaturas.id_assinatura", ondelete="CASCADE"), nullable=False)
    valor = Column(Dinheiro, nullable=False)
    data_pagamento = Column(Date, nullable=False)
    status = Column(String(10), nullable=False, default="PAGO")
    metodo = Column(String(15), nullable=False, default="SIMULADO")
    __table_args__ = (CheckConstraint(_in("status", ["PAGO", "PENDENTE", "FALHOU"]), name="ck_pag_status"),)


class LogAdmin(Base):
    __tablename__ = "logs_admin"
    id_log = Column(Integer, primary_key=True)
    id_admin = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    acao = Column(String(120), nullable=False)
    alvo = Column(String(80))
    data_hora = Column(DateTime, nullable=False, default=agora)


class ConfiguracaoSistema(Base):
    __tablename__ = "configuracoes_sistema"
    chave = Column(String(40), primary_key=True)
    valor = Column(String(80), nullable=False)
