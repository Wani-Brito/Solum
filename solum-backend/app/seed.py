"""Dados iniciais (idempotentes) e dados de demonstração."""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from . import models as m
from .security import hash_senha

FONTE_DAS_2026 = "Salário mínimo R$ 1.621,00 (2026); INSS 5% (12% caminhoneiro), ICMS R$ 1,00, ISS R$ 5,00. Conferir no Portal do Empreendedor."


def dados_iniciais(db: Session) -> None:
    if db.query(m.Plano).count() == 0:
        db.add_all([m.Plano(nome="NORMAL", preco_mensal=Decimal("0.00")), m.Plano(nome="PREMIUM", preco_mensal=Decimal("19.90"))])
    if db.query(m.TabelaDAS).filter_by(ano=2026).first() is None:
        db.add(m.TabelaDAS(ano=2026, salario_minimo=Decimal("1621.00"), perc_inss=Decimal("5"), perc_inss_caminhoneiro=Decimal("12"),
                           valor_icms=Decimal("1.00"), valor_iss=Decimal("5.00"), teto_anual=Decimal("81000.00"),
                           teto_caminhoneiro=Decimal("251600.00"), fonte=FONTE_DAS_2026))
    if db.get(m.CotacaoCache, "CDI") is None:
        db.add(m.CotacaoCache(simbolo="CDI", descricao="CDI (% a.a.) - valor de exemplo", valor=Decimal("10.5000"), fonte="Exemplo (cache local)"))
        db.add(m.CotacaoCache(simbolo="SELIC", descricao="Selic meta (% a.a.) - valor de exemplo", valor=Decimal("10.5000"), fonte="Exemplo (cache local)"))
    if db.get(m.ConfiguracaoSistema, "percentual_alerta_padrao") is None:
        db.add(m.ConfiguracaoSistema(chave="percentual_alerta_padrao", valor="80"))
    db.commit()
