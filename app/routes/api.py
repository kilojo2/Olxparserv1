"""REST API: список объявлений, ручной запуск, статус."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import db
from app.models import Listing
from app.scheduler import get_last_result, run_now

router = APIRouter(prefix="/api")


@router.get("/listings")
def list_listings(limit: int = 500, session: Session = Depends(db.get_db)):
    rows = (
        session.query(Listing)
        .order_by(Listing.published_at.desc())
        .limit(limit)
        .all()
    )
    return {"count": len(rows), "listings": [r.to_dict() for r in rows]}


@router.post("/run")
def run_parser():
    run_now()
    return {"status": "started"}


@router.get("/status")
def status():
    return {"last_result": get_last_result()}
