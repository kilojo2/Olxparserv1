"""Подключение к базе данных (SQLite локально, PostgreSQL на Railway)."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _build_db_url() -> str:
    url = settings.database_url
    # Railway иногда выдаёт схему postgres:// — SQLAlchemy ожидает postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


connect_args = {}
if _build_db_url().startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(_build_db_url(), connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    """FastAPI-зависимость: выдаёт сессию БД на время обработки запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Создаёт таблицы при старте приложения."""
    from app import models  # noqa: F401  — регистрация модели

    Base.metadata.create_all(bind=engine)
