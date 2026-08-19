"""Cookie-based admin authentication with expiring tokens and login throttling."""
from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

_valid_tokens: dict[str, float] = {}
_failed_logins: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _purge_expired(now: float) -> None:
    for token, expires_at in list(_valid_tokens.items()):
        if expires_at <= now:
            _valid_tokens.pop(token, None)


def login_allowed(request: Request) -> bool:
    from app.config import settings

    now = time.time()
    window = max(1, settings.admin_login_rate_window_seconds)
    with _lock:
        attempts = [stamp for stamp in _failed_logins[_client_key(request)] if stamp > now - window]
        _failed_logins[_client_key(request)] = attempts
        return len(attempts) < max(1, settings.admin_login_rate_limit)


def record_failed_login(request: Request) -> None:
    with _lock:
        _failed_logins[_client_key(request)].append(time.time())


def clear_failed_logins(request: Request) -> None:
    with _lock:
        _failed_logins.pop(_client_key(request), None)


def check_password(password: str) -> bool:
    from app.config import settings

    configured = settings.admin_password
    if not configured or configured == "changeme":
        return False
    return secrets.compare_digest(password or "", configured)


def create_token() -> tuple[str, int]:
    from app.config import settings

    token = secrets.token_hex(16)
    ttl = max(60, settings.admin_token_ttl_seconds)
    with _lock:
        _purge_expired(time.time())
        _valid_tokens[token] = time.time() + ttl
    return token, ttl


def is_admin(request: Request) -> bool:
    token = request.cookies.get("admin_token")
    if not token:
        return False
    with _lock:
        _purge_expired(time.time())
        return token in _valid_tokens


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Требуется авторизация")
