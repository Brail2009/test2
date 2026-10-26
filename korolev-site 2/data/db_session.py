"""
Инициализация SQLAlchemy и фабрика сессий.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

_engine = None
_session_factory = None


def global_init(db_path: str) -> None:
    """Инициализирует движок и создаёт таблицы. Вызывается один раз при старте."""
    global _engine, _session_factory
    if _engine is not None:
        return

    db_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    url = f"sqlite:///{db_path}"

    _engine = create_engine(
        url,
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(_engine)
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)


def create_session():
    """Возвращает новую сессию SQLAlchemy. Закрывайте через with."""
    if _session_factory is None:
        raise RuntimeError("DB не инициализирована. Вызовите global_init() сначала.")
    return _session_factory()