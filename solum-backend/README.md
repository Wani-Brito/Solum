# Solum: API (backend)

API em Python (FastAPI) com o núcleo de regras de negócio em POO, banco PostgreSQL e testes automatizados.

## Requisitos

- Python 3.11 ou mais novo
- PostgreSQL (por exemplo, no Neon). Sem banco configurado, a API usa um SQLite local só para desenvolvimento.

## Como rodar (Windows)

```bat
cd solum-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

No Linux ou Mac: `source venv/bin/activate` e `cp .env.example .env`.

A API sobe em http://localhost:8000 e a documentação interativa fica em http://localhost:8000/docs.

## Configuração (.env)

| Variável | Para que serve |
| --- | --- |
| DATABASE_URL | Conexão do PostgreSQL, ex.: `postgresql://usuario:senha@host/banco?sslmode=require`. Aceita também o formato `postgres://` do Neon. |
| SECRET_KEY | Chave que assina os tokens de login. Gere uma com `python -c "import secrets; print(secrets.token_hex(32))"`. |
| ALLOWED_ORIGINS | Endereços do painel web e do app autorizados a chamar a API (CORS). |
| COTACOES_ONLINE | `1` busca CDI e Selic no Banco Central; `0` usa só o cache. |
| ADMIN_SENHA | Senha do administrador criado pelo seed de demonstração. |

Ao iniciar, a API cria as tabelas que faltam e cadastra os dados iniciais (planos, Tabela DAS 2026 e cotações de exemplo). Se preferir criar o banco na mão, use `schema.sql` (`psql -f schema.sql`).

## Dados de demonstração

```bat
python -m app.seed_demo
```

Cria o administrador (`admin@solum.app`, senha `admin123` ou a de ADMIN_SENHA), a usuária de demonstração (`emilly@email.com`, senha `12345678`) com oito meses de dados e outros usuários para os dashboards. Troque essas senhas antes de qualquer uso real.

## Testes

```bat
pytest
pytest --cov=app --cov-report=term
```

Os testes usam SQLite em memória e cobrem as regras de domínio (RN05 a RN16, incluindo os sete meses do exemplo da suavização) e as rotas da API (token, perfis, fluxo de caixa, fechamento do mês, faturas, investimentos, painel do administrador). Repita a verificação no PostgreSQL real do grupo.

## Estrutura

```
app/
  main.py            aplicação, CORS e tratamento de erros
  config.py          variáveis de ambiente
  database.py        conexão (PostgreSQL ou SQLite de desenvolvimento)
  models.py          32 tabelas (SQLAlchemy)
  security.py        hash de senha, token JWT, perfis (Normal, Premium, Admin)
  schemas.py         validação das entradas
  dominio/           regras de negócio em POO, sem banco
    transacao.py       Transacao (abstrata), Entrada, Saida, fábrica
    fluxo.py           FluxoCaixa
    reserva.py         ReservaEstabilizacao (saldo encapsulado)
    suavizacao.py      ServicoSuavizacao (RN06 a RN09)
    das.py             CalculadoraDAS (Strategy): comércio, serviço, ambos
    teto.py            teto anual e desenquadramento (RN05)
    precificacao.py    preço mínimo (RN14)
    fatura.py          status, nota fiscal e bloqueio (RN10 a RN13)
    notificacao.py     avisos (RN17 a RN21)
    chatbot.py         interpreta "Gastei 150 com internet"
  servicos.py        serviços que ligam domínio e banco
  servicos_painel.py dashboards do MEI e do administrador
  routers/           rotas: auth, financeiro, fiscal, admin
  seed.py            dados iniciais
  seed_demo.py       dados de demonstração
tests/               testes automatizados
schema.sql           script do banco (gerado por gerar_schema.py)
```

## Perfis e acesso

- Todas as rotas, exceto `/`, `/planos`, `/auth/login` e `/auth/registro`, exigem o token (`Authorization: Bearer ...`).
- Investimentos exige Premium (ou Admin). As rotas `/admin/*` exigem Admin.
- Quem se cadastra entra como Normal. O perfil só muda pelo painel do administrador ou pela assinatura do Premium (pagamento simulado).

## Problemas comuns

- `psycopg2` não instala: use a versão binária já listada (`psycopg2-binary`) e um Python 3.11 a 3.13.
- Erro de CORS no painel: confira `ALLOWED_ORIGINS` no `.env` e reinicie a API.
- "Tabela DAS de AAAA ainda não foi cadastrada": cadastre o ano no painel do administrador (Tabela DAS).
