# Solum

O Solum é um sistema em Python orientado a objetos que garante estabilidade financeira a MEIs com renda irregular. Ele cria um "salário sintético" suave, calcula o imposto DAS, monitora o teto de faturamento, auxilia na precificação de serviços e exibe cotações de investimento.

## Backend

O backend está em `backend/app.py`. Antes de iniciar a API, configure a variável de ambiente `DATABASE_URL` com a URL do PostgreSQL. Use `.env.example` como referência e mantenha credenciais reais fora do repositório.

Instale as dependências e inicie a API:

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload
```
