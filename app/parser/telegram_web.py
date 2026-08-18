"""Парсер публичных Telegram-каналов через веб-превью t.me/s/ (без входа)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

from app.parser.extract import parse_district, parse_rooms, parse_tg_price

KIEV_TZ = ZoneInfo("Europe/Kiev")
_POST_ID_RE = re.compile(r"/(\d+)$")
_AREA_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*м[²2]")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}


def normalize_channel(channel: str) -> str:
    """Приводит ссылку/username канала к голому имени (без @ и https://t.me/)."""
    c = (channel or "").strip()
    if "/" in c:
        c = c.rstrip("/").split("/")[-1]
    return c.lstrip("@").lower()


def run_telegram_web_parse(config: dict) -> tuple[list[dict], list[str]]:
    """Читает публичные каналы и возвращает (карточки, ошибки)."""
    channels = [
        normalize_channel(c)
        for c in (config.get("channels") or "").split(",")
        if c.strip()
    ]
    if not channels:
        return [], ["telegram: список каналов пуст"]

    cards: list[dict] = []
    errors: list[str] = []
    for channel in channels:
        try:
            cards.extend(_parse_channel(channel, config.get("limit", 30)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"telegram {channel}: {exc}")
    return cards, errors


def _parse_channel(channel: str, limit: int) -> list[dict]:
    url = f"https://t.me/s/{channel}"
    resp = httpx.get(url, headers=_HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cards: list[dict] = []
    for msg in soup.select(".tgme_widget_message"):
        data_post = msg.get("data-post", "")
        m = _POST_ID_RE.search(data_post)
        if not m:
            continue
        msg_id = m.group(1)

        text_el = msg.select_one(".tgme_widget_message_text")
        if not text_el:
            continue
        text = " ".join(text_el.get_text(" ", strip=True).split())
        if not text:
            continue

        published_at = _extract_time(msg)
        cards.append(_build_card(channel, msg_id, text, published_at))
        if len(cards) >= limit:
            break
    return cards


def _extract_time(msg) -> Optional[datetime]:
    """Дата публикации из <time datetime="...">; None, если её нет."""
    time_el = msg.select_one("time[datetime]")
    if time_el and time_el.get("datetime"):
        try:
            return (
                datetime.fromisoformat(time_el["datetime"])
                .astimezone(KIEV_TZ)
                .replace(tzinfo=None)
            )
        except ValueError:
            return None
    return None


def _build_card(channel: str, msg_id: str, text: str, published_at: Optional[datetime]) -> dict:
    price_value = parse_tg_price(text)
    if price_value is not None:
        if price_value == int(price_value):
            price = f"{int(price_value):,}".replace(",", " ") + " грн."
        else:
            price = f"{price_value:,.2f}".replace(",", " ") + " грн."
    else:
        price = ""

    area = ""
    area_m = _AREA_RE.search(text)
    if area_m:
        area = area_m.group(0)

    return {
        "olx_id": f"tg-{msg_id}",
        "url": f"https://t.me/{channel}/{msg_id}",
        "title": text[:300],
        "price": price,
        "price_value": price_value,
        "rooms": parse_rooms(text),
        "area": area,
        "location": "Хмельницький",
        "district": parse_district(text),
        "published_at": published_at,
        "source": "telegram",
        "channel": channel,
    }
