"""Хранилище настроек в БД (key-value)."""
from __future__ import annotations

import base64
import hashlib
from typing import Optional

from app import db
from app.models import AppSetting

_SECRET_SETTINGS = {"telegram_api_hash", "telegram_session"}
_ENCRYPTED_PREFIX = "enc:v1:"


def _fernet():
    from cryptography.fernet import Fernet
    from app.config import settings

    if not settings.secret_key:
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode("utf-8")).digest())
    return Fernet(key)


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


def get_secret_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    value = get_setting(key)
    if value is None:
        return default
    if not value.startswith(_ENCRYPTED_PREFIX):
        # Legacy rows are read once and upgraded when a key is configured.
        if _fernet() is None:
            return default
        set_secret_setting(key, value)
        return value
    fernet = _fernet()
    if fernet is None:
        return default
    try:
        return fernet.decrypt(value[len(_ENCRYPTED_PREFIX):].encode("utf-8")).decode("utf-8")
    except Exception:  # noqa: BLE001
        return default


def set_secret_setting(key: str, value: Optional[str]) -> None:
    if key not in _SECRET_SETTINGS:
        raise ValueError(f"Unsupported secret setting: {key}")
    if value is None:
        set_setting(key, None)
        return
    fernet = _fernet()
    if fernet is None:
        raise RuntimeError("SECRET_KEY must be configured before saving Telegram secrets")
    encrypted = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    set_setting(key, _ENCRYPTED_PREFIX + encrypted)


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
        "api_hash": get_secret_setting("telegram_api_hash") or settings.telegram_api_hash,
        "session": get_secret_setting("telegram_session") or settings.telegram_session,
        "channels": get_setting("telegram_channels") or settings.telegram_channels,
        "limit": settings.telegram_limit,
    }
