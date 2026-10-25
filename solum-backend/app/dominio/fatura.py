"""Regras de faturas e cobrança (RN10 a RN13, RN16)."""
from datetime import date

PENDENTE, PAGA, ATRASADA = "PENDENTE", "PAGA", "ATRASADA"
LIMITE_INADIMPLENCIA = 3  # RN13: cliente com 3 ou mais faturas atrasadas é bloqueado


def status_por_vencimento(status_atual: str, vencimento: date, hoje: date) -> str:
    """RN10: o status muda sozinho conforme o vencimento. Fatura paga nunca volta atrás."""
    if status_atual == PAGA:
        return PAGA
    return ATRASADA if vencimento < hoje else PENDENTE


def nota_obrigatoria(tipo_pessoa: str, solicitada: bool = False) -> bool:
    """RN11: NF obrigatória para pessoa jurídica e sob solicitação para pessoa física."""
    return tipo_pessoa == "PJ" or bool(solicitada)


def deve_bloquear(qtd_atrasadas: int) -> bool:
    return qtd_atrasadas >= LIMITE_INADIMPLENCIA
