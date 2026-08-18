"""Логика парсинга страницы поиска OLX."""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlencode

from playwright.sync_api import Page

from app.parser.date_parser import parse_olx_date
from app.parser.extract import parse_district, parse_price_value, parse_rooms

# Долгосрочная аренда квартир
CATEGORY_SLUG = "nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir"
SORT_ORDER = "created_at:desc"

# Признаки блокировки (Cloudflare / капча). Специфичные фразы, чтобы не
# ловить ложные срабатывания (например, «доступними» в обычном заголовке).
_ACCESS_DENIED_TITLE_MARKERS = [
    "just a moment",
    "attention required",
    "verify you are human",
    "доступ заборонено",
    "доступ запрещён",
    "доступ запрещен",
    "доступ ограничен",
    "ще мить",
    "щё мить",
]

_AD_ID_RE = re.compile(r"ID([A-Za-z0-9]+)\.html")
_AREA_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*м²")


def _clean(text: str) -> str:
    """Схлопывает лишние пробелы и переносы строк."""
    return " ".join((text or "").split())



def build_search_url(base_url: str, city_slug: str, page: int) -> str:
    """Собирает URL поиска с сортировкой по новизне."""
    base = base_url.rstrip("/")
    path = f"/uk/{CATEGORY_SLUG}/{city_slug}/"
    params = {"search[order]": SORT_ORDER, "page": page}
    return f"{base}{path}?{urlencode(params)}"


def extract_ad_id(url: Optional[str]) -> Optional[str]:
    """Извлекает идентификатор объявления OLX из ссылки."""
    if not url:
        return None
    m = _AD_ID_RE.search(url)
    return m.group(1) if m else None


def is_access_denied(page: Page) -> bool:
    """Проверяет, не заблокирован ли доступ (Cloudflare/капча)."""
    try:
        title = (page.title() or "").lower()
    except Exception:
        return False
    return any(marker in title for marker in _ACCESS_DENIED_TITLE_MARKERS)


def split_location_date(text: str) -> tuple[str, str]:
    """Разделяет строку вида 'Хмельницький - Сьогодні о 12:04' на локацию и дату."""
    if " - " in text:
        location, date = text.split(" - ", 1)
        return location.strip(), date.strip()
    return text.strip(), ""


def extract_card(card, now) -> Optional[dict]:
    """Извлекает данные одной карточки объявления."""
    try:
        # Ссылка заголовка объявления — самый надёжный селектор.
        link_el = card.query_selector("a[data-testid='card-title-link']")
        if link_el is None:
            # Fallback: первая ссылка на объявление с непустым текстом
            # (фото-ссылка на карточке пустая, поэтому ищем по тексту).
            for link in card.query_selector_all("a[href*='/d/']"):
                if (link.inner_text() or "").strip():
                    link_el = link
                    break
        if link_el is None:
            link_el = card.query_selector("a[href*='/d/']")
        if link_el is None:
            return None

        href = link_el.get_attribute("href")
        if not href or "/d/" not in href:
            return None

        url = href if href.startswith("http") else "https://www.olx.ua" + href
        olx_id = extract_ad_id(url)
        if not olx_id:
            return None

        title = _clean(link_el.inner_text() or "")
        if not title:
            for tag in ("h4", "h6", "h3", "h2"):
                heading = card.query_selector(tag)
                if heading:
                    title = _clean(heading.inner_text() or "")
                    if title:
                        break

        price = ""
        price_el = card.query_selector("[data-testid='ad-price']")
        if price_el:
            price = _clean(price_el.inner_text() or "")

        location = ""
        date_text = ""
        loc_el = card.query_selector("[data-testid='location-date']")
        if loc_el:
            location, date_text = split_location_date(_clean(loc_el.inner_text() or ""))

        area = ""
        card_text = card.inner_text()
        area_m = _AREA_RE.search(card_text)
        if area_m:
            area = area_m.group(0)

        published_at = parse_olx_date(date_text, now)

        price_value = parse_price_value(price)
        rooms = parse_rooms(title)
        district = parse_district(title, location)

        return {
            "olx_id": olx_id,
            "url": url,
            "title": title,
            "price": price,
            "price_value": price_value,
            "rooms": rooms,
            "area": area,
            "location": location,
            "district": district,
            "published_at": published_at,
        }
    except Exception:
        return None


def parse_listing_page(page: Page, now) -> list[dict]:
    """Парсит все карточки текущей страницы поиска."""
    try:
        page.wait_for_selector("[data-cy='l-card']", timeout=20000)
    except Exception:
        pass  # возможно, страница пустая или заблокирована

    results = []
    for card in page.query_selector_all("[data-cy='l-card']"):
        data = extract_card(card, now)
        if data:
            results.append(data)
    return results
