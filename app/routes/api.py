"""REST API: список объявлений с фильтрами, ручной запуск, статус."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import auth, db
from app.config import settings
from app.models import Listing
from app.scheduler import get_last_result, get_next_run_at, run_now

router = APIRouter(prefix="/api")


@router.get("/listings")
def list_listings(
    request: Request,
    limit: int = Query(500, ge=1, le=1000),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    rooms: Optional[int] = Query(None, ge=0, le=20),
    district: Optional[str] = Query(None, max_length=128),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    q: Optional[str] = Query(None, max_length=200),
    currency: Optional[str] = Query(None, pattern=r"^[A-Za-z₴$]{1,8}$"),
    session: Session = Depends(db.get_db),
):
    auth.require_admin(request)
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price must not exceed max_price")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    query = session.query(Listing)

    if min_price is not None:
        query = query.filter(Listing.price_value >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price_value <= max_price)
    if rooms is not None:
        query = query.filter(Listing.rooms == rooms)
    if district:
        query = query.filter(Listing.district == district)
    if currency:
        query = query.filter(Listing.currency == currency.upper())
    elif min_price is not None or max_price is not None:
        query = query.filter(Listing.currency == "UAH")
    if date_from:
        query = query.filter(Listing.published_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(Listing.published_at <= datetime.combine(date_to, time.max))
    if q:
        query = query.filter(Listing.title.ilike(f"%{q}%"))

    rows = query.order_by(Listing.published_at.desc()).limit(limit).all()
    return {"count": len(rows), "listings": [r.to_dict() for r in rows]}


@router.get("/filters")
def available_filters(request: Request, session: Session = Depends(db.get_db)):
    """Доступные значения для дропдаунов (районы и число комнат)."""
    auth.require_admin(request)
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
    currencies = [
        row[0]
        for row in session.query(Listing.currency).filter(Listing.currency.isnot(None)).distinct().order_by(Listing.currency).all()
    ]
    return {"districts": districts, "rooms": rooms, "currencies": currencies}


@router.post("/run")
def run_parser(request: Request):
    auth.require_admin(request)
    run_now()
    return {"status": "started"}


@router.get("/status")
def status(request: Request):
    auth.require_admin(request)
    return {
        "last_result": get_last_result(),
        "next_run_at": get_next_run_at(),
        "interval_minutes": settings.interval_minutes,
    }


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=256)


@router.post("/admin/login")
def admin_login(request: Request, body: LoginBody, response: Response):
    if not auth.login_allowed(request):
        raise HTTPException(status_code=429, detail="Слишком много попыток входа")
    if not auth.check_password(body.password):
        auth.record_failed_login(request)
        raise HTTPException(status_code=401, detail="Неверный пароль")
    auth.clear_failed_logins(request)
    token, ttl = auth.create_token()
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    secure = request.url.scheme == "https" or forwarded_proto == "https"
    response.set_cookie(
        "admin_token", token, httponly=True, samesite="lax", secure=secure, max_age=ttl
    )
    return {"ok": True}


@router.post("/admin/logout")
def admin_logout(response: Response):
    response.delete_cookie("admin_token")
    return {"ok": True}
