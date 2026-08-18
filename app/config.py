"""Настройки приложения, читаются из переменных окружения и файла .env."""
from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Приложение ---
    app_name: str = "OLX Rent Parser"

    # --- Парсер ---
    city: str = "Хмельницький"
    pages_per_run: int = 2
    interval_minutes: int = 120
    max_age_days: int = 2
    headless: bool = True

    # --- База данных ---
    database_url: str = "sqlite:///./olx.db"

    # --- Прокси ---
    proxy_enabled: bool = False
    proxy_url: Optional[str] = None
    proxy_protocol: Optional[str] = None
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_list: str = ""

    # --- OLX ---
    olx_base_url: str = "https://www.olx.ua"

    # --- Админ ---
    admin_password: str = "changeme"

    # --- Telegram ---
    telegram_enabled: bool = False
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_session: Optional[str] = None
    telegram_channels: str = (
        "orenda_nerukhomist_kvartiry,arenda_khmelnitskiy_kvartiry,an_monolith"
    )
    telegram_limit: int = 30


settings = Settings()
