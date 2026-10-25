"""FluxoCaixa: compõe Transacoes (composição) e calcula entradas, saídas e saldo."""
from decimal import Decimal

from .dinheiro import D, q
from .transacao import Transacao


class FluxoCaixa:
    def __init__(self, saldo_inicial=0):
        self.saldo_inicial = q(saldo_inicial)
        self._transacoes: list[Transacao] = []

    def adicionar(self, transacao: Transacao) -> None:
        self._transacoes.append(transacao)

    @property
    def total_entradas(self) -> Decimal:
        return q(sum((t.valor for t in self._transacoes if t.tipo == "ENTRADA"), Decimal("0")))

    @property
    def total_saidas(self) -> Decimal:
        return q(sum((t.valor for t in self._transacoes if t.tipo == "SAIDA"), Decimal("0")))

    @property
    def resultado(self) -> Decimal:
        return q(self.total_entradas - self.total_saidas)

    @property
    def saldo_final(self) -> Decimal:
        return q(self.saldo_inicial + self.resultado)
