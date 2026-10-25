"""Gera o schema.sql (PostgreSQL) a partir dos modelos. Uso:  python gerar_schema.py"""
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import Base

partes = ["-- SOLUM - Modelo de banco de dados (PostgreSQL)\n-- Gerado a partir de app/models.py. Para recriar o banco do zero: psql -f schema.sql\n"]
for tabela in Base.metadata.sorted_tables:
    partes.append(str(CreateTable(tabela).compile(dialect=postgresql.dialect())).strip() + ";")
    for idx in sorted(tabela.indexes, key=lambda i: i.name):
        partes.append(str(CreateIndex(idx).compile(dialect=postgresql.dialect())).strip() + ";")
open("schema.sql", "w", encoding="utf-8").write("\n\n".join(partes) + "\n")
print(f"schema.sql gerado com {len(Base.metadata.sorted_tables)} tabelas")
