"""Извлечение структурированных полей из текста объявления: цена, комнаты, район."""
from __future__ import annotations

import re
from typing import Optional

# --- Цена ---------------------------------------------------------------

_PRICE_NUM_RE = re.compile(r"\d[\d\s\u00a0\u202f.,]*")


def parse_price_value(price: Optional[str]) -> Optional[float]:
    """Извлекает числовое значение цены (в гривнах).

    "13 000 грн." -> 13000.0
    "35 843.63 грн." -> 35843.63
    "18 000 грн. Договірна" -> 18000.0
    "Договірна" -> None
    """
    if not price:
        return None
    m = _PRICE_NUM_RE.search(price)
    if not m:
        return None
    raw = m.group(0)

    # Определяем десятичный разделитель — последний из . , в числе.
    last_sep = None
    for ch in raw:
        if ch in ".,":
            last_sep = ch

    cleaned = re.sub(r"[\s\u00a0\u202f]", "", raw)
    if last_sep is None:
        pass  # целое число
    elif last_sep == ",":
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:  # "."
        cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


# --- Комнаты ------------------------------------------------------------

_ROOMS_FRAC_RE = re.compile(r"(\d+)[.,]\d+\s*[-–]?\s*[кk]\b")  # "1.5к" / "1,5к"
_ROOMS_K_RE = re.compile(r"(\d+)\s*[-–]?\s*[кk]\b")  # "1к", "2-к", "3 к"
_ROOMS_NUM_RE = re.compile(
    r"(\d+)\s*[-–]?\s*[хx]?\s*(?:кімнат|комнат)"
)  # "2-кімнатна", "2-х комнатная"

# Словарные формы (подстрока -> число комнат)
_WORD_ROOMS = [
    ("однокімнатн", 1), ("однокомнатн", 1), ("однушк", 1),
    ("двокімнатн", 2), ("двокомнатн", 2), ("двухкомнатн", 2), ("двушк", 2),
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
    ("Озерна", ["озерн"]),
    ("Виставка", ["вистав", "выстав"]),
    ("Дубово", ["дубов"]),
    ("Гречани", ["гречан"]),
    ("Раково", ["раков"]),
    ("Паркова", ["парков"]),
    ("Центр", ["центр"]),
]


def parse_district(title: Optional[str], location: Optional[str] = None) -> Optional[str]:
    """Определяет район Хмельницкого по заголовку/локации (keyword-based)."""
    text = " ".join(filter(None, [title, location])).lower()
    for canonical, stems in DISTRICT_KEYWORDS:
        for stem in stems:
            if stem in text:
                return canonical
    return None
