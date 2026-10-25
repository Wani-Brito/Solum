"""Reserva de estabilização. Encapsulamento: o saldo só muda por aportar() e retirar()."""
from dataclasses import dataclass
from decimal import Decimal

from .dinheiro import q


@dataclass
class Movimento:
    tipo: str  # APORTE ou RETIRADA
    valor: Decimal
    saldo_apos: Decimal
    descricao: str


class ReservaEstabilizacao:
    def __init__(self, saldo=0):
        saldo = q(saldo)
        if saldo < 0:
            raise ValueError("O saldo da reserva não pode ser negativo.")
        self._saldo = saldo
        self.movimentos: list[Movimento] = []

    @property
    def saldo(self) -> Decimal:
        return self._saldo

    def aportar(self, valor, descricao: str = "Sobra do mês") -> Movimento:
        valor = q(valor)
        if valor <= 0:
            raise ValueError("O aporte deve ser maior que zero.")
        self._saldo = q(self._saldo + valor)
        mov = Movimento("APORTE", valor, self._saldo, descricao)
        self.movimentos.append(mov)
        return mov

    def retirar(self, valor, descricao: str = "Complemento do salário") -> Movimento:
        valor = q(valor)
        if valor <= 0:
            raise ValueError("A retirada deve ser maior que zero.")
        if valor > self._saldo:  # RN08: limitada ao saldo
            raise ValueError("A retirada não pode exceder o saldo da reserva.")
        self._saldo = q(self._saldo - valor)
        mov = Movimento("RETIRADA", valor, self._saldo, descricao)
        self.movimentos.append(mov)
        return mov
