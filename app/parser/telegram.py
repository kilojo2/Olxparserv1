"""Парсер Telegram-каналов через Telethon (MTProto)."""
from __future__ import annotations

import asyncio
from typing import Optional
from zoneinfo import ZoneInfo

from app.parser.extract import parse_district, parse_price_value, parse_rooms

KIEV_TZ = ZoneInfo("Europe/Kiev")


def _clean(text: str) -> str:
    return " ".join((text or "").split())


def normalize_channel(channel: str) -> str:
    """Приводит ссылку/username канала к голому имени (без @ и https://t.me/)."""
    c = channel.strip()
    if "/" in c:
        c = c.rstrip("/").split("/")[-1]
    return c.lstrip("@").lower()


def run_telegram_parse(config: dict) -> tuple[list[dict], list[str]]:
    """Синхронная обёртка: читает каналы и возвращает (карточки, ошибки)."""
    return asyncio.run(_fetch_channel_messages(config))


async def _fetch_channel_messages(config: dict) -> tuple[list[dict], list[str]]:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    channels = [
        normalize_channel(c)
        for c in (config.get("channels") or "").split(",")
        if c.strip()
    ]
    if not channels:
        return [], ["telegram: список каналов пуст"]

    client = TelegramClient(
        StringSession(config.get("session")),
        config.get("api_id"),
        config.get("api_hash"),
    )

    cards: list[dict] = []
    errors: list[str] = []

    async with client:
        for channel in channels:
            try:
                entity = await client.get_entity(channel)
                messages = await client.get_messages(
                    entity, limit=config.get("limit", 30)
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"telegram {channel}: {exc}")
                continue
            for msg in messages:
                card = _message_to_card(msg, channel)
                if card:
                    cards.append(card)

    return cards, errors


def _message_to_card(msg, channel: str) -> Optional[dict]:
    text = _clean(msg.message)
    if not text:
        return None

    published_at = (
        msg.date.astimezone(KIEV_TZ).replace(tzinfo=None) if msg.date else None
    )

    price_value = parse_price_value(text)
    if price_value is not None:
        if price_value == int(price_value):
            price = f"{int(price_value):,}".replace(",", " ") + " грн."
        else:
            price = f"{price_value:,.2f}".replace(",", " ") + " грн."
    else:
        price = ""

    return {
        "olx_id": f"tg-{msg.id}",
        "url": f"https://t.me/{channel}/{msg.id}",
        "title": text[:300],
        "price": price,
        "price_value": price_value,
        "rooms": parse_rooms(text),
        "area": "",
        "location": "Хмельницький",
        "district": parse_district(text),
        "published_at": published_at,
        "source": "telegram",
        "channel": channel,
    }
