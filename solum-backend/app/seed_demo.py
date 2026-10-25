"""Dados de demonstração para a apresentação.  Uso:  python -m app.seed_demo

Cria um administrador, a usuária de demonstração (com 8 meses de dados reais calculados pelas regras do sistema)
e alguns outros usuários para os dashboards do administrador."""
import os
from datetime import date, datetime
from decimal import Decimal

from . import models as m
from .database import SessionLocal, engine
from .schemas import (AplicacaoIn, ClienteIn, FaturaIn, MeiIn, MetaIn, PlanejarRetiradaIn, ServicoIn, TransacaoIn)
from .security import hash_senha
from .seed import dados_iniciais
from .servicos import (ServicoAssinaturas, ServicoFaturas, ServicoFechamentoMensal, ServicoImposto, ServicoInvestimentos,
                       ServicoMei, ServicoMetas, ServicoNotificacoes, ServicoTransacoes)

SENHA_ADMIN = os.environ.get("ADMIN_SENHA", "admin123")
SENHA_DEMO = "12345678"
HOJE = date.today() if date.today().year == 2026 and date.today().month >= 2 else date(2026, 10, 17)


def _usuario(db, nome, email, senha, perfil="NORMAL", cadastro=None):
    u = db.query(m.Usuario).filter_by(email=email).first()
    if u:
        return u, False
    u = m.Usuario(nome=nome, email=email, senha=hash_senha(senha), perfil=perfil, telefone="(19) 90000-0000",
                  data_cadastro=cadastro or datetime.now())
    db.add(u)
    db.flush()
    db.add(m.PreferenciasUsuario(id_usuario=u.id_usuario))
    db.commit()
    return u, True


def _estrutura(db, u, tipo="SERVICO", abertura=date(2024, 3, 10)):
    ServicoMei(db).salvar(u, MeiIn(tipo_atividade=tipo, categoria="PADRAO", cnae="6201501", data_abertura=abertura, nome_fantasia=f"{u.nome} Serviços", cidade="Indaiatuba", uf="SP"))
    contas = {n: m.Conta(id_usuario=u.id_usuario, nome=n, banco=n, saldo=0) for n in ("Nubank", "Inter")}
    cats = {(n, t): m.Categoria(id_usuario=u.id_usuario, nome=n, tipo=t) for n, t in (("Serviços", "ENTRADA"), ("Ferramentas", "SAIDA"), ("Custos fixos", "SAIDA"))}
    db.add_all(list(contas.values()) + list(cats.values()))
    db.commit()
    return contas, cats


def _lancar(db, u, conta, cat, tipo, valor, data, desc):
    ServicoTransacoes(db).criar(u, TransacaoIn(id_conta=conta.id_conta, id_categoria=cat.id_categoria, descricao=desc, valor=Decimal(str(valor)), data=data, tipo=tipo))


