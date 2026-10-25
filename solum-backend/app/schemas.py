"""Schemas de entrada (Pydantic). Dinheiro sempre Decimal."""
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Valor = Decimal


class RegistroIn(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=72)
    telefone: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    senha: str


class PerfilIn(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    telefone: Optional[str] = None


class SenhaIn(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=6, max_length=72)


class PreferenciasIn(BaseModel):
    tema: Optional[Literal["ESCURO", "CLARO", "SISTEMA"]] = None
    notif_das: Optional[bool] = None
    notif_dasn: Optional[bool] = None
    notif_saldo: Optional[bool] = None
    notif_teto: Optional[bool] = None
    notif_fatura: Optional[bool] = None
    saldo_minimo: Optional[Decimal] = Field(default=None, ge=0)
    percentual_alerta: Optional[Decimal] = Field(default=None, gt=0, le=100)


class MeiIn(BaseModel):
    tipo_atividade: Literal["COMERCIO", "SERVICO", "AMBOS"]
    categoria: Literal["PADRAO", "CAMINHONEIRO"] = "PADRAO"
    cnae: str = Field(min_length=7, max_length=10)
    data_abertura: date
    cnpj: Optional[str] = Field(default=None, max_length=18)
    nome_fantasia: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = Field(default=None, min_length=2, max_length=2)


class ContaIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    banco: Optional[str] = None
    saldo: Decimal = Decimal("0")


class CategoriaIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    tipo: Literal["ENTRADA", "SAIDA"]


class TransacaoIn(BaseModel):
    id_conta: int
    id_categoria: int
    descricao: str = Field(min_length=1, max_length=150)
    valor: Decimal = Field(gt=0)  # RN15
    data: date
    tipo: Literal["ENTRADA", "SAIDA"]
    ligada_atividade: bool = True


class SimularIn(BaseModel):
    resultado_mes: Decimal
    saldo_reserva: Decimal = Field(ge=0)
    salario_desejado: Decimal = Field(ge=0)


class FecharMesIn(BaseModel):
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    salario_desejado: Decimal = Field(ge=0)


class ClienteIn(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    tipo_pessoa: Literal["PF", "PJ"] = "PF"
    documento: Optional[str] = None
    email: Optional[str] = None


class FaturaIn(BaseModel):
    id_cliente: int
    descricao: str = Field(min_length=1, max_length=150)
    valor: Decimal = Field(gt=0)
    data_emissao: date
    data_vencimento: date
    nota_solicitada: bool = False


class PagarFaturaIn(BaseModel):
    data_pagamento: Optional[date] = None
    id_conta: Optional[int] = None
    id_categoria: Optional[int] = None


class ServicoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    descricao: Optional[str] = None
    horas_trabalho: Decimal = Field(gt=0)
    custo_materiais: Decimal = Field(default=Decimal("0"), ge=0)
    outros_custos: Decimal = Field(default=Decimal("0"), ge=0)


class PrecificarIn(BaseModel):
    id_servico: int
    margem_lucro: Decimal = Field(ge=0, lt=100)
    custo_hora: Decimal = Field(ge=0)
    servicos_por_mes: int = Field(default=1, ge=1)


class MetaIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    descricao: Optional[str] = None
    valor_objetivo: Decimal = Field(gt=0)
    prazo: date


class AporteIn(BaseModel):
    valor: Decimal = Field(gt=0)


class AplicacaoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    tipo: Literal["RENDA_FIXA", "RENDA_VARIAVEL", "FUNDOS", "TESOURO", "OUTROS"]
    valor_atual: Decimal = Field(gt=0)
    rentabilidade: Decimal = Decimal("0")
    prazo: Optional[str] = None
    data_aplicacao: date


class RecomendacaoIn(BaseModel):
    valor_disponivel: Decimal = Field(gt=0)
    perfil_risco: Literal["CONSERVADOR", "MODERADO", "ARROJADO"]


class StatusPropostaIn(BaseModel):
    status: Literal["ACEITA", "RECUSADA"]


class ChatbotIn(BaseModel):
    mensagem: str = Field(min_length=3, max_length=300)
    id_conta: Optional[int] = None
    id_categoria: Optional[int] = None


class AssinarIn(BaseModel):
    nome_plano: Literal["PREMIUM"] = "PREMIUM"


class AdminUsuarioIn(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=72)
    perfil: Literal["NORMAL", "PREMIUM", "ADMIN"] = "NORMAL"


class AdminUsuarioPatch(BaseModel):
    perfil: Optional[Literal["NORMAL", "PREMIUM", "ADMIN"]] = None
    ativo: Optional[bool] = None


class TabelaDASIn(BaseModel):
    salario_minimo: Decimal = Field(gt=0)
    perc_inss: Decimal = Field(default=Decimal("5"), gt=0, le=100)
    perc_inss_caminhoneiro: Decimal = Field(default=Decimal("12"), gt=0, le=100)
    valor_icms: Decimal = Field(default=Decimal("1"), ge=0)
    valor_iss: Decimal = Field(default=Decimal("5"), ge=0)
    teto_anual: Decimal = Field(gt=0)
    teto_caminhoneiro: Decimal = Field(gt=0)
    fonte: str = Field(min_length=3, max_length=200)


class ConfigSistemaIn(BaseModel):
    percentual_alerta_padrao: Decimal = Field(gt=0, le=100)
    dias_aviso_das: int = Field(ge=1, le=30)
    dias_aviso_dasn: int = Field(ge=1, le=90)


class CnaeIn(BaseModel):
    cnae: str = Field(min_length=7, max_length=10)
    descricao: str
    tipo_atividade: Literal["COMERCIO", "SERVICO", "AMBOS"] = "SERVICO"


class PlanejarRetiradaIn(BaseModel):
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    valor_desejado: Decimal = Field(ge=0)
