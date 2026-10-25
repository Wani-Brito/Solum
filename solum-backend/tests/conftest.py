import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "chave-de-teste"

import pytest
from fastapi.testclient import TestClient

from app import models as m
from app.database import SessionLocal, engine
from app.main import app
from app.security import hash_senha


@pytest.fixture()
def client():
    m.Base.metadata.drop_all(bind=engine)
    with TestClient(app) as c:
        yield c


def _auth(client, email="ana@teste.com", nome="Ana Teste"):
    r = client.post("/auth/registro", json={"nome": nome, "email": email, "senha": "segredo123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    return _auth(client)


@pytest.fixture()
def outro(client):
    return _auth(client, "bia@teste.com", "Bia Teste")


@pytest.fixture()
def admin(client):
    with SessionLocal() as db:
        db.add(m.Usuario(nome="Admin", email="admin@teste.com", senha=hash_senha("admin123"), perfil="ADMIN"))
        db.commit()
    r = client.post("/auth/login", json={"email": "admin@teste.com", "senha": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def mei(client, auth):
    """Usuário com MEI de serviço (DAS 2026 = R$ 86,05), uma conta e categorias."""
    r = client.put("/mei", headers=auth, json={"tipo_atividade": "SERVICO", "categoria": "PADRAO", "cnae": "6201501", "data_abertura": "2024-03-10"})
    assert r.status_code == 200, r.text
    conta = client.post("/contas", headers=auth, json={"nome": "Nubank", "banco": "Nubank"}).json()
    cat_e = client.post("/categorias", headers=auth, json={"nome": "Serviços", "tipo": "ENTRADA"}).json()
    cat_s = client.post("/categorias", headers=auth, json={"nome": "Custos", "tipo": "SAIDA"}).json()
    return {"h": auth, "conta": conta["id_conta"], "cat_e": cat_e["id_categoria"], "cat_s": cat_s["id_categoria"]}


def lancar(client, mei, tipo, valor, data, desc="Lançamento", ligada=True):
    r = client.post("/transacoes", headers=mei["h"], json={
        "id_conta": mei["conta"], "id_categoria": mei["cat_e"] if tipo == "ENTRADA" else mei["cat_s"],
        "descricao": desc, "valor": str(valor), "data": data, "tipo": tipo, "ligada_atividade": ligada})
    return r
