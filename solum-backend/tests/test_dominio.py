from datetime import date
from decimal import Decimal

import pytest

from app.dominio import fatura as regras_fatura
from app.dominio.chatbot import interpretar
from app.dominio.das import ParametrosDAS, calcular_das
from app.dominio.fluxo import FluxoCaixa
from app.dominio.notificacao import gerar_notificacoes
from app.dominio.precificacao import calcular_preco_minimo
from app.dominio.reserva import ReservaEstabilizacao
from app.dominio.suavizacao import ServicoSuavizacao
from app.dominio.teto import avaliar_teto, teto_proporcional
from app.dominio.transacao import Entrada, Saida, criar_transacao

D = Decimal
P2026 = ParametrosDAS(2026, D("1621"), D("5"), D("12"), D("1"), D("5"), D("81000"), D("251600"))


# ---- RN15 e herança
def test_valor_zero_ou_negativo_e_rejeitado():
    for v in (0, -1, "-0.01"):
        with pytest.raises(ValueError):
            Entrada(v, date(2026, 1, 1))


def test_somente_entrada_ligada_a_atividade_conta_para_o_teto():
    assert Entrada(100, date(2026, 1, 1)).conta_para_teto
    assert not Entrada(100, date(2026, 1, 1), ligada_atividade=False).conta_para_teto
    assert not Saida(100, date(2026, 1, 1)).conta_para_teto


def test_factory_de_transacao():
    assert isinstance(criar_transacao("ENTRADA", 10, date(2026, 1, 1)), Entrada)
    assert criar_transacao("SAIDA", 10, date(2026, 1, 1)).valor_assinado() == D("-10.00")
    with pytest.raises(ValueError):
        criar_transacao("OUTRO", 10, date(2026, 1, 1))


def test_fluxo_de_caixa_soma_entradas_e_saidas():
    f = FluxoCaixa(1000)
    f.adicionar(Entrada(500, date(2026, 1, 1)))
    f.adicionar(Saida(200, date(2026, 1, 2)))
    assert (f.total_entradas, f.total_saidas, f.resultado, f.saldo_final) == (D("500.00"), D("200.00"), D("300.00"), D("1300.00"))


# ---- reserva (encapsulamento)
def test_reserva_nao_permite_retirar_mais_que_o_saldo():
    r = ReservaEstabilizacao(100)
    with pytest.raises(ValueError):
        r.retirar(100.01)
    r.retirar(40)
    assert r.saldo == D("60.00")
    assert [m.tipo for m in r.movimentos] == ["RETIRADA"]


def test_reserva_nao_nasce_negativa():
    with pytest.raises(ValueError):
        ReservaEstabilizacao(-1)


# ---- suavização (RN06 a RN09): 7 meses, DAS 86,05, salário desejado 3.000
MESES = [  # receita, despesa, retirada esperada, saldo final esperado, faltou esperado
    (6000, 500, "3000.00", "2413.95", "0.00"),
    (1800, 300, "3000.00", "827.90", "0.00"),
    (4200, 400, "3000.00", "1541.85", "0.00"),
    (900, 200, "2155.80", "0.00", "844.20"),
    (7000, 100, "3000.00", "3813.95", "0.00"),
    (1100, 150, "3000.00", "1677.90", "0.00"),
    (300, 100, "1791.85", "0.00", "1208.15"),
]


def test_suavizacao_sete_meses():
    reserva, srv, das = ReservaEstabilizacao(0), ServicoSuavizacao(), D("86.05")
    for receita, despesa, retirada, saldo, faltou in MESES:
        r = srv.fechar_mes(D(receita) - D(despesa) - das, 3000, reserva)
        assert r.retirada == D(retirada)
        assert r.saldo_final == D(saldo) == reserva.saldo
        assert r.faltou == D(faltou)


def test_retirada_nunca_excede_receita_mais_reserva():  # RN06
    r = ServicoSuavizacao().fechar_mes(D("100"), 3000, ReservaEstabilizacao(50))
    assert r.retirada == D("150.00") and r.saldo_final == D("0.00")
    assert "Faltou" in r.mensagem and "150,00" in r.mensagem  # RN08.2: informa o valor real disponível


def test_mes_negativo_sai_da_reserva_limitado_ao_saldo():
    reserva = ReservaEstabilizacao(500)
    r = ServicoSuavizacao().fechar_mes(D("-200"), 3000, reserva)
    assert r.retirada == D("300.00") and reserva.saldo == D("0.00")


def test_todo_movimento_da_reserva_gera_log():  # RN09.3
    reserva = ReservaEstabilizacao(0)
    ServicoSuavizacao().fechar_mes(D("5000"), 3000, reserva, "01/2026")
    ServicoSuavizacao().fechar_mes(D("2000"), 3000, reserva, "02/2026")
    assert [(m.tipo, m.valor, m.saldo_apos) for m in reserva.movimentos] == [("APORTE", D("2000.00"), D("2000.00")), ("RETIRADA", D("1000.00"), D("1000.00"))]


def test_salario_desejado_negativo_e_rejeitado():
    with pytest.raises(ValueError):
        ServicoSuavizacao().fechar_mes(100, -1, ReservaEstabilizacao(0))


