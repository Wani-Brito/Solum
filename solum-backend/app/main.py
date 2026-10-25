"""API do Solum (FastAPI). Execute com:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import SessionLocal, engine
from .models import Base
from .routers import admin, auth, financeiro, fiscal
from .servicos import RegraNegocio


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # cria as tabelas que ainda não existem
    from .seed import dados_iniciais
    with SessionLocal() as db:
        dados_iniciais(db)  # planos, Tabela DAS 2026 e cotações de exemplo (só se estiverem vazios)
    yield


app = FastAPI(title="Solum API", version="1.0",
              description="Gestão financeira para MEIs com renda irregular: salário sintético, reserva de imposto (DAS), teto anual, faturas e investimentos.",
              lifespan=ciclo_de_vida)

app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RegraNegocio)
async def _regra(request: Request, exc: RegraNegocio):
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def _valor(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/", tags=["Sistema"])
def raiz():
    return {"status": "online", "sistema": "Solum API", "versao": "1.0"}


for r in (auth.router, financeiro.router, fiscal.router, admin.router):
    app.include_router(r)
