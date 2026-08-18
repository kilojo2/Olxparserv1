"""Запуск браузера Playwright с anti-detection и поддержкой прокси."""
from __future__ import annotations

import random
from typing import Optional
from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, sync_playwright

from app.config import Settings

# Набор правдоподобных User-Agent для рандомизации.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Скрываем признаки автоматизации.
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['uk-UA','uk','ru-RU','ru','en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || {};
window.chrome.runtime = window.chrome.runtime || {};
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
    window.navigator.permissions.query = (params) => (
        params && params.name === 'notifications'
            ? Promise.resolve({state: Notification.permission})
            : originalQuery(params)
    );
}
"""


def _proxy_from_url(url: str) -> dict:
    parsed = urlparse(url)
    if not parsed.hostname or not parsed.port:
        raise ValueError(f"Некорректный URL прокси: {url!r}")
    proxy = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        proxy["username"] = parsed.username
        proxy["password"] = parsed.password or ""
    return proxy


def build_proxy(settings: Settings) -> Optional[dict]:
    """Собирает словарь прокси для Playwright (все типы, с авторизацией)."""
    if settings.proxy_url:
        return _proxy_from_url(settings.proxy_url)
    if settings.proxy_host and settings.proxy_port:
        protocol = settings.proxy_protocol or "http"
        proxy = {"server": f"{protocol}://{settings.proxy_host}:{settings.proxy_port}"}
        if settings.proxy_username:
            proxy["username"] = settings.proxy_username
            proxy["password"] = settings.proxy_password or ""
        return proxy
    return None


def get_proxy_list(settings: Settings) -> list[Optional[dict]]:
    """Возвращает список прокси для ротации; пустой список — прокси нет."""
    if not settings.proxy_enabled:
        return [None]
    if settings.proxy_list:
        proxies = []
        for item in settings.proxy_list.split(","):
            item = item.strip()
            if item:
                proxies.append(_proxy_from_url(item))
        return proxies or [None]
    single = build_proxy(settings)
    return [single] if single else [None]


class BrowserSession:
    """Контекстный менеджер запуска Chromium с прокси и stealth-настройками."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._pw = None
        self._browser = None

    def __enter__(self) -> "BrowserSession":
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=self.settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        return self

    def new_context(self, proxy: Optional[dict] = None) -> BrowserContext:
        context = self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            proxy=proxy,
            viewport={"width": 1366, "height": 768},
            locale="uk-UA",
            timezone_id="Europe/Kiev",
        )
        context.add_init_script(STEALTH_JS)
        return context

    def __exit__(self, *exc) -> None:
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
