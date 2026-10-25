from app.config import normalizar_url


def test_url_do_neon_e_normalizada():
    assert normalizar_url("postgres://u:s@host/db?sslmode=require") == "postgresql://u:s@host/db?sslmode=require"
    assert normalizar_url("postgresql://u:s@host/db") == "postgresql://u:s@host/db"
    assert normalizar_url("sqlite:///./x.db") == "sqlite:///./x.db"
