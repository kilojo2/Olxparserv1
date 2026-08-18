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


settings = Settings()
