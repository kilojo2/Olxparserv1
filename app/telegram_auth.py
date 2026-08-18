"""Процесс входа в Telegram через веб-интерфейс (in-memory состояние)."""
from __future__ import annotations

from typing import Optional

from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.sessions import StringSession

from app.settings_store import get_telegram_config

_client: Optional[TelegramClient] = None
_phone: Optional[str] = None


def _code_method_name(sent) -> str:
    """Определяет, каким способом Telegram отправил код."""
    type_name = type(getattr(sent, "type", None)).__name__ if getattr(sent, "type", None) else ""
    mapping = {
        "SentCodeTypeApp": "в приложение Telegram (чат «Telegram»)",
        "SentCodeTypeSms": "по SMS",
        "SentCodeTypeCall": "телефонным звонком (последние 5 цифр номера)",
        "SentCodeTypeFlashCall": "флэш-звонком",
        "SentCodeTypeEmailCode": "на e-mail",
    }
    return mapping.get(type_name, type_name or "стандартным способом")


async def send_code(phone: str, force_sms: bool = False) -> dict:
    global _client, _phone
    cfg = get_telegram_config()
    if not cfg["api_id"] or not cfg["api_hash"]:
        raise ValueError("Сначала задайте API ID и API Hash")

    phone = (phone or "").strip()
    if not phone.startswith("+"):
        phone = "+" + phone.lstrip("0")
    if len(phone) < 8:
        raise ValueError("Некорректный номер телефона")

    # Закрываем предыдущую незавершённую сессию, если есть
    if _client is not None:
        try:
            await _client.disconnect()
        except Exception:  # noqa: BLE001
            pass
        _client = None

    client = TelegramClient(StringSession(), cfg["api_id"], cfg["api_hash"])
    try:
        await client.connect()
        sent = await client.send_code_request(phone, force_sms=force_sms)
    except FloodWaitError as exc:
        await client.disconnect()
        raise ValueError(
            f"Слишком много запросов. Подождите {exc.seconds} сек и повторите."
        )
    except Exception:
        await client.disconnect()
        raise

    _client = client
    _phone = phone
    return {
        "method": _code_method_name(sent),
        "timeout": getattr(sent, "timeout", None),
    }


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
