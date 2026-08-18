"""Модель объявления (SQLAlchemy)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.db import Base
from app.parser.date_parser import kiev_now


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    olx_id = Column(String(64), unique=True, index=True, nullable=False)
    url = Column(String(512), unique=True, index=True, nullable=False)
    title = Column(String(512), nullable=True)
    price = Column(String(128), nullable=True)
    area = Column(String(64), nullable=True)
    location = Column(String(256), nullable=True)
    price_value = Column(Float, nullable=True, index=True)
    rooms = Column(Integer, nullable=True, index=True)
    district = Column(String(128), nullable=True, index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    first_seen_at = Column(DateTime, default=kiev_now, nullable=False)
    last_seen_at = Column(DateTime, default=kiev_now, onupdate=kiev_now, nullable=False)

    def to_dict(self) -> dict:
        def _iso(value: Optional[datetime]) -> Optional[str]:
            return value.isoformat(sep=" ") if value else None

        return {
            "id": self.id,
            "olx_id": self.olx_id,
            "url": self.url,
            "title": self.title,
            "price": self.price,
            "price_value": self.price_value,
            "rooms": self.rooms,
            "area": self.area,
            "location": self.location,
            "district": self.district,
            "published_at": _iso(self.published_at),
            "first_seen_at": _iso(self.first_seen_at),
        }
