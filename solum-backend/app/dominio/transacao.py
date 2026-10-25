"""Hierarquia de transações (herança): Entrada e Saida. Só Entrada conta para o teto."""
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from .dinheiro import D, q


class Transacao(ABC):
    def __init__(self, valor, data: date, descricao: str = "", ligada_atividade: bool = True):
        valor = q(valor)
        if valor <= 0:  # RN15
            raise ValueError("O valor deve ser maior que zero (RN15).")
        self._valor = valor
        self.data = data
        self.descricao = descricao
        self.ligada_atividade = ligada_atividade

    @property
    def valor(self) -> Decimal:
        return self._valor

    @property
    @abstractmethod
    def tipo(self) -> str: ...

    @abstractmethod
    def valor_assinado(self) -> Decimal: ...

    @property
    @abstractmethod
    def conta_para_teto(self) -> bool: ...


class Entrada(Transacao):
    tipo = "ENTRADA"

    def valor_assinado(self) -> Decimal:
        return self._valor

    @property
    def conta_para_teto(self) -> bool:
        # receitas do negócio e Pix pessoal ligado à atividade (proposta, seção 7)
        return self.ligada_atividade


class Saida(Transacao):
    tipo = "SAIDA"

    def valor_assinado(self) -> Decimal:
        return -self._valor

    @property
    def conta_para_teto(self) -> bool:
        return False


def criar_transacao(tipo: str, valor, data: date, descricao: str = "", ligada_atividade: bool = True) -> Transacao:
    """Factory: cria Entrada ou Saida a partir do texto do tipo."""
    classes = {"ENTRADA": Entrada, "SAIDA": Saida}
    if tipo not in classes:
        raise ValueError("Tipo da transação deve ser ENTRADA ou SAIDA.")
    return classes[tipo](valor, data, descricao, ligada_atividade)
