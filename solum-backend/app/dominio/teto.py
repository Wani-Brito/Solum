"""Teto de faturamento anual (RN05)."""
from dataclasses import dataclass
from decimal import Decimal

from .dinheiro import D, q


@dataclass
class StatusTeto:
    acumulado: Decimal
    teto: Decimal
    percentual: Decimal
    nivel: str  # NORMAL, ALERTA, EXCESSO_TOLERADO, DESENQUADRAMENTO
    mensagem: str
    restante: Decimal


def teto_proporcional(teto_anual, mes_abertura: int) -> Decimal:
    """No ano de abertura o teto é proporcional aos meses de atividade (inclui o mês de abertura)."""
    meses = 13 - mes_abertura
    return q(D(teto_anual) / 12 * meses)


def avaliar_teto(acumulado, teto, percentual_alerta=80) -> StatusTeto:
    acumulado, teto = q(acumulado), q(teto)
    alerta = D(percentual_alerta)
    pct = q(acumulado / teto * 100) if teto > 0 else Decimal("0.00")
    restante = q(max(Decimal("0"), teto - acumulado))
    if pct > 120:
        nivel = "DESENQUADRAMENTO"
        msg = "Excesso acima de 20% do teto: desenquadramento retroativo do MEI. Procure um contador para a migração ao Simples Nacional."
    elif pct > 100:
        nivel = "EXCESSO_TOLERADO"
        msg = "Teto ultrapassado em até 20%: você segue como MEI até o fim do ano e migra no ano seguinte."
    elif pct >= alerta:
        nivel = "ALERTA"
        msg = f"Atenção: você já usou {pct}% do teto anual."
    else:
        nivel = "NORMAL"
        msg = "Faturamento dentro do limite."
    return StatusTeto(acumulado, teto, pct, nivel, msg, restante)