def demo_principal(db):
    u, novo = _usuario(db, "Emilly", "emilly@email.com", SENHA_DEMO, "NORMAL", datetime(2026, 1, 5))
    if not novo:
        return
    contas, cats = _estrutura(db, u)
    nu, it = contas["Nubank"], contas["Inter"]
    ent, fer, fixo = cats[("Serviços", "ENTRADA")], cats[("Ferramentas", "SAIDA")], cats[("Custos fixos", "SAIDA")]
    historico = [(1, 6000, 500), (2, 1800, 300), (3, 4200, 400), (4, 900, 200), (5, 7000, 100), (6, 1100, 150), (7, 300, 100), (8, 4800, 600), (9, 5200, 500)]
    for mes, receita, despesa in [h for h in historico if h[0] < HOJE.month]:
        _lancar(db, u, nu, ent, "ENTRADA", receita, date(2026, mes, 10), f"Projetos de {mes:02d}/2026")
        _lancar(db, u, it, fixo, "SAIDA", despesa, date(2026, mes, 11), f"Custos de {mes:02d}/2026")
        ServicoFechamentoMensal(db).fechar(u, 2026, mes, Decimal("3000"))
    # mês atual: ainda aberto, com o salário planejado
    mes = HOJE.month
    _lancar(db, u, nu, ent, "ENTRADA", 2500, date(2026, mes, 12), "Projeto site - Cliente A")
    _lancar(db, u, nu, ent, "ENTRADA", 1200, date(2026, mes, 10), "Pix - Cliente B")
    _lancar(db, u, nu, ent, "ENTRADA", 2300, date(2026, mes, 3), "Manutenção mensal - Cliente C")
    _lancar(db, u, it, fer, "SAIDA", 120, date(2026, mes, 8), "Licença de software")
    _lancar(db, u, it, fixo, "SAIDA", 110, date(2026, mes, 5), "Internet")
    _lancar(db, u, it, fixo, "SAIDA", 270, date(2026, mes, 2), "Coworking")
    r = db.query(m.RetiradaMensal).filter_by(id_usuario=u.id_usuario, ano=2026, mes=mes).first() or m.RetiradaMensal(id_usuario=u.id_usuario, ano=2026, mes=mes, valor=0)
    r.valor_desejado, r.status = Decimal("3000"), "PLANEJADA"
    db.add(r)
    db.commit()
    ServicoImposto(db).cota_mensal(u, 2026, mes, HOJE)
    for o in db.query(m.ObrigacaoImposto).filter_by(id_usuario=u.id_usuario).all():  # a usuária já pagou os DAS vencidos
        if o.descricao.startswith("DAS ") and o.data_vencimento < date(2026, mes, 1):
            o.status = "PAGO"
    db.commit()
    # clientes, faturas, serviço, metas e investimentos
    pj = m.Cliente(id_usuario=u.id_usuario, nome="Studio Aurora Ltda", tipo_pessoa="PJ", email="contato@aurora.com")
    pf = m.Cliente(id_usuario=u.id_usuario, nome="Cliente B", tipo_pessoa="PF")
    db.add_all([pj, pf])
    db.commit()
    fat = ServicoFaturas(db)
    fat.criar(u, FaturaIn(id_cliente=pj.id_cliente, descricao="Projeto site", valor=Decimal("2500"), data_emissao=date(2026, 9, 12), data_vencimento=date(2026, 10, 12)))
    fat.criar(u, FaturaIn(id_cliente=pf.id_cliente, descricao="Manutenção de agosto", valor=Decimal("800"), data_emissao=date(2026, 8, 30), data_vencimento=date(2026, 9, 15)))
    f3 = fat.criar(u, FaturaIn(id_cliente=pj.id_cliente, descricao="Identidade visual", valor=Decimal("1800"), data_emissao=date(2026, 8, 1), data_vencimento=date(2026, 8, 20)))
    f3.status, f3.data_pagamento = "PAGA", date(2026, 8, 18)
    db.commit()
    db.add(m.Servico(id_usuario=u.id_usuario, nome="Criação de site", descricao="Site institucional", horas_trabalho=Decimal("20"), custo_materiais=Decimal("80"), outros_custos=Decimal("120")))
    db.commit()
    for nome, objetivo, atual, prazo in (("Notebook novo", 6000, 3300, date(2026, 12, 20)), ("Fundo de emergência", 10000, 3000, date(2027, 6, 30)), ("Curso de UX", 1000, 1000, date(2026, 9, 15))):
        meta = m.MetaFinanceira(id_usuario=u.id_usuario, nome=nome, valor_objetivo=Decimal(objetivo), prazo=prazo)
        db.add(meta)
        db.commit()
        ServicoMetas(db).aportar(u, meta.id_meta, Decimal(atual))
    ServicoAssinaturas(db).assinar(u, "PREMIUM")
    cart = ServicoInvestimentos(db).carteira(u)
    for nome, tipo, valor, rent, prazo in (("Tesouro Selic", "TESOURO", 4200, "10.50", "2 anos"), ("CDB 110% CDI", "RENDA_FIXA", 3000, "11.55", "1 ano"), ("Fundo DI", "FUNDOS", 1250, "9.80", "6 meses")):
        db.add(m.Investimento(id_carteira=cart.id_carteira, nome=nome, tipo=tipo, valor_atual=Decimal(valor), rentabilidade=Decimal(rent), prazo=prazo, data_aplicacao=date(2026, 2, 10)))
    db.commit()
    ServicoNotificacoes(db).gerar(u, HOJE)


