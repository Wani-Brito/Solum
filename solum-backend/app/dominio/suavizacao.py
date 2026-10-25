"""ServicoSuavizacao: regras RN06 a RN09 (o ponto mais crítico do projeto).

disponível = resultado do mês + saldo da reserva
retirada   = o menor entre o salário desejado e o disponível (nunca negativa)
sobra      = vai para a reserva; déficit sai dela, limitado ao saldo
"""
from dataclasses import dataclass
from decimal import Decimal

from .dinheiro import brl, q
from .reserva import ReservaEstabilizacao


@dataclass
class ResultadoFechamento:
    resultado_mes: Decimal
    saldo_inicial: Decimal
    disponivel: Decimal
    salario_desejado: Decimal
    retirada: Decimal
    aporte: Decimal
    retirada_da_reserva: Decimal
    saldo_final: Decimal
    faltou: Decimal
    mensagem: str


class ServicoSuavizacao:
    def fechar_mes(self, resultado_mes, salario_desejado, reserva: ReservaEstabilizacao, descricao_mes: str = "") -> ResultadoFechamento:
        resultado_mes = q(resultado_mes)
        desejado = q(salario_desejado)
        if desejado < 0:
            raise ValueError("O salário desejado não pode ser negativo.")
        saldo_ini = reserva.saldo
        disponivel = q(resultado_mes + saldo_ini)                      # RN06
        retirada = q(max(Decimal("0"), min(desejado, disponivel)))     # RN06 + RN08
        saldo_fim = q(max(Decimal("0"), disponivel - retirada))
        delta = q(saldo_fim - saldo_ini)
        sufixo = f" ({descricao_mes})" if descricao_mes else ""
        if delta > 0:                                                  # RN07
            reserva.aportar(delta, "Sobra do mês" + sufixo)
        elif delta < 0:                                                # RN08
            reserva.retirar(-delta, "Complemento do salário" + sufixo)
        faltou = q(desejado - retirada)
        if faltou > 0:                                                 # RN08.2
            msg = f"A reserva não cobre o salário desejado. Valor real disponível: R$ {brl(retirada)}. Faltou R$ {brl(faltou)}."
        elif delta > 0:
            msg = f"Salário de R$ {brl(retirada)} garantido. R$ {brl(delta)} foram para a reserva."
        elif delta < 0:
            msg = f"Salário de R$ {brl(retirada)} garantido, com R$ {brl(-delta)} vindos da reserva."
        else:
            msg = f"Salário de R$ {brl(retirada)} garantido."
        return ResultadoFechamento(resultado_mes, saldo_ini, disponivel, desejado, retirada,
                                   max(delta, Decimal("0")), max(-delta, Decimal("0")), saldo_fim, faltou, msg)
