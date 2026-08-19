"""Извлечение структурированных полей из текста объявления: цена, комнаты, район."""
from __future__ import annotations

import re
from typing import Optional

# --- Цена ---------------------------------------------------------------

_PRICE_MARKER_RE = re.compile(
    r"💰\s*(\d[\d\s\u00a0\u202f.,]*)\s*(грн|₴|uah|\$|usd|дол(?:л|ларов?)?|€|eur|евро)?",
    re.IGNORECASE,
)
_PRICE_WITH_CURRENCY_RE = re.compile(
    r"(?<!\d)(?:(грн|₴|uah|\$|usd|дол(?:л|ларов?)?|€|eur|евро)\s*)?"
    r"(\d[\d\s\u00a0\u202f.,]*)\s*"
    r"(грн|₴|uah|\$|usd|дол(?:л|ларов?)?|€|eur|евро|\+кп)(?!\w)",
    re.IGNORECASE,
)
_PRICE_PREFIX_RE = re.compile(
    r"(?<!\d)(грн|₴|uah|\$|usd|дол(?:л|ларов?)?|€|eur|евро)\s*"
    r"(\d[\d\s\u00a0\u202f.,]*)(?!\d)",
    re.IGNORECASE,
)


def _to_float(raw: str) -> Optional[float]:
    """Преобразует строку числа (с пробелами/запятыми/точками) в float."""
    last_sep = None
    for ch in raw:
        if ch in ".,":
            last_sep = ch

    cleaned = re.sub(r"[\s\u00a0\u202f]", "", raw)
    if last_sep == ",":
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif last_sep == ".":
        cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_price_value(price: Optional[str]) -> Optional[float]:
    """Извлекает числовое значение цены, если в строке указана валюта.

    "13 000 грн." -> 13000.0
    "35 843.63 грн." -> 35843.63
    "18 000 грн. Договірна" -> 18000.0
    "Договірна" -> None
    """
    value, _ = parse_price_info(price)
    return value


def normalize_currency(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip().lower()
    if value in {"грн", "₴", "uah", "+кп"}:
        return "UAH"
    if value in {"$", "usd", "дол", "долл", "доллар", "долларов"}:
        return "USD"
    if value in {"€", "eur", "евро"}:
        return "EUR"
    return None


def parse_price_info(price: Optional[str], default_currency: Optional[str] = None) -> tuple[Optional[float], Optional[str]]:
    """Returns a numeric amount and currency only when a currency marker is present."""
    if not price:
        return None, None
    marker = _PRICE_MARKER_RE.search(price)
    if marker:
        return _to_float(marker.group(1)), normalize_currency(marker.group(2)) or default_currency or "UAH"
    match = _PRICE_WITH_CURRENCY_RE.search(price)
    if match:
        amount = _to_float(match.group(2))
        currency = normalize_currency(match.group(1)) or normalize_currency(match.group(3))
        return amount, currency or default_currency
    prefix = _PRICE_PREFIX_RE.search(price)
    if prefix:
        return _to_float(prefix.group(2)), normalize_currency(prefix.group(1))
    return None, None


def parse_price_currency(price: Optional[str]) -> Optional[str]:
    return parse_price_info(price)[1]


def parse_tg_price(text: Optional[str]) -> Optional[float]:
    """Извлекает цену из текста Telegram-объявления (по маркерам цены)."""
    if not text:
        return None
    value, _ = parse_price_info(text, default_currency="UAH")
    return value


# --- Комнаты ------------------------------------------------------------

_ROOMS_FRAC_RE = re.compile(r"(\d+)[.,]\d+\s*[-–]?\s*[кk]\b")  # "1.5к" / "1,5к"
_ROOMS_K_RE = re.compile(r"(\d+)\s*[-–]?\s*[кk]\b")  # "1к", "2-к", "3 к"
_ROOMS_NUM_RE = re.compile(
    r"(\d+)\s*[-–:]?\s*[хx]?\s*(?:кімн|кімнат|комн|комнат)",
    re.IGNORECASE,
)  # "2-кімнатна", "2-х комнатная", "2 кімн."
_ROOMS_KEYCAP_RE = re.compile(r"([1-9])(?:\ufe0f)?\u20e3\s*[-–:]?\s*(?:кімн|кімнат|комн|комнат)", re.IGNORECASE)

# Словарные формы (подстрока -> число комнат)
_WORD_ROOMS = [
    ("однокімнатн", 1), ("однокомнатн", 1), ("однушк", 1),
    ("двокімнатн", 2), ("двохкімнатн", 2), ("двокомнатн", 2), ("двухкомнатн", 2), ("двушк", 2),
    ("трикімнатн", 3), ("трикомнатн", 3), ("трехкомнатн", 3),
    ("трьохкімнатн", 3), ("трёхкомнатн", 3),
    ("чотирикімнатн", 4), ("чотирьохкімнатн", 4), ("четирикімнатн", 4),
    ("четырехкомнатн", 4), ("чотирьохкомнатн", 4),
    ("п'ятикімнатн", 5), ("пятикомнатн", 5),
    ("студі", 1), ("студи", 1),
]


def parse_rooms(title: Optional[str]) -> Optional[int]:
    """Определяет количество комнат из заголовка объявления."""
    if not title:
        return None
    text = title.lower()

    m = _ROOMS_KEYCAP_RE.search(text)
    if m:
        return int(m.group(1))

    m = _ROOMS_FRAC_RE.search(text)  # "1.5к" -> 1
    if m:
        return int(m.group(1))

    m = _ROOMS_K_RE.search(text)  # "2к", "3 к"
    if m:
        return int(m.group(1))

    m = _ROOMS_NUM_RE.search(text)  # "2-кімнатна", "3-х комнатная"
    if m:
        return int(m.group(1))

    for word, rooms in _WORD_ROOMS:
        if word in text:
            return rooms

    return None


# --- Район --------------------------------------------------------------

# Каноническое название -> список «стемов» для поиска (укр + рус).
DISTRICT_KEYWORDS = [
    ("Проспект Миру", ["проспект мир", "проспекті мир"]),
    ("Старокостянтинівське шосе", ["старокостянтин", "староконстантин"]),
    ("Нижня Берегова", ["беркгов", "берегов"]),
    ("Південно-Західний", ["південно-захід", "юго-запад"]),
    ("Інститутська", ["інститут", "институт"]),
    ("Зарічанська", ["зарічан", "заречан"]),
    ("Лезневе", ["лезнев"]),
    ("Озерна", ["озерн"]),
    ("Виставка", ["вистав", "выстав"]),
    ("Дубово", ["дубов"]),
    ("Гречани", ["гречан"]),
    ("Раково", ["раков"]),
    ("Паркова", ["парков"]),
    ("Центр", ["центр"]),
]


# Упоминания улиц (вул./пров./ул.) — чтобы не путать улицу с районом
_STREET_RE = re.compile(
    r"(?:вул\.?|вулиця|ул\.?|улица|пров\.?|провулок|пер\.?|переулок)\s*[\w'’.-]*",
    re.IGNORECASE,
)


def parse_district(title: Optional[str], location: Optional[str] = None) -> Optional[str]:
    """Определяет район Хмельницкого по заголовку/локации (keyword-based)."""
    text = " ".join(filter(None, [title, location]))
    # Убираем упоминания улиц («вул. Зарічанська»), чтобы не путать с районом
    text = _STREET_RE.sub(" ", text)
    text = text.lower()
    for canonical, stems in DISTRICT_KEYWORDS:
        for stem in stems:
            if stem in text:
                return canonical
    return None