def outros_usuarios(db):
    pessoas = [("Marina Souza", "marina@email.com", "PREMIUM", datetime(2026, 8, 12)), ("Carlos Lima", "carlos@email.com", "NORMAL", datetime(2026, 10, 3)),
               ("Joana Reis", "joana@email.com", "NORMAL", datetime(2026, 10, 15)), ("Pedro Alves", "pedro@email.com", "PREMIUM", datetime(2026, 9, 21)),
               ("Lúcia Tavares", "lucia@email.com", "NORMAL", datetime(2026, 6, 2))]
    for nome, email, perfil, cad in pessoas:
        u, novo = _usuario(db, nome, email, SENHA_DEMO, "NORMAL", cad)
        if not novo:
            continue
        contas, cats = _estrutura(db, u)
        nu, ent = contas["Nubank"], cats[("Serviços", "ENTRADA")]
        if nome.startswith("Marina"):
            _lancar(db, u, nu, ent, "ENTRADA", 75000, date(2026, 2, 1), "Contratos do ano")  # 92,6% do teto
        elif nome.startswith("Carlos"):
            _lancar(db, u, nu, ent, "ENTRADA", 1500, date(2026, 8, 5), "Projeto")
            ServicoImposto(db).gerar_obrigacoes(u, 2026)
        elif nome.startswith("Joana"):
            _lancar(db, u, nu, ent, "ENTRADA", 800, date(2026, 8, 5), "Projeto pequeno")
            ServicoFechamentoMensal(db).fechar(u, 2026, 8, Decimal("3000"))
        else:
            _lancar(db, u, nu, ent, "ENTRADA", 2000, date(2026, 5, 5), "Projeto")
        if perfil == "PREMIUM":
            ServicoAssinaturas(db).assinar(u, "PREMIUM")
    for email, inicio in (("emilly@email.com", date(2026, 2, 10)), ("marina@email.com", date(2026, 6, 12)), ("pedro@email.com", date(2026, 8, 21))):
        us = db.query(m.Usuario).filter_by(email=email).first()
        a = db.query(m.Assinatura).filter_by(id_usuario=us.id_usuario, status="ATIVA").first()
        if a:
            a.data_inicio = inicio
            db.query(m.Pagamento).filter_by(id_assinatura=a.id_assinatura).delete()
    db.commit()
    lucia = db.query(m.Usuario).filter_by(email="lucia@email.com").first()
    if lucia and not db.query(m.Assinatura).filter_by(id_usuario=lucia.id_usuario).first():
        ServicoAssinaturas(db).assinar(lucia, "PREMIUM")
        ServicoAssinaturas(db).cancelar(lucia)
    ServicoAssinaturas(db).cobrar_mensalidades(HOJE)


def main():
    m.Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        dados_iniciais(db)
        admin, novo = _usuario(db, "Admin Solum", "admin@solum.app", SENHA_ADMIN, "ADMIN", datetime(2026, 1, 1))
        if novo:
            admin.perfil = "ADMIN"
            db.add(m.LogAdmin(id_admin=admin.id_usuario, acao="Editou a Tabela DAS 2026", alvo="2026"))
            db.commit()
        demo_principal(db)
        outros_usuarios(db)
    print("Dados de demonstração prontos.")
    print(f"  Administrador: admin@solum.app / {SENHA_ADMIN}   (troque a senha em produção)")
    print(f"  Usuária demo : emilly@email.com / {SENHA_DEMO}")


if __name__ == "__main__":
    main()
