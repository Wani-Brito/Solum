from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings

_args = {}
_kw = {"pool_pre_ping": True}  # o Neon suspende conexões ociosas
if settings.database_url.startswith("sqlite"):
    _args = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        _kw["poolclass"] = StaticPool

engine = create_engine(settings.database_url, connect_args=_args, **_kw)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
