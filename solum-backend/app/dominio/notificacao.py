"""Geração das notificações (RN17 a RN21). Cada uma tem uma chave única, para não repetir."""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .dinheiro import brl


@dataclass
class NotificacaoDominio:
    chave: str
    tipo: str
    mensagem: str


def gerar_notificacoes(hoje: date, saldo_total: Decimal, saldo_minimo: Decimal, obrigacoes: list, faturas_atrasadas: list, status_teto, prefs: dict) -> list:
    """obrigacoes: lista de (descricao, vencimento, status). faturas_atrasadas: lista de (id, descricao)."""
    out: list[NotificacaoDominio] = []
    if prefs.get("saldo", True) and saldo_total < saldo_minimo:
        out.append(NotificacaoDominio(f"saldo-{hoje:%Y-%m}", "SALDO_BAIXO", f"Saldo abaixo do mínimo (R$ {brl(saldo_minimo)})."))
    for desc, venc, status in obrigacoes:
        if status == "PAGO":
            continue
        if desc.startswith("DASN") and prefs.get("dasn", True) and hoje <= venc <= hoje + timedelta(days=30):
            out.append(NotificacaoDominio(f"dasn-{venc.year}", "DASN_SIMEI", f"A declaração anual (DASN-SIMEI) vence em {venc:%d/%m/%Y}."))
        elif desc.startswith("DAS ") and prefs.get("das", True) and hoje <= venc <= hoje + timedelta(days=3):
            out.append(NotificacaoDominio(f"das-{venc:%Y-%m}", "DAS", f"O DAS vence em {venc:%d/%m/%Y}."))
        elif desc.startswith("DAS ") and prefs.get("das", True) and venc < hoje:
            out.append(NotificacaoDominio(f"das-atraso-{venc:%Y-%m}", "DAS", f"O {desc} está atrasado (venceu em {venc:%d/%m/%Y})."))
    if prefs.get("fatura", True):
        for fid, desc in faturas_atrasadas:
            out.append(NotificacaoDominio(f"fatura-{fid}", "FATURA_ATRASADA", f"Fatura atrasada: {desc}."))
    if prefs.get("teto", True) and status_teto is not None and status_teto.nivel != "NORMAL":
        out.append(NotificacaoDominio(f"teto-{status_teto.nivel}-{hoje.year}", "TETO", status_teto.mensagem))
    return out