# ---- DAS 2026 (valores oficiais) e Strategy
@pytest.mark.parametrize("atividade,esperado", [("COMERCIO", "82.05"), ("SERVICO", "86.05"), ("AMBOS", "87.05")])
def test_das_padrao_2026(atividade, esperado):
    assert calcular_das(P2026, atividade).total == D(esperado)


@pytest.mark.parametrize("atividade,esperado", [("COMERCIO", "195.52"), ("SERVICO", "199.52"), ("AMBOS", "200.52")])
def test_das_caminhoneiro_2026(atividade, esperado):
    assert calcular_das(P2026, atividade, caminhoneiro=True).total == D(esperado)


def test_das_mostra_as_tres_esferas():
    e = calcular_das(P2026, "AMBOS").esferas()
    assert (e["federal"]["valor"], e["estadual"]["valor"], e["municipal"]["valor"]) == (D("81.05"), D("1.00"), D("5.00"))


def test_atividade_invalida():
    with pytest.raises(ValueError):
        calcular_das(P2026, "INDUSTRIA")


# ---- teto (RN05)
@pytest.mark.parametrize("acumulado,nivel", [(10000, "NORMAL"), (64800, "ALERTA"), (81000, "ALERTA"), (90000, "EXCESSO_TOLERADO"), (97200, "EXCESSO_TOLERADO"), (97300, "DESENQUADRAMENTO")])
def test_niveis_do_teto(acumulado, nivel):
    assert avaliar_teto(acumulado, 81000, 80).nivel == nivel


def test_teto_proporcional_no_ano_de_abertura():
    assert teto_proporcional(81000, 7) == D("40500.00")   # julho a dezembro = 6 meses
    assert teto_proporcional(81000, 1) == D("81000.00")


# ---- precificação (RN14)
def test_preco_minimo_embute_custos_e_das():
    r = calcular_preco_minimo(20, 40, 80, 120, 30, "86.05", 4)
    assert (r.custo_base, r.imposto_rateado, r.ponto_equilibrio, r.preco_minimo) == (D("1000.00"), D("21.51"), D("1021.51"), D("1459.30"))


def test_preco_nunca_abaixo_do_ponto_de_equilibrio():
    r = calcular_preco_minimo(1, 10, 0, 0, 0, "86.05", 1)
    assert r.preco_minimo >= r.ponto_equilibrio


@pytest.mark.parametrize("margem", [-1, 100, 150])
def test_margem_invalida(margem):
    with pytest.raises(ValueError):
        calcular_preco_minimo(1, 10, 0, 0, margem, "86.05", 1)


# ---- faturas (RN10 a RN13)
def test_status_da_fatura_segue_o_vencimento():
    assert regras_fatura.status_por_vencimento("PENDENTE", date(2026, 5, 1), date(2026, 5, 2)) == "ATRASADA"
    assert regras_fatura.status_por_vencimento("PENDENTE", date(2026, 5, 2), date(2026, 5, 2)) == "PENDENTE"
    assert regras_fatura.status_por_vencimento("PAGA", date(2020, 1, 1), date(2026, 5, 2)) == "PAGA"


def test_nota_fiscal_obrigatoria_para_pj_e_sob_pedido_para_pf():
    assert regras_fatura.nota_obrigatoria("PJ")
    assert not regras_fatura.nota_obrigatoria("PF")
    assert regras_fatura.nota_obrigatoria("PF", solicitada=True)


def test_bloqueio_por_inadimplencia_recorrente():
    assert not regras_fatura.deve_bloquear(2)
    assert regras_fatura.deve_bloquear(3)


# ---- notificações
def test_notificacoes_e_preferencias():
    hoje = date(2026, 10, 18)
    obrig = [("DAS 09/2026", date(2026, 10, 20), "PENDENTE"), ("DAS 08/2026", date(2026, 9, 20), "PENDENTE"), ("DASN-SIMEI 2025", date(2026, 5, 31), "PENDENTE")]
    teto = avaliar_teto(70000, 81000, 80)
    tudo = {"das": True, "dasn": True, "saldo": True, "teto": True, "fatura": True}
    tipos = {n.tipo for n in gerar_notificacoes(hoje, D("50"), D("100"), obrig, [(1, "Site")], teto, tudo)}
    assert tipos == {"SALDO_BAIXO", "DAS", "FATURA_ATRASADA", "TETO"}
    nenhuma = gerar_notificacoes(hoje, D("50"), D("100"), obrig, [(1, "Site")], teto, {k: False for k in tudo})
    assert nenhuma == []


# ---- chatbot
@pytest.mark.parametrize("msg,tipo,valor", [("Gastei 150 com internet", "SAIDA", "150"), ("Recebi 1.500,50 do cliente", "ENTRADA", "1500.50"),
                                            ("Paguei 89,90 em 12/09/2026", "SAIDA", "89.90"), ("vendi 2.500 hoje", "ENTRADA", "2500")])
def test_chatbot_interpreta_valores_brasileiros(msg, tipo, valor):
    t, v, _ = interpretar(msg)
    assert (t, v) == (tipo, D(valor))


@pytest.mark.parametrize("msg", ["Olá, tudo bem?", "gastei e recebi 10", "Gastei muito"])
def test_chatbot_recusa_frases_ambiguas(msg):
    with pytest.raises(ValueError):
        interpretar(msg)
