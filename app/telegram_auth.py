"""Процесс входа в Telegram через веб-интерфейс (in-memory состояние)."""
from __future__ import annotations

from typing import Optional

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

from app.settings_store import get_telegram_config

_client: Optional[TelegramClient] = None
_phone: Optional[str] = None


async def send_code(phone: str) -> None:
    global _client, _phone
    cfg = get_telegram_config()
    if not cfg["api_id"] or not cfg["api_hash"]:
        raise ValueError("Сначала задайте API ID и API Hash")
    _client = TelegramClient(StringSession(), cfg["api_id"], cfg["api_hash"])
    await _client.connect()
    await _client.send_code_request(phone)
    _phone = phone


async def verify_code(code: str) -> dict:
    global _client, _phone
    if _client is None or _phone is None:
        raise ValueError("Сначала отправьте код")
    try:
        await _client.sign_in(_phone, code)
    except SessionPasswordNeededError:
        return {"twofa": True}
    session_str = _client.session.save()
    await _client.disconnect()
    _client = None
    _phone = None
    return {"twofa": False, "session": session_str}


async def verify_password(password: str) -> str:
    global _client, _phone
    if _client is None:
        raise ValueError("Нет активного процесса входа")
    await _client.sign_in(password=password)
    session_str = _client.session.save()
    await _client.disconnect()
    _client = None
    _phone = None
    return session_str


def has_pending_login() -> bool:
    return _client is not None
