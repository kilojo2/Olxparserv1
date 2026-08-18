"""Оркестрация одного прогона парсера: браузер -> страницы -> фильтр -> БД."""
from __future__ import annotations

import random
import time
from typing import Optional

from app import db
from app.config import Settings
from app.models import Listing
from app.parser.browser import BrowserSession, get_proxy_list
from app.parser.city_map import normalize_city
from app.parser.date_parser import age_days, kiev_now
from app.parser.olx import build_search_url, is_access_denied, parse_listing_page


def run_parse_once(settings: Optional[Settings] = None) -> dict:
    """Выполняет один полный прогон парсинга и возвращает статистику."""
    if settings is None:
        from app.config import settings as default_settings

        settings = default_settings

    now = kiev_now()
    city_slug = normalize_city(settings.city)
    proxies = get_proxy_list(settings)
    seen_ids: set = set()  # дедупликация внутри текущего прогона

    stats = {
        "status": "ok",
        "pages": 0,
        "cards": 0,
        "saved": 0,
        "skipped_old": 0,
        "skipped_duplicate": 0,
        "skipped_unknown": 0,
        "errors": [],
        "finished_at": now.isoformat(sep=" "),
    }

    with BrowserSession(settings) as browser:
        proxy = random.choice(proxies)
        context = browser.new_context(proxy=proxy)
        page = context.new_page()
        try:
            for page_num in range(1, settings.pages_per_run + 1):
                url = build_search_url(settings.olx_base_url, city_slug, page_num)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                except Exception as exc:
                    stats["errors"].append(f"page {page_num}: {exc}")
                    continue

                if is_access_denied(page):
                    stats["errors"].append(
                        f"page {page_num}: доступ заблокирован (Cloudflare/капча)"
                    )
                    continue

                cards = parse_listing_page(page, now)
                stats["pages"] += 1
                stats["cards"] += len(cards)
                _store(cards, now, settings, stats, seen_ids)

                # Пауза между страницами, чтобы не триггерить анти-бот.
                time.sleep(random.uniform(1.5, 4.0))
        finally:
            context.close()

    return stats


def _store(cards: list[dict], now, settings: Settings, stats: dict, seen_ids: set) -> None:
    """Сохраняет свежие объявления в БД с дедупликацией по olx_id."""
    session = db.SessionLocal()
    try:
        for card in cards:
            olx_id = card.get("olx_id")
            if not olx_id:
                stats["skipped_unknown"] += 1
                continue

            # Промо-объявления OLX дублируются на странице — отсекаем повторы
            # внутри текущего прогона.
            if olx_id in seen_ids:
                stats["skipped_duplicate"] += 1
                continue
            seen_ids.add(olx_id)

            age = age_days(card.get("published_at"), now)
            if age is None:
                stats["skipped_unknown"] += 1
                continue
            if age >= settings.max_age_days:
                stats["skipped_old"] += 1
                continue

            exists = session.query(Listing).filter(Listing.olx_id == olx_id).first()
            if exists:
                exists.last_seen_at = now
                stats["skipped_duplicate"] += 1
                continue

            session.add(
                Listing(
                    olx_id=olx_id,
                    url=card["url"],
                    title=card["title"],
                    price=card["price"],
                    price_value=card.get("price_value"),
                    rooms=card.get("rooms"),
                    district=card.get("district"),
                    area=card["area"],
                    location=card["location"],
                    published_at=card["published_at"],
                    first_seen_at=now,
                    last_seen_at=now,
                )
            )
            stats["saved"] += 1

        session.commit()
    except Exception as exc:
        session.rollback()
        stats["errors"].append(str(exc))
    finally:
        session.close()
