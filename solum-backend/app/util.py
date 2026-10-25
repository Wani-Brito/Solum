def linha(obj, excluir=("senha",)) -> dict:
    """Converte uma linha do banco em dict (para respostas JSON)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in excluir}
