"""Configurações lidas de variáveis de ambiente (ou do arquivo .env)."""
import os
from dotenv import load_dotenv

load_dotenv()


def normalizar_url(url: str) -> str:
    """Provedores como o Neon entregam 'postgres://...'; o SQLAlchemy 2 exige 'postgresql://...'."""
    return "postgresql://" + url[len("postgres://"):] if url.startswith("postgres://") else url


class Settings:
    # PostgreSQL em produção (ex.: Neon). Sem DATABASE_URL, usa SQLite local só para desenvolvimento.
    database_url: str = normalizar_url(os.environ.get("DATABASE_URL") or "sqlite:///./solum_dev.db")
    secret_key: str = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
    token_minutos: int = int(os.environ.get("TOKEN_MINUTOS", "480"))
    allowed_origins: list[str] = [
        o.strip()
        for o in os.environ.get(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:8081,http://localhost:19006,http://localhost:3000",
        ).split(",")
        if o.strip()
    ]
    cotacoes_online: bool = os.environ.get("COTACOES_ONLINE", "0") == "1"


settings = Settings()
