from datetime import date, timedelta

import pytest

from app import models as m
from app.database import SessionLocal
from tests.conftest import _auth, lancar

ANO = date.today().year


def garantir_tabela(ano):
    """O seed cadastra 2026; para outros anos, copia os mesmos valores (só nos testes)."""
    with SessionLocal() as db:
        if not db.query(m.TabelaDAS).filter_by(ano=ano).first():
            base = db.query(m.TabelaDAS).filter_by(ano=2026).first()
            db.add(m.TabelaDAS(ano=ano, **{c.name: getattr(base, c.name) for c in base.__table__.columns if c.name not in ("id_tabela", "ano")}))
            db.commit()


# ---------------------------------------------------------------- segurança
def test_raiz_e_cors(client):
    assert client.get("/").json()["status"] == "online"
    r = client.options("/auth/login", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_rotas_protegidas_exigem_token(client):
    for rota in ("/usuarios/me", "/transacoes", "/dashboard", "/teto", "/faturas", "/metas", "/reserva", "/notificacoes"):
        assert client.get(rota).status_code == 401, rota
    assert client.get("/usuarios/me", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_registro_login_e_senha_com_hash(client):
    r = client.post("/auth/registro", json={"nome": "Ana", "email": "ANA@x.com", "senha": "segredo123", "perfil": "ADMIN"})
    assert r.status_code == 201 and r.json()["usuario"]["perfil"] == "NORMAL"  # o cliente não escolhe o perfil
    with SessionLocal() as db:
        senha = db.query(m.Usuario).first().senha
        assert senha != "segredo123" and senha.startswith("$2")  # bcrypt
    assert client.post("/auth/login", json={"email": "ana@x.com", "senha": "segredo123"}).status_code == 200
    assert client.post("/auth/login", json={"email": "ana@x.com", "senha": "errada"}).status_code == 401
    assert client.post("/auth/registro", json={"nome": "Ana", "email": "ana@x.com", "senha": "segredo123"}).status_code == 409


def test_perfil_senha_e_preferencias(client, auth):
    assert client.put("/usuarios/me", headers=auth, json={"nome": "Ana Maria", "telefone": "(19) 90000-0000"}).json()["nome"] == "Ana Maria"
    assert client.put("/usuarios/me/senha", headers=auth, json={"senha_atual": "x", "nova_senha": "novasenha1"}).status_code == 400
    assert client.put("/usuarios/me/senha", headers=auth, json={"senha_atual": "segredo123", "nova_senha": "novasenha1"}).status_code == 200
    assert client.post("/auth/login", json={"email": "ana@teste.com", "senha": "novasenha1"}).status_code == 200
    p = client.get("/usuarios/me/preferencias", headers=auth).json()
    assert p["tema"] == "ESCURO"  # o Solum nasce no modo escuro
    assert client.put("/usuarios/me/preferencias", headers=auth, json={"tema": "CLARO", "notif_das": False}).json()["tema"] == "CLARO"


def test_um_usuario_nao_acessa_dados_de_outro(client, mei, outro):
    t = lancar(client, mei, "ENTRADA", 100, "2026-01-10").json()
    assert client.put(f"/transacoes/{t['id_transacao']}", headers=outro, json={"id_conta": 1, "id_categoria": 1, "descricao": "x", "valor": "1", "data": "2026-01-10", "tipo": "ENTRADA"}).status_code == 404
    assert client.delete(f"/transacoes/{t['id_transacao']}", headers=outro).status_code == 404
    assert client.get("/transacoes", headers=outro).json() == []


def test_perfis_premium_e_admin(client, auth, admin):
    assert client.get("/investimentos/carteira", headers=auth).status_code == 403
    assert client.get("/admin/dashboard", headers=auth).status_code == 403
    assert client.get("/admin/dashboard", headers=admin).status_code == 200


# ---------------------------------------------------------------- MEI
def test_cadastro_do_mei_valida_cnae(client, auth):
    base = {"tipo_atividade": "SERVICO", "categoria": "PADRAO", "cnae": "62015", "data_abertura": "2024-03-10"}
    assert client.put("/mei", headers=auth, json=base).status_code == 422
    assert client.put("/mei", headers=auth, json={**base, "cnae": "6201-5/01"}).status_code == 200
    assert client.get("/mei", headers=auth).json()["cnae"] == "6201501"


def test_cnae_so_aceita_atividades_permitidas_quando_a_lista_existe(client, auth, admin):
    assert client.post("/admin/cnaes", headers=admin, json=[{"cnae": "4781-4/00", "descricao": "Comércio de roupas", "tipo_atividade": "COMERCIO"}]).json()["importados"] == 1
    base = {"tipo_atividade": "SERVICO", "categoria": "PADRAO", "data_abertura": "2024-03-10"}
    assert client.put("/mei", headers=auth, json={**base, "cnae": "6201501"}).status_code == 422
    assert client.put("/mei", headers=auth, json={**base, "cnae": "4781400"}).status_code == 200


def test_sem_mei_nao_ha_das(client, auth):
    assert client.get("/impostos/das", headers=auth).status_code == 422


# ---------------------------------------------------------------- transações e fluxo
def test_transacao_atualiza_conta_fluxo_e_faturamento(client, mei):
    assert lancar(client, mei, "ENTRADA", "2500.00", "2026-01-12").status_code == 201
    assert lancar(client, mei, "SAIDA", "500.00", "2026-01-15").status_code == 201
    assert client.get("/contas", headers=mei["h"]).json()[0]["saldo"] == "2000.00" or float(client.get("/contas", headers=mei["h"]).json()[0]["saldo"]) == 2000.0
    f = client.get("/fluxo-caixa/2026/1", headers=mei["h"]).json()
    assert (float(f["total_entradas"]), float(f["total_saidas"]), float(f["saldo_final"])) == (2500.0, 500.0, 2000.0)
    assert len(client.get("/fluxo-caixa/historico", headers=mei["h"]).json()) == 1  # o histórico deixou de dar 404


def test_saldo_inicial_encadeia_entre_meses_e_reconsolida(client, mei):
    lancar(client, mei, "ENTRADA", 1000, "2026-01-10")
    lancar(client, mei, "ENTRADA", 500, "2026-02-10")
    fev = client.get("/fluxo-caixa/2026/2", headers=mei["h"]).json()
    assert float(fev["saldo_inicial"]) == 1000.0 and float(fev["saldo_final"]) == 1500.0
    lancar(client, mei, "SAIDA", 200, "2026-01-20")  # lançamento retroativo muda o saldo inicial de fevereiro
    fev = client.get("/fluxo-caixa/2026/2", headers=mei["h"]).json()
    assert float(fev["saldo_inicial"]) == 800.0 and float(fev["saldo_final"]) == 1300.0


def test_regras_de_integridade_de_transacao(client, mei):
    assert lancar(client, mei, "ENTRADA", 0, "2026-01-10").status_code == 422      # RN15
    assert lancar(client, mei, "ENTRADA", -5, "2026-01-10").status_code == 422
    r = client.post("/transacoes", headers=mei["h"], json={"id_conta": mei["conta"], "id_categoria": mei["cat_s"], "descricao": "x", "valor": "10", "data": "2026-01-10", "tipo": "ENTRADA"})
    assert r.status_code == 422  # categoria de saída em uma entrada
    assert client.post("/transacoes", headers=mei["h"], json={"id_conta": 999, "id_categoria": mei["cat_e"], "descricao": "x", "valor": "10", "data": "2026-01-10", "tipo": "ENTRADA"}).status_code == 404


def test_editar_e_excluir_transacao_refaz_saldo_e_teto(client, mei):
    t = lancar(client, mei, "ENTRADA", 1000, "2026-03-05").json()
    body = {"id_conta": mei["conta"], "id_categoria": mei["cat_e"], "descricao": "Ajustada", "valor": "400", "data": "2026-03-06", "tipo": "ENTRADA"}
    assert client.put(f"/transacoes/{t['id_transacao']}", headers=mei["h"], json=body).status_code == 200
    assert float(client.get("/contas", headers=mei["h"]).json()[0]["saldo"]) == 400.0
    assert client.delete(f"/transacoes/{t['id_transacao']}", headers=mei["h"]).status_code == 204
    assert float(client.get("/contas", headers=mei["h"]).json()[0]["saldo"]) == 0.0
    assert float(client.get("/fluxo-caixa/2026/3", headers=mei["h"]).json()["total_entradas"]) == 0.0


def test_listar_transacoes_por_mes_e_tipo(client, mei):
    lancar(client, mei, "ENTRADA", 100, "2026-04-01")
    lancar(client, mei, "SAIDA", 30, "2026-04-02")
    lancar(client, mei, "ENTRADA", 50, "2026-05-01")
    assert len(client.get("/transacoes?ano=2026&mes=4", headers=mei["h"]).json()) == 2
    assert len(client.get("/transacoes?ano=2026&mes=4&tipo=SAIDA", headers=mei["h"]).json()) == 1


def test_chatbot_cria_transacao(client, mei):
    r = client.post("/chatbot/registrar-transacao", headers=mei["h"], json={"mensagem": "Gastei 150,50 com internet"})
    assert r.status_code == 201 and r.json()["tipo"] == "SAIDA" and float(r.json()["valor"]) == 150.5
    assert client.post("/chatbot/registrar-transacao", headers=mei["h"], json={"mensagem": "bom dia tudo bem"}).status_code == 422


# ---------------------------------------------------------------- DAS, teto, reserva
def test_das_por_esfera(client, mei):
    d = client.get("/impostos/das?ano=2026", headers=mei["h"]).json()
    assert d["total"] in ("86.05", 86.05) or float(d["total"]) == 86.05
    assert float(d["esferas"]["federal"]["valor"]) == 81.05 and float(d["esferas"]["municipal"]["valor"]) == 5.0 and float(d["esferas"]["estadual"]["valor"]) == 0.0


def test_ano_sem_tabela_das_avisa(client, mei):
    assert "ainda não foi cadastrada" in client.get("/impostos/das?ano=2031", headers=mei["h"]).json()["detail"]


def test_cota_mensal_e_idempotente(client, mei):
    garantir_tabela(ANO)
    lancar(client, mei, "ENTRADA", 3000, f"{ANO}-01-10")
    a = client.post("/impostos/cota-mensal", headers=mei["h"]).json()
    b = client.post("/impostos/cota-mensal", headers=mei["h"]).json()
    assert a["valor_reservado"] == b["valor_reservado"] and float(a["das_total"]) == 86.05  # não soma de novo a cada chamada
    assert len(client.get("/impostos/obrigacoes", headers=mei["h"]).json()) == 13  # 12 DAS + DASN-SIMEI


def test_pagar_obrigacao(client, mei):
    garantir_tabela(ANO)
    client.post("/impostos/obrigacoes/gerar", headers=mei["h"])
    o = client.get("/impostos/obrigacoes", headers=mei["h"]).json()[0]
    assert client.patch(f"/impostos/obrigacoes/{o['id_obrigacao']}/pagar", headers=mei["h"]).json()["status"] == "PAGO"


def test_teto_acumula_entradas_ligadas_a_atividade(client, mei):
    garantir_tabela(ANO)
    lancar(client, mei, "ENTRADA", 60000, f"{ANO}-02-01")
    lancar(client, mei, "ENTRADA", 20000, f"{ANO}-02-02", ligada=False)  # Pix pessoal sem relação não conta
    lancar(client, mei, "SAIDA", 5000, f"{ANO}-02-03")                    # saída não conta
    t = client.get("/teto", headers=mei["h"]).json()
    assert float(t["acumulado"]) == 60000.0 and float(t["teto"]) == 81000.0 and t["nivel"] == "NORMAL"
    lancar(client, mei, "ENTRADA", 6000, f"{ANO}-03-01")
    assert client.get("/teto", headers=mei["h"]).json()["nivel"] == "ALERTA"
    lancar(client, mei, "ENTRADA", 20000, f"{ANO}-04-01")
    assert client.get("/teto", headers=mei["h"]).json()["nivel"] == "EXCESSO_TOLERADO"
    lancar(client, mei, "ENTRADA", 20000, f"{ANO}-05-01")
    assert client.get("/teto", headers=mei["h"]).json()["nivel"] == "DESENQUADRAMENTO"


def test_alerta_do_teto_e_configuravel(client, mei):
    garantir_tabela(ANO)
    client.put("/usuarios/me/preferencias", headers=mei["h"], json={"percentual_alerta": 50})
    lancar(client, mei, "ENTRADA", 45000, f"{ANO}-02-01")
    assert client.get("/teto", headers=mei["h"]).json()["nivel"] == "ALERTA"


def test_fechamento_de_mes_sete_meses_com_log_da_reserva(client, mei):
    garantir_tabela(2026)
    dados = [(6000, 500), (1800, 300), (4200, 400), (900, 200), (7000, 100), (1100, 150), (300, 100)]
    esperado = [("3000.00", "2413.95"), ("3000.00", "827.90"), ("3000.00", "1541.85"), ("2155.80", "0.00"), ("3000.00", "3813.95"), ("3000.00", "1677.90"), ("1791.85", "0.00")]
    for mes, ((rec, desp), (ret, saldo)) in enumerate(zip(dados, esperado), start=1):
        lancar(client, mei, "ENTRADA", rec, f"2026-{mes:02d}-10")
        lancar(client, mei, "SAIDA", desp, f"2026-{mes:02d}-11")
        r = client.post("/suavizacao/fechar-mes", headers=mei["h"], json={"ano": 2026, "mes": mes, "salario_desejado": "3000"})
        assert r.status_code == 200, r.text
        assert (float(r.json()["retirada"]), float(r.json()["saldo_final"])) == (float(ret), float(saldo)), f"mês {mes}"
    reserva = client.get("/reserva", headers=mei["h"]).json()
    assert float(reserva["saldo"]) == 0.0 and len(reserva["movimentos"]) >= 7  # log auditável
    assert len(client.get("/retiradas", headers=mei["h"]).json()) == 7


def test_nao_fecha_o_mesmo_mes_duas_vezes(client, mei):
    lancar(client, mei, "ENTRADA", 5000, "2026-01-10")
    corpo = {"ano": 2026, "mes": 1, "salario_desejado": "3000"}
    assert client.post("/suavizacao/fechar-mes", headers=mei["h"], json=corpo).status_code == 200
    assert client.post("/suavizacao/fechar-mes", headers=mei["h"], json=corpo).status_code == 409


def test_simulacao_nao_grava_nada(client, mei):
    r = client.post("/suavizacao/simular", headers=mei["h"], json={"resultado_mes": "100", "saldo_reserva": "50", "salario_desejado": "3000"})
    assert float(r.json()["retirada"]) == 150.0 and float(r.json()["faltou"]) == 2850.0
    assert client.get("/reserva", headers=mei["h"]).json()["movimentos"] == []


# ---------------------------------------------------------------- clientes e faturas
def _cliente(client, h, nome="Cliente A", tipo="PF"):
    return client.post("/clientes", headers=h, json={"nome": nome, "tipo_pessoa": tipo}).json()["id_cliente"]


def _fatura(client, h, cid, valor, emissao, venc, **kw):
    return client.post("/faturas", headers=h, json={"id_cliente": cid, "descricao": f"Serviço {valor}", "valor": str(valor), "data_emissao": emissao, "data_vencimento": venc, **kw})


def test_fatura_duplicada_e_rejeitada(client, auth):  # RN16
    cid = _cliente(client, auth)
    assert _fatura(client, auth, cid, 500, "2030-01-01", "2030-01-31").status_code == 201
    assert _fatura(client, auth, cid, 500, "2030-01-01", "2030-02-15").status_code == 409
    assert _fatura(client, auth, cid, 500, "2030-01-02", "2030-02-15").status_code == 201


def test_nota_fiscal_por_tipo_de_cliente(client, auth):  # RN11
    pj, pf = _cliente(client, auth, "Empresa", "PJ"), _cliente(client, auth, "Pessoa", "PF")
    assert _fatura(client, auth, pj, 100, "2030-01-01", "2030-01-31").json()["nota_obrigatoria"] is True
    assert _fatura(client, auth, pf, 100, "2030-01-01", "2030-01-31").json()["nota_obrigatoria"] is False
    assert _fatura(client, auth, pf, 200, "2030-01-01", "2030-01-31", nota_solicitada=True).json()["nota_obrigatoria"] is True


def test_vencimento_antes_da_emissao_e_invalido(client, auth):
    assert _fatura(client, auth, _cliente(client, auth), 100, "2030-02-01", "2030-01-01").status_code == 422


def test_status_automatico_e_pagamento(client, auth):
    cid = _cliente(client, auth)
    antiga = _fatura(client, auth, cid, 100, "2020-01-01", "2020-01-31").json()
    assert antiga["status"] == "ATRASADA"
    futura = _fatura(client, auth, cid, 200, "2030-01-01", "2030-01-31").json()
    assert futura["status"] == "PENDENTE"
    pago = client.patch(f"/faturas/{futura['id_fatura']}/pagar", headers=auth, json={}).json()
    assert pago["status"] == "PAGA"
    assert client.patch(f"/faturas/{futura['id_fatura']}/pagar", headers=auth, json={}).status_code == 409
    assert [f["status"] for f in client.get("/faturas?status=ATRASADA", headers=auth).json()] == ["ATRASADA"]


def test_pagar_fatura_pode_gerar_entrada_no_caixa(client, mei):
    cid = _cliente(client, mei["h"])
    f = _fatura(client, mei["h"], cid, 700, "2030-01-01", "2030-01-31").json()
    client.patch(f"/faturas/{f['id_fatura']}/pagar", headers=mei["h"], json={"data_pagamento": "2030-01-20", "id_conta": mei["conta"], "id_categoria": mei["cat_e"]})
    assert float(client.get("/contas", headers=mei["h"]).json()[0]["saldo"]) == 700.0


def test_cliente_inadimplente_recorrente_e_bloqueado(client, auth):  # RN13
    cid = _cliente(client, auth)
    for i in range(3):
        _fatura(client, auth, cid, 100 + i, f"2020-0{i + 1}-01", f"2020-0{i + 1}-28")
    r = client.post("/faturas/atualizar-status", headers=auth).json()
    assert r["clientes_bloqueados"] == 1
    assert _fatura(client, auth, cid, 999, "2030-01-01", "2030-01-31").status_code == 409
    assert len(client.get("/faturas", headers=auth).json()) == 3  # o histórico é mantido
    client.patch(f"/clientes/{cid}/desbloquear", headers=auth)
    assert _fatura(client, auth, cid, 999, "2030-01-01", "2030-01-31").status_code == 201


def test_emitir_nota(client, auth):
    f = _fatura(client, auth, _cliente(client, auth, "Empresa", "PJ"), 100, "2030-01-01", "2030-01-31").json()
    assert client.patch(f"/faturas/{f['id_fatura']}/nota", headers=auth).json()["nota_emitida"] is True


# ---------------------------------------------------------------- notificações
def test_notificacoes_sem_repeticao(client, mei):
    garantir_tabela(ANO)
    cid = _cliente(client, mei["h"])
    _fatura(client, mei["h"], cid, 100, "2020-01-01", "2020-01-31")
    client.post("/impostos/obrigacoes/gerar", headers=mei["h"])
    primeira = client.post("/notificacoes/gerar", headers=mei["h"]).json()
    tipos = {n["tipo"] for n in primeira}
    assert {"SALDO_BAIXO", "FATURA_ATRASADA"} <= tipos
    assert client.post("/notificacoes/gerar", headers=mei["h"]).json() == []
    n = client.get("/notificacoes", headers=mei["h"]).json()[0]
    assert client.patch(f"/notificacoes/{n['id_notificacao']}/lida", headers=mei["h"]).json()["lida"] is True


def test_notificacao_respeita_preferencias(client, mei):
    client.put("/usuarios/me/preferencias", headers=mei["h"], json={"notif_saldo": False, "notif_fatura": False, "notif_das": False, "notif_dasn": False, "notif_teto": False})
    assert client.post("/notificacoes/gerar", headers=mei["h"]).json() == []


# ---------------------------------------------------------------- precificação, metas, investimentos
def test_precificacao_embute_o_das(client, mei):
    garantir_tabela(ANO)
    s = client.post("/servicos", headers=mei["h"], json={"nome": "Criação de site", "horas_trabalho": "20", "custo_materiais": "80", "outros_custos": "120"}).json()
    r = client.post("/precificacao/calcular", headers=mei["h"], json={"id_servico": s["id_servico"], "margem_lucro": "30", "custo_hora": "40", "servicos_por_mes": 4}).json()
    assert float(r["preco_minimo"]) == 1459.30 and float(r["das_mensal"]) == 86.05
    assert float(client.get("/servicos", headers=mei["h"]).json()[0]["precificacao"]["valor_sugerido"]) == 1459.30


def test_servico_invalido(client, mei):
    assert client.post("/servicos", headers=mei["h"], json={"nome": "x", "horas_trabalho": "0"}).status_code == 422


def test_metas_com_aporte_e_conclusao(client, auth):
    meta = client.post("/metas", headers=auth, json={"nome": "Notebook", "valor_objetivo": "1000", "prazo": "2030-12-20"}).json()
    r = client.post(f"/metas/{meta['id_meta']}/aporte", headers=auth, json={"valor": "400"}).json()
    assert float(r["valor_atual"]) == 400.0 and r["status"] == "ATIVA"
    r = client.post(f"/metas/{meta['id_meta']}/aporte", headers=auth, json={"valor": "600"}).json()
    assert r["status"] == "CONCLUIDA"
    assert client.post(f"/metas/{meta['id_meta']}/aporte", headers=auth, json={"valor": "1"}).status_code == 409
    assert client.post(f"/metas/{meta['id_meta']}/aporte", headers=auth, json={"valor": "0"}).status_code == 422


def test_assinatura_premium_libera_investimentos(client, auth):
    assert client.get("/investimentos/propostas", headers=auth).status_code == 403
    assert client.post("/assinaturas", headers=auth, json={}).status_code == 201
    assert client.post("/assinaturas", headers=auth, json={}).status_code == 409
    prop = client.post("/investimentos/recomendacao", headers=auth, json={"valor_disponivel": "1000", "perfil_risco": "CONSERVADOR"})
    assert prop.status_code == 201 and prop.json()["risco"] == "Baixo" and float(prop.json()["rentabilidade_estimada"]) == 10.5
    pid = prop.json()["id_proposta"]
    assert client.patch(f"/investimentos/propostas/{pid}", headers=auth, json={"status": "ACEITA"}).json()["status"] == "ACEITA"
    assert client.patch(f"/investimentos/propostas/{pid}", headers=auth, json={"status": "RECUSADA"}).status_code == 409
    client.post("/investimentos/aplicacoes", headers=auth, json={"nome": "Tesouro Selic", "tipo": "TESOURO", "valor_atual": "4200", "data_aplicacao": "2026-01-10"})
    assert float(client.get("/investimentos/carteira", headers=auth).json()["total"]) == 4200.0
    assert client.get("/investimentos/cotacoes", headers=auth).json()["cotacoes"][0]["simbolo"] == "CDI"  # cache local


def test_cancelar_assinatura_volta_ao_normal(client, auth):
    client.post("/assinaturas", headers=auth, json={})
    assert client.delete("/assinaturas/minha", headers=auth).json()["status"] == "CANCELADA"
    assert client.get("/usuarios/me", headers=auth).json()["perfil"] == "NORMAL"
    assert client.get("/investimentos/propostas", headers=auth).status_code == 403


def test_rentabilidade_do_arrojado_nao_e_prometida(client, auth):
    client.post("/assinaturas", headers=auth, json={})
    r = client.post("/investimentos/recomendacao", headers=auth, json={"valor_disponivel": "500", "perfil_risco": "ARROJADO"}).json()
    assert r["rentabilidade_estimada"] is None and r["risco"] == "Alto"


# ---------------------------------------------------------------- dashboards e admin
def test_dashboard_do_mei(client, mei):
    garantir_tabela(ANO)
    hoje = date.today()
    lancar(client, mei, "ENTRADA", 6000, hoje.isoformat())
    lancar(client, mei, "SAIDA", 500, hoje.isoformat())
    client.post("/impostos/cota-mensal", headers=mei["h"])
    d = client.get("/dashboard", headers=mei["h"]).json()
    assert float(d["fluxo_mes"]["entradas"]) == 6000.0 and d["teto"]["nivel"] == "NORMAL" and d["proximo_das"]["descricao"].startswith("DAS")


def test_admin_gerencia_usuarios(client, auth, admin):
    novo = client.post("/admin/usuarios", headers=admin, json={"nome": "Carlos Lima", "email": "carlos@x.com", "senha": "senha123", "perfil": "PREMIUM"})
    assert novo.status_code == 201 and novo.json()["perfil"] == "PREMIUM" and "senha" not in novo.json()
    assert client.post("/admin/usuarios", headers=admin, json={"nome": "Carlos", "email": "carlos@x.com", "senha": "senha123"}).status_code == 409
    uid = client.get("/usuarios/me", headers=auth).json()["id_usuario"]
    assert client.patch(f"/admin/usuarios/{uid}", headers=admin, json={"perfil": "PREMIUM"}).json()["perfil"] == "PREMIUM"
    client.patch(f"/admin/usuarios/{uid}", headers=admin, json={"ativo": False})
    assert client.get("/usuarios/me", headers=auth).status_code == 401  # desativado perde o acesso
    assert client.post("/auth/login", json={"email": "ana@teste.com", "senha": "segredo123"}).status_code == 401
    assert [u["email"] for u in client.get("/admin/usuarios?busca=carlos", headers=admin).json()] == ["carlos@x.com"]
    meu_id = client.get("/usuarios/me", headers=admin).json()["id_usuario"]
    assert client.patch(f"/admin/usuarios/{meu_id}", headers=admin, json={"perfil": "NORMAL"}).status_code == 409


def test_admin_edita_tabela_das_e_isso_muda_o_calculo(client, mei, admin):
    corpo = {"salario_minimo": "1800.00", "teto_anual": "81000", "teto_caminhoneiro": "251600", "fonte": "Teste"}
    assert client.put("/admin/tabela-das/2027", headers=admin, json=corpo).status_code == 200
    assert float(client.get("/impostos/das?ano=2027", headers=mei["h"]).json()["total"]) == 95.0   # 5% de 1.800 + ISS 5
    assert len(client.get("/admin/tabela-das", headers=admin).json()) == 2
    logs = client.get("/admin/logs", headers=admin).json()
    assert any("Tabela DAS 2027" in x["acao"] for x in logs)


def test_admin_configuracoes_do_sistema(client, admin):
    r = client.put("/admin/configuracoes", headers=admin, json={"percentual_alerta_padrao": "75", "dias_aviso_das": 5, "dias_aviso_dasn": 45})
    assert r.json()["percentual_alerta_padrao"] == "75" and client.get("/admin/configuracoes", headers=admin).json()["dias_aviso_dasn"] == "45"


def test_dashboard_admin_controle(client, mei, admin):
    garantir_tabela(ANO)
    lancar(client, mei, "ENTRADA", 75000, date.today().isoformat())  # 92,6% do teto
    d = client.get("/admin/dashboard", headers=admin).json()
    assert d["usuarios"] == 1 and d["perto_do_teto"] == 1 and d["perfis"]["ADMIN"] == 1
    assert any(a["motivo"] == "Teto" for a in d["atencao"]) and len(d["cadastros_por_mes"]) == 6
    assert d["saude"]["api"] == "online" and "banco" not in str(d["saude"]).lower()


def test_dashboard_de_vendas(client, auth, admin):
    client.post("/assinaturas", headers=auth, json={})
    v = client.get("/admin/vendas", headers=admin).json()
    assert float(v["receita_mes"]) == 19.9 and v["assinantes_premium"] == 1 and float(v["conversao_percentual"]) == 100.0
    assert v["ultimas_assinaturas"][0]["plano"] == "PREMIUM" and v["funil"]["cadastrados"] == 1
    assert client.get("/planos").json()[1]["nome"] == "PREMIUM"


def test_planejar_salario_e_nao_alterar_mes_fechado(client, mei):
    corpo = {"ano": 2026, "mes": 9, "valor_desejado": "3000"}
    assert client.put("/retiradas/planejar", headers=mei["h"], json=corpo).json()["status"] == "PLANEJADA"
    assert client.put("/retiradas/planejar", headers=mei["h"], json={**corpo, "valor_desejado": "3500"}).json()["valor_desejado"] in ("3500.00", 3500.0)
    lancar(client, mei, "ENTRADA", 5000, "2026-09-10")
    r = client.post("/suavizacao/fechar-mes", headers=mei["h"], json={"ano": 2026, "mes": 9, "salario_desejado": "3500"})
    assert r.status_code == 200 and float(r.json()["retirada"]) == 3500.0
    assert client.put("/retiradas/planejar", headers=mei["h"], json=corpo).status_code == 409


def test_rentabilidade_media_da_carteira(client, auth):
    client.post("/assinaturas", headers=auth, json={})
    for nome, tipo, valor, rent in (("A", "TESOURO", "1000", "10"), ("B", "RENDA_FIXA", "3000", "12")):
        client.post("/investimentos/aplicacoes", headers=auth, json={"nome": nome, "tipo": tipo, "valor_atual": valor, "rentabilidade": rent, "data_aplicacao": "2026-01-10"})
    assert float(client.get("/investimentos/carteira", headers=auth).json()["rentabilidade_media"]) == 11.5


def test_cobranca_mensal_simulada_e_idempotente(client, auth, admin):
    client.post("/assinaturas", headers=auth, json={})
    with SessionLocal() as db:
        a = db.query(m.Assinatura).first()
        a.data_inicio = date(ANO, 1, 10)
        db.commit()
    hoje = date.today()
    esperado = hoje.month - 1  # a assinatura já tem o pagamento de hoje; faltam os meses anteriores
    r = client.post("/admin/assinaturas/cobrar", headers=admin).json()
    assert r["pagamentos_criados"] == esperado or r["pagamentos_criados"] == esperado + 1
    assert client.post("/admin/assinaturas/cobrar", headers=admin).json()["pagamentos_criados"] == 0
