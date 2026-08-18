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
    """Создаёт таблицы и применяет лёгкие миграции при старте."""
    from app import models  # noqa: F401  — регистрация модели

    Base.metadata.create_all(bind=engine)
    _migrate()
    _backfill()


def _migrate() -> None:
    """Добавляет отсутствующие колонки к существующей таблице listings."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "listings" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("listings")}
    additions = {
        "price_value": "FLOAT",
        "rooms": "INTEGER",
        "district": "VARCHAR(128)",
        "source": "VARCHAR(16)",
        "channel": "VARCHAR(128)",
    }
    for name, col_type in additions.items():
        if name not in existing:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE listings ADD COLUMN {name} {col_type}"))


def _backfill() -> None:
    """Заполняет новые поля для уже сохранённых объявлений."""
    from sqlalchemy import or_

    from app.models import Listing
    from app.parser.extract import parse_district, parse_price_value, parse_rooms

    session = SessionLocal()
    try:
        rows = (
            session.query(Listing)
            .filter(
                or_(
                    Listing.price_value.is_(None),
                    Listing.rooms.is_(None),
                    Listing.district.is_(None),
                )
            )
            .all()
        )
        changed = False
        for row in rows:
            if row.price_value is None and row.price:
                row.price_value = parse_price_value(row.price)
                changed = True
            if row.rooms is None and row.title:
                row.rooms = parse_rooms(row.title)
                changed = True
            if row.district is None:
                row.district = parse_district(row.title, row.location)
                if row.district is not None:
                    changed = True
        if changed:
            session.commit()
    finally:
        session.close()
