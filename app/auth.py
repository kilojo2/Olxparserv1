"""Простая авторизация администратора (токен в cookie, хранится в памяти)."""
from __future__ import annotations

import secrets

from fastapi import HTTPException, Request

_valid_tokens: set[str] = set()


def check_password(password: str) -> bool:
    from app.config import settings

    return secrets.compare_digest(password or "", settings.admin_password)


def create_token() -> str:
    token = secrets.token_hex(16)
    _valid_tokens.add(token)
    return token


def is_admin(request: Request) -> bool:
    token = request.cookies.get("admin_token")
    return bool(token) and token in _valid_tokens


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Требуется авторизация")
