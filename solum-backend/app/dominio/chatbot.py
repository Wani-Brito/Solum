"""Interpreta frases como 'Gastei 150,50 com internet' em uma transação."""
import re
import unicodedata
from decimal import Decimal

SAIDAS = ("gastei", "paguei", "comprei", "despesa", "custo", "saida", "debito")
ENTRADAS = ("recebi", "ganhei", "vendi", "faturei", "entrada", "credito", "caiu")
_DATA = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
_NUM = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?")


def _sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def normalizar_numero(txt: str) -> Decimal:
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", txt):
        txt = txt.replace(".", "")
    return Decimal(txt)


def interpretar(mensagem: str) -> tuple[str, Decimal, str]:
    base = _sem_acento(mensagem)
    palavras = set(re.findall(r"[a-z]+", base))
    e_saida = any(p in palavras for p in SAIDAS)
    e_entrada = any(p in palavras for p in ENTRADAS)
    if e_saida == e_entrada:
        raise ValueError("Não entendi se é entrada ou saída. Use palavras como 'gastei' ou 'recebi'.")
    sem_datas = _DATA.sub(" ", mensagem)
    achados = _NUM.findall(sem_datas)
    if not achados:
        raise ValueError("Não encontrei o valor na mensagem.")
    valor = normalizar_numero(achados[0])
    if valor <= 0:
        raise ValueError("O valor deve ser maior que zero (RN15).")
    return ("ENTRADA" if e_entrada else "SAIDA"), valor, mensagem.strip()[:150]
