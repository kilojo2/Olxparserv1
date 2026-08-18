"""Хранилище настроек в БД (key-value)."""
from __future__ import annotations

from typing import Optional

from app import db
from app.models import AppSetting


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    session = db.SessionLocal()
    try:
        row = session.query(AppSetting).filter(AppSetting.key == key).first()
        return row.value if row else default
    finally:
        session.close()


def set_setting(key: str, value: Optional[str]) -> None:
    session = db.SessionLocal()
    try:
        row = session.query(AppSetting).filter(AppSetting.key == key).first()
        if row is not None:
            row.value = value
        else:
            session.add(AppSetting(key=key, value=value))
        session.commit()
    finally:
        session.close()


def _as_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def _as_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def get_telegram_config() -> dict:
    """Полные настройки Telegram (из БД, с фолбэком на env)."""
    from app.config import settings

    return {
        "enabled": _as_bool(get_setting("telegram_enabled")),
        "api_id": _as_int(get_setting("telegram_api_id")) or settings.telegram_api_id,
        "api_hash": get_setting("telegram_api_hash") or settings.telegram_api_hash,
        "session": get_setting("telegram_session") or settings.telegram_session,
        "channels": get_setting("telegram_channels") or settings.telegram_channels,
        "limit": settings.telegram_limit,
    }
