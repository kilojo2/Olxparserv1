"""Карта соответствий: название города (рус/укр) -> slug на OLX.ua."""
from __future__ import annotations

# Ключи — нижний регистр без апострофов; значения — slug OLX.
CITY_SLUGS = {
    "хмельницкий": "khmelnitskiy",
    "хмельницький": "khmelnitskiy",
    "киев": "kiev",
    "київ": "kiev",
    "львов": "lviv",
    "львів": "lviv",
    "одесса": "odessa",
    "одеса": "odessa",
    "днепр": "dnepr",
    "дніпро": "dnipro",
    "харьков": "kharkov",
    "харків": "kharkiv",
    "запорожье": "zaporozhe",
    "запоріжжя": "zaporozhe",
    "винница": "vinnitsa",
    "вінниця": "vinnitsa",
    "житомир": "zhitomir",
    "черновцы": "chernovtsy",
    "чернівці": "chernivtsi",
    "полтава": "poltava",
    "черкассы": "cherkassy",
    "черкаси": "cherkassy",
    "ровно": "rovno",
    "рівне": "rovno",
    "тернополь": "ternopol",
    "тернопіль": "ternopol",
    "сумы": "sumy",
    "суми": "sumy",
}


def normalize_city(name: str) -> str:
    """Приводит название города к slug OLX, принимая русский и украинский варианты."""
    if not name:
        raise ValueError("Название города не задано")
    key = name.strip().lower().replace("ё", "е").replace("'", "").replace("’", "")
    slug = CITY_SLUGS.get(key)
    if slug:
        return slug
    raise ValueError(
        f"Неизвестный город: {name!r}. Добавьте его в CITY_SLUGS (app/parser/city_map.py)."
    )
