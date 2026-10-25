"""CalculadoraDAS: Strategy por atividade (comércio, serviço, ambos), sem if/else espalhado.
Os valores vêm da TabelaDAS (banco), nunca do código."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from .dinheiro import q


@dataclass(frozen=True)
class ParametrosDAS:
    ano: int
    salario_minimo: Decimal
    perc_inss: Decimal
    perc_inss_caminhoneiro: Decimal
    valor_icms: Decimal
    valor_iss: Decimal
    teto_anual: Decimal
    teto_caminhoneiro: Decimal
    fonte: str = ""

    def inss(self, caminhoneiro: bool = False) -> Decimal:
        pct = self.perc_inss_caminhoneiro if caminhoneiro else self.perc_inss
        return q(self.salario_minimo * pct / Decimal("100"))

    def teto(self, caminhoneiro: bool = False) -> Decimal:
        return self.teto_caminhoneiro if caminhoneiro else self.teto_anual


@dataclass(frozen=True)
class ComposicaoDAS:
    inss: Decimal          # federal
    icms: Decimal = Decimal("0.00")   # estadual
    iss: Decimal = Decimal("0.00")    # municipal

    @property
    def total(self) -> Decimal:
        return q(self.inss + self.icms + self.iss)

    def esferas(self) -> dict:
        return {"federal": {"tributo": "INSS", "valor": self.inss},
                "estadual": {"tributo": "ICMS", "valor": self.icms},
                "municipal": {"tributo": "ISS", "valor": self.iss}}


class CalculadoraDAS(ABC):
    @abstractmethod
    def calcular(self, p: ParametrosDAS, caminhoneiro: bool = False) -> ComposicaoDAS: ...


class DASComercio(CalculadoraDAS):
    def calcular(self, p, caminhoneiro=False):
        return ComposicaoDAS(inss=p.inss(caminhoneiro), icms=q(p.valor_icms))


class DASServico(CalculadoraDAS):
    def calcular(self, p, caminhoneiro=False):
        return ComposicaoDAS(inss=p.inss(caminhoneiro), iss=q(p.valor_iss))


class DASAmbos(CalculadoraDAS):
    def calcular(self, p, caminhoneiro=False):
        return ComposicaoDAS(inss=p.inss(caminhoneiro), icms=q(p.valor_icms), iss=q(p.valor_iss))


_CALCULADORAS = {"COMERCIO": DASComercio, "SERVICO": DASServico, "AMBOS": DASAmbos}


def calculadora_para(tipo_atividade: str) -> CalculadoraDAS:
    """Factory da Strategy."""
    try:
        return _CALCULADORAS[tipo_atividade]()
    except KeyError:
        raise ValueError("Tipo de atividade deve ser COMERCIO, SERVICO ou AMBOS.")


def calcular_das(p: ParametrosDAS, tipo_atividade: str, caminhoneiro: bool = False) -> ComposicaoDAS:
    return calculadora_para(tipo_atividade).calcular(p, caminhoneiro)
