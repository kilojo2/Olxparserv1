"""Разбор дат публикации OLX (укр/рус) и вычисление возраста объявления."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

KIEV_TZ = ZoneInfo("Europe/Kiev")


def kiev_now() -> datetime:
    """Текущее время в часовом поясе Киева (naive datetime)."""
    return datetime.now(KIEV_TZ).replace(tzinfo=None)


_UK_MONTHS = {
    "січня": 1, "лютого": 2, "березня": 3, "квітня": 4,
    "травня": 5, "червня": 6, "липня": 7, "серпня": 8,
    "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
}

_RU_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

_MONTHS = {**_UK_MONTHS, **_RU_MONTHS}

_TODAY_RE = re.compile(r"(сьогодні|сегодня)\D*?(\d{1,2}):(\d{2})")
_YESTERDAY_RE = re.compile(r"(вчора|вчера)\D*?(\d{1,2}):(\d{2})")
_DAYS_AGO_RE = re.compile(r"(\d{1,2})\s*(днів|дні|дня|день|дней)\s*(тому|назад)")
_ABS_DATE_RE = re.compile(r"(\d{1,2})\s+([а-яіїєґa-z]+)\s+(\d{4})")


def parse_olx_date(text: Optional[str], now: Optional[datetime] = None) -> Optional[datetime]:
    """Преобразует строку даты OLX в абсолютный datetime.

    Поддерживаемые форматы:
      * "Сьогодні о 12:04" / "Сегодня в 12:04"
      * "Вчора о 18:00" / "Вчера в 18:00"
      * "2 дні тому" / "2 дня назад"
      * "17 серпня 2026 р." / "17 августа 2026 г."
    """
    if not text:
        return None
    now = now or kiev_now()
    s = text.strip().lower()

    m = _TODAY_RE.search(s)
    if m:
        hour, minute = int(m.group(2)), int(m.group(3))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    m = _YESTERDAY_RE.search(s)
    if m:
        hour, minute = int(m.group(2)), int(m.group(3))
        return (now - timedelta(days=1)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

    m = _DAYS_AGO_RE.search(s)
    if m:
        return (now - timedelta(days=int(m.group(1)))).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    m = _ABS_DATE_RE.search(s)
    if m:
        day = int(m.group(1))
        month = _MONTHS.get(m.group(2))
        year = int(m.group(3))
        if month:
            return datetime(year, month, day)

    return None


def age_days(published: Optional[datetime], now: Optional[datetime] = None) -> Optional[float]:
    """Возраст объявления в днях (дробное число). None, если дата неизвестна."""
    if published is None:
        return None
    now = now or kiev_now()
    return (now - published).total_seconds() / 86400.0
