"""Планировщик периодического запуска парсера (APScheduler)."""
from __future__ import annotations

import threading
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.parser.service import run_parse_once

_scheduler: Optional[BackgroundScheduler] = None
_run_lock = threading.Lock()
last_result: Optional[dict] = None


def _job() -> None:
    global last_result
    if not _run_lock.acquire(blocking=False):
        # Предыдущий прогон ещё выполняется — пропускаем.
        return
    try:
        try:
            last_result = run_parse_once(settings)
        except Exception as exc:  # noqa: BLE001
            last_result = {"status": "error", "errors": [str(exc)]}
    finally:
        _run_lock.release()


def start_scheduler() -> None:
    """Запускает планировщик и первый прогон в фоне."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone="Europe/Kiev")
    _scheduler.add_job(
        _job,
        IntervalTrigger(minutes=settings.interval_minutes),
        id="olx_parse",
        replace_existing=True,
    )
    _scheduler.start()

    # Первый прогон — в отдельном потоке, чтобы не блокировать старт приложения.
    threading.Thread(target=_job, daemon=True).start()


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def run_now() -> None:
    """Запускает прогон вручную (из API), не дожидаясь расписания."""
    threading.Thread(target=_job, daemon=True).start()


def get_last_result() -> Optional[dict]:
    return last_result


def get_next_run_at() -> Optional[str]:
    """Время следующего автозапуска (ISO) или None, если планировщик не запущен."""
    global _scheduler
    if _scheduler is None:
        return None
    job = _scheduler.get_job("olx_parse")
    if job is None or job.next_run_time is None:
        return None
    return job.next_run_time.isoformat()
