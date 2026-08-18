"""Одноразовая настройка: вход в Telegram и получение строки сессии.

Запуск (локально):

    Windows:
      set TELEGRAM_API_ID=34682111
      set TELEGRAM_API_HASH=8aa1c674e979d3be51f9e937fc7c5590
      python setup_telegram.py

    Linux/macOS:
      export TELEGRAM_API_ID=34682111
      export TELEGRAM_API_HASH=8aa1c674e979d3be51f9e937fc7c5590
      python setup_telegram.py

Скрипт попросит номер телефона и код из Telegram (и пароль 2FA, если включён),
затем выведет строку сессии — сохраните её в переменную TELEGRAM_SESSION.
"""
import asyncio
import os

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    api_id = int(os.environ.get("TELEGRAM_API_ID", "0"))
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")

    if not api_id or not api_hash:
        print("Задайте переменные TELEGRAM_API_ID и TELEGRAM_API_HASH")
        return

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start()
    print()
    print("=== TELEGRAM_SESSION (скопируйте строку ниже) ===")
    print(client.session.save())
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
