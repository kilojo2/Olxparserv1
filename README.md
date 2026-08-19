# Apartment Rent Parser

Веб-приложение для мониторинга свежих объявлений **долгосрочной аренды квартир** из OLX.ua, DOM.RIA, RIELTOR.UA и публичных Telegram-каналов. Источники используют выбранный город, объявления сохраняются в базу данных и показываются на закрытом админ-дашборде.

## Возможности

- Парсинг долгосрочной аренды квартир в выбранном городе (принимает и рус., и укр. название).
- Сохранение **только свежих** объявлений (возраст < 2 дней, настраивается).
- Автоматический запуск по расписанию (по умолчанию — **2 страницы каждые 2 часа**).
- Ручной запуск кнопкой «Запустить сейчас» на дашборде.
- Прокси: **HTTP / HTTPS / SOCKS4 / SOCKS5**, с авторизацией и ротацией списка.
- Anti-detection: рандомный User-Agent, stealth-скрипты, случайные паузы.
- Дедупликация по источнику и ID объявления, включая имя Telegram-канала.
- Явное хранение валюты и фильтрация цен без смешивания UAH/USD/EUR.
- Хранение: SQLite (локально) или PostgreSQL (на Railway).
- Видимый браузер локально, headless на сервере (автопереключение через `HEADLESS`).

## Требования

- Python 3.11+
- Playwright (Chromium)

## Локальный запуск

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

Создайте файл `.env` из примера:

```bash
# Windows
copy .env.example .env
# Linux / macOS
cp .env.example .env
```

Запуск:

```bash
uvicorn app.main:app --reload
```

Откройте http://127.0.0.1:8000 — на дашборде будет таблица свежих объявлений.

> Для локальной отладки поставьте в `.env` `HEADLESS=false`, чтобы видеть браузер.

## Конфигурация (`.env`)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `CITY` | `Хмельницький` | Город (рус. или укр. название) |
| `PAGES_PER_RUN` | `2` | Страниц за один прогон |
| `INTERVAL_MINUTES` | `120` | Интервал между прогонами, мин |
| `MAX_AGE_DAYS` | `2` | Сохранять объявления младше N дней |
| `HEADLESS` | `true` | `false` — видимый браузер |
| `DATABASE_URL` | `sqlite:///./olx.db` | Строка подключения БД |
| `PROXY_ENABLED` | `false` | Включить прокси |
| `PROXY_URL` | — | Полный URL прокси (с авторизацией) |
| `PROXY_PROTOCOL/HOST/PORT/USERNAME/PASSWORD` | — | Прокси отдельными полями |
| `PROXY_LIST` | — | Список прокси через запятую (ротация) |
| `OLX_BASE_URL` | `https://www.olx.ua` | Базовый URL OLX |
| `ADMIN_PASSWORD` | — | Обязательный пароль администратора |
| `SECRET_KEY` | — | Ключ шифрования Telegram-секретов |
| `SCHEDULER_ENABLED` | `true` | Включить периодический планировщик |
| `SCHEDULER_RUN_ON_START` | `false` | Разрешить сетевой прогон сразу после старта |

### Пример прокси

```bash
# Одиночный SOCKS5 с авторизацией
PROXY_ENABLED=true
PROXY_URL=socks5://user:password@1.2.3.4:1080

# Или HTTP прокси отдельными полями
PROXY_ENABLED=true
PROXY_PROTOCOL=http
PROXY_HOST=1.2.3.4
PROXY_PORT=8080
PROXY_USERNAME=user
PROXY_PASSWORD=pass

# Ротация нескольких прокси
PROXY_ENABLED=true
PROXY_LIST=socks5://u1:p1@h1:1080,http://u2:p2@h2:8080
```

## Как работает фильтр «2 дня»

При каждом прогоне парсер:

1. Открывает страницы поиска с сортировкой «Найновіші».
2. Извлекает у каждого объявления дату публикации (`Сьогодні о 12:04`, `Вчора о 18:00`, `17 серпня 2026 р.` и т.п.).
3. Вычисляет возраст объявления.
4. **Сохраняет**, если возраст < `MAX_AGE_DAYS`, иначе **пропускает**.
5. Пропускает дубли по ID объявления OLX.

## Деплой на Railway

1. Залейте проект в GitHub и подключите репозиторий в Railway (Deploy → New project → Deploy from GitHub).
2. Railway определит `Dockerfile` (конфиг `railway.json` уже приложен) и соберёт образ с Chromium.
3. Добавьте **PostgreSQL**: в проекте — «New» → «Database» → «PostgreSQL». Railway автоматически добавит переменную `DATABASE_URL`.
4. Убедитесь, что заданы нужные переменные окружения (`CITY`, `HEADLESS=true`, `INTERVAL_MINUTES` и т.д.).
5. Приложение поднимется, а первый сетевой прогон произойдёт по расписанию. Для multi-worker запускайте планировщик отдельным процессом с одним worker.

Порт Railway передаёт через переменную `PORT` (учтено в `Dockerfile`).

## Тесты

```bash
pytest
```

## Структура проекта

```
e:\Parser\
├── app\
│   ├── main.py            # FastAPI-приложение
│   ├── config.py          # настройки (env / .env)
│   ├── db.py              # подключение к БД
│   ├── models.py          # модель Listing
│   ├── scheduler.py       # планировщик APScheduler
│   ├── parser\
│   │   ├── browser.py     # Playwright + прокси + anti-detect
│   │   ├── olx.py         # парсинг страниц поиска OLX
│   │   ├── date_parser.py # разбор дат укр/рус
│   │   ├── city_map.py    # город -> slug
│   │   └── service.py     # оркестрация прогона
│   ├── routes\
│   │   ├── pages.py       # HTML-дашборд
│   │   └── api.py         # REST API
│   ├── templates\         # Jinja2-шаблоны
│   └── static\            # CSS/JS
├── tests\                 # юнит-тесты
├── Dockerfile             # образ для Railway
├── railway.json           # конфиг деплоя Railway
├── requirements.txt
└── .env.example
```

## Предупреждение

- Парсер работает с публичными страницами источников. Учитывайте условия использования сайтов и законодательство.
- OLX защищён Cloudflare: при частых запросах возможна блокировка. Для снижения риска используйте прокси, умеренные интервалы и не уменьшайте паузы.
