"""Utilitários de dinheiro: sempre Decimal, sempre 2 casas (nunca float)."""
from decimal import ROUND_HALF_UP, Decimal


def D(valor) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def q(valor) -> Decimal:
    return D(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def brl(valor) -> str:
    """1234.5 -> '1.234,50' (formato brasileiro, para mensagens ao usuário)."""
    return f"{q(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
