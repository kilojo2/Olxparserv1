FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Установка Chromium и системных зависимостей для Playwright
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000

# $PORT задаётся Railway автоматически; локально — 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
