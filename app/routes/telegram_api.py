"""API управления Telegram: конфигурация и вход в аккаунт."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import auth
from app.settings_store import get_telegram_config, set_setting
from app.telegram_auth import has_pending_login, send_code, verify_code, verify_password

router = APIRouter(prefix="/api/telegram")


class ConfigBody(BaseModel):
    api_id: Optional[str] = None
    api_hash: Optional[str] = None
    channels: Optional[str] = None
    enabled: Optional[bool] = None


class PhoneBody(BaseModel):
    phone: str
    force_sms: bool = False


class CodeBody(BaseModel):
    code: str


class PasswordBody(BaseModel):
    password: str


@router.get("/config")
def get_config(request: Request):
    auth.require_admin(request)
    cfg = get_telegram_config()
    return {
        "enabled": cfg["enabled"],
        "api_id": cfg["api_id"],
        "api_hash": cfg["api_hash"],
        "session_set": bool(cfg["session"]),
        "channels": cfg["channels"],
        "pending_login": has_pending_login(),
    }


@router.post("/config")
def save_config(request: Request, body: ConfigBody):
    auth.require_admin(request)
    if body.api_id is not None:
        set_setting("telegram_api_id", body.api_id if body.api_id else None)
    if body.api_hash is not None:
        set_setting("telegram_api_hash", body.api_hash if body.api_hash else None)
    if body.channels is not None:
        set_setting("telegram_channels", body.channels)
    if body.enabled is not None:
        set_setting("telegram_enabled", "true" if body.enabled else "false")
    return {"ok": True}


@router.post("/send-code")
async def send_code_endpoint(request: Request, body: PhoneBody):
    auth.require_admin(request)
    phone = body.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Укажите номер телефона")
    try:
        info = await send_code(phone, force_sms=body.force_sms)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Ошибка отправки кода: {exc}")
    return {"ok": True, **info}


@router.post("/verify-code")
async def verify_code_endpoint(request: Request, body: CodeBody):
    auth.require_admin(request)
    code = body.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Укажите код")
    try:
        result = await verify_code(code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Ошибка проверки кода: {exc}")
    if result["twofa"]:
        return {"ok": True, "twofa": True}
    set_setting("telegram_session", result["session"])
    return {"ok": True, "twofa": False, "connected": True}


@router.post("/verify-password")
async def verify_password_endpoint(request: Request, body: PasswordBody):
    auth.require_admin(request)
    try:
        session_str = await verify_password(body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Ошибка проверки пароля: {exc}")
    set_setting("telegram_session", session_str)
    return {"ok": True, "connected": True}
