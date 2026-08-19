"""Парсеры HTML-площадок недвижимости: DOM.RIA, RIELTOR.UA."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

from app.parser.city_map import normalize_city
from app.parser.date_parser import parse_olx_date
from app.parser.extract import parse_district, parse_price_currency, parse_price_value, parse_rooms

KIEV_TZ = ZoneInfo("Europe/Kiev")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}
_AREA_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*м[²2]")
SITE_CITY_CONFIG = {
    "khmelnitskiy": {"domria": "khmelnytskyi", "rieltor": "hmelnitskij", "name": "Хмельницький"},
    "kiev": {"domria": "kiev", "rieltor": "kiev", "name": "Київ"},
    "lviv": {"domria": "lviv", "rieltor": "lvov", "name": "Львів"},
    "odessa": {"domria": "odessa", "rieltor": "odessa", "name": "Одеса"},
    "dnepr": {"domria": "dnepr", "rieltor": "dnepr", "name": "Дніпро"},
    "dnipro": {"domria": "dnepr", "rieltor": "dnepr", "name": "Дніпро"},
    "kharkov": {"domria": "kharkiv", "rieltor": "kharkov", "name": "Харків"},
    "kharkiv": {"domria": "kharkiv", "rieltor": "kharkov", "name": "Харків"},
    "zaporozhe": {"domria": "zaporizhzhia", "rieltor": "zaporozhe", "name": "Запоріжжя"},
    "vinnitsa": {"domria": "vinnytsia", "rieltor": "vinnitsa", "name": "Вінниця"},
    "zhitomir": {"domria": "zhytomyr", "rieltor": "zhitomir", "name": "Житомир"},
    "chernovtsy": {"domria": "chernivtsi", "rieltor": "chernovtsy", "name": "Чернівці"},
    "chernivtsi": {"domria": "chernivtsi", "rieltor": "chernovtsy", "name": "Чернівці"},
    "poltava": {"domria": "poltava", "rieltor": "poltava", "name": "Полтава"},
    "cherkassy": {"domria": "cherkasy", "rieltor": "cherkassy", "name": "Черкаси"},
    "rovno": {"domria": "rivne", "rieltor": "rovno", "name": "Рівне"},
    "ternopol": {"domria": "ternopil", "rieltor": "ternopol", "name": "Тернопіль"},
    "sumy": {"domria": "sumy", "rieltor": "sumy", "name": "Суми"},
}


def run_sites_parse(settings=None, now: Optional[datetime] = None) -> tuple[list[dict], list[str]]:
    """Парсит все HTML-площадки и возвращает (карточки, ошибки)."""
    if settings is None:
        from app.config import settings as default_settings

        settings = default_settings
    city_slug = normalize_city(settings.city)
    city = SITE_CITY_CONFIG.get(city_slug)
    if city is None:
        return [], [f"sites: city {settings.city!r} has no DOM.RIA/RIELTOR slug mapping"]
    now = now or datetime.now(tz=KIEV_TZ).replace(tzinfo=None)
    cards: list[dict] = []
    errors: list[str] = []
    for name, fn in (("domria", _parse_domria), ("rieltor", _parse_rieltor)):
        try:
            parsed = fn(city, now)
            if not parsed:
                errors.append(f"{name}: selector returned no cards for {city['name']}")
            cards.extend(parsed)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    return cards, errors


def _get_soup(url: str) -> BeautifulSoup:
    resp = httpx.get(url, headers=_HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _id_from_url(url: str) -> str:
    m = re.search(r"(?:view/|realty-)(\d+)", url) or re.search(r"(\d+)\.html", url)
    if m:
        return m.group(1)
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _parse_domria(city: dict, now: datetime) -> list[dict]:
    soup = _get_soup(f"https://dom.ria.com/uk/arenda-kvartir/{city['domria']}/")
    cards: list[dict] = []
    for item in soup.select("section.realty-item"):
        price_el = item.select_one("b.size22")
        price = " ".join(price_el.get_text(" ", strip=True).split()) if price_el else ""

        link_el = item.select_one("a[href*='/realty-']")
        href = link_el.get("href") if link_el else None
        title = (link_el.get("title") or "").strip() if link_el else ""
        if not title and link_el:
            title = " ".join(link_el.get_text(" ", strip=True).split())
        url = "https://dom.ria.com" + href if href and href.startswith("/") else (href or "")
        if not url:
            continue

        district_el = item.select_one("a[data-level='area']")
        district = " ".join(district_el.get_text(" ", strip=True).split()) if district_el else ""

        time_el = item.select_one("time[datetime]")
        published_at = None
        if time_el and time_el.get("datetime"):
            try:
                published_at = datetime.strptime(time_el["datetime"].strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                published_at = None

        chars = [
            " ".join(c.get_text(" ", strip=True).split())
            for c in item.select(".realty-char span.point-before")
        ]
        chars_text = " ".join(chars)

        area = ""
        area_m = _AREA_RE.search(chars_text)
        if area_m:
            area = area_m.group(0)

        cards.append({
            "olx_id": f"domria-{_id_from_url(url)}",
            "url": url,
            "title": title or (chars_text[:200] if chars_text else "Квартира"),
            "price": price,
            "price_value": parse_price_value(price),
            "currency": parse_price_currency(price),
            "rooms": parse_rooms(chars_text),
            "area": area,
            "location": city["name"],
            "district": district or parse_district(title),
            "published_at": published_at,
            "source": "domria",
            "channel": None,
        })
    return cards


def _parse_rieltor(city: dict, now: datetime) -> list[dict]:
    soup = _get_soup(f"https://rieltor.ua/{city['rieltor']}/flats-rent/")
    cards: list[dict] = []
    for card in soup.select(".catalog-card"):
        item_id = card.get("data-catalog-item-id", "")
        price = (card.get("data-label") or "").strip()

        link_el = card.select_one("a[href*='/view/']")
        href = link_el.get("href") if link_el else ""
        url = href if href.startswith("http") else ("https://rieltor.ua" + href if href else "")
        if not url:
            continue

        img = card.select_one("img[alt]")
        title = (img.get("alt") or "").strip() if img else ""
        if not title:
            title_el = card.select_one("[class*='title'], h3, h2")
            title = " ".join(title_el.get_text(" ", strip=True).split()) if title_el else ""

        text = " ".join(card.get_text(" ", strip=True).split())
        area = ""
        area_m = _AREA_RE.search(text)
        if area_m:
            area = area_m.group(0)

        published_at: Optional[datetime] = None
        time_el = card.select_one("time[datetime]")
        if time_el and time_el.get("datetime"):
            try:
                published_at = datetime.strptime(time_el["datetime"].strip()[:10], "%Y-%m-%d")
            except ValueError:
                published_at = None
        if published_at is None:
            text_lower = text.lower()
            if "сьогодні" in text_lower or "сегодня" in text_lower:
                published_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif "вчора" in text_lower or "вчера" in text_lower:
                published_at = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if published_at is None:
            published_at = parse_olx_date(text, now)
        item_id = item_id or _id_from_url(url)

        cards.append({
            "olx_id": f"rieltor-{item_id}",
            "url": url,
            "title": title or "Квартира",
            "price": price,
            "price_value": parse_price_value(price),
            "currency": parse_price_currency(price),
            "rooms": parse_rooms(text),
            "area": area,
            "location": city["name"],
            "district": parse_district(title),
            "published_at": published_at,
            "source": "rieltor",
            "channel": None,
        })
    return cards
