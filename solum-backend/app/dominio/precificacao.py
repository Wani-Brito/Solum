"""Preço mínimo de um serviço (RN14): nunca abaixo do ponto de equilíbrio, já embutindo o DAS."""
from dataclasses import dataclass
from decimal import Decimal

from .dinheiro import D, q


@dataclass
class ResultadoPreco:
    custo_base: Decimal
    imposto_rateado: Decimal
    ponto_equilibrio: Decimal
    preco_minimo: Decimal


def calcular_preco_minimo(horas, custo_hora, custo_materiais, outros_custos, margem_lucro, das_mensal, servicos_por_mes=1) -> ResultadoPreco:
    horas, custo_hora = D(horas), q(custo_hora)
    margem = D(margem_lucro)
    if horas <= 0 or custo_hora < 0 or q(custo_materiais) < 0 or q(outros_custos) < 0:
        raise ValueError("Horas devem ser maiores que zero e custos não podem ser negativos.")
    if not (0 <= margem < 100):
        raise ValueError("A margem de lucro deve estar entre 0 e 100 (exclusive).")
    if int(servicos_por_mes) < 1:
        raise ValueError("Serviços por mês deve ser pelo menos 1.")
    custo_base = q(horas * custo_hora + q(custo_materiais) + q(outros_custos))
    imposto = q(q(das_mensal) / int(servicos_por_mes))
    equilibrio = q(custo_base + imposto)
    preco = q(equilibrio / (1 - margem / 100))
    return ResultadoPreco(custo_base, imposto, equilibrio, max(preco, equilibrio))
