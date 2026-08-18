"""REST API: список объявлений с фильтрами, ручной запуск, статус."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import db
from app.config import settings
from app.models import Listing
from app.scheduler import get_last_result, get_next_run_at, run_now

router = APIRouter(prefix="/api")


def _parse_date(value: str, end_of_day: bool = False) -> datetime:
    dt = datetime.strptime(value, "%Y-%m-%d")
    if end_of_day:
        return dt.replace(hour=23, minute=59, second=59)
    return dt


@router.get("/listings")
def list_listings(
    limit: int = 500,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rooms: Optional[int] = None,
    district: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    session: Session = Depends(db.get_db),
):
    query = session.query(Listing)

    if min_price is not None:
        query = query.filter(Listing.price_value >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price_value <= max_price)
    if rooms is not None:
        query = query.filter(Listing.rooms == rooms)
    if district:
        query = query.filter(Listing.district == district)
    if date_from:
        query = query.filter(Listing.published_at >= _parse_date(date_from))
    if date_to:
        query = query.filter(Listing.published_at <= _parse_date(date_to, end_of_day=True))
    if q:
        query = query.filter(Listing.title.ilike(f"%{q}%"))

    rows = query.order_by(Listing.published_at.desc()).limit(limit).all()
    return {"count": len(rows), "listings": [r.to_dict() for r in rows]}


@router.get("/filters")
def available_filters(session: Session = Depends(db.get_db)):
    """Доступные значения для дропдаунов (районы и число комнат)."""
    districts = [
        row[0]
        for row in (
            session.query(Listing.district)
            .filter(Listing.district.isnot(None))
            .distinct()
            .order_by(Listing.district)
            .all()
        )
    ]
    rooms = [
        row[0]
        for row in (
            session.query(Listing.rooms)
            .filter(Listing.rooms.isnot(None))
            .distinct()
            .order_by(Listing.rooms)
            .all()
        )
    ]
    return {"districts": districts, "rooms": rooms}


@router.post("/run")
def run_parser():
    run_now()
    return {"status": "started"}


@router.get("/status")
def status():
    return {
        "last_result": get_last_result(),
        "next_run_at": get_next_run_at(),
        "interval_minutes": settings.interval_minutes,
    }
