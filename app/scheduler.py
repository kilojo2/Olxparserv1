"""Планировщик периодического запуска парсера (APScheduler)."""
from __future__ import annotations

import threading
import os
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

from app import db
from app.config import settings
from app.parser.service import run_parse_once

_scheduler: Optional[BackgroundScheduler] = None
_run_lock = threading.Lock()
_db_lock_session = None
last_result: Optional[dict] = None


def _acquire_database_lock() -> bool:
    """Uses a PostgreSQL advisory lock to elect one scheduler owner per DB."""
    global _db_lock_session
    if db.engine.dialect.name != "postgresql":
        return True
    if _db_lock_session is not None:
        return True
    session = db.SessionLocal()
    try:
        locked = session.execute(text("SELECT pg_try_advisory_lock(812734109)"))
        if not bool(locked.scalar()):
            session.close()
            return False
        _db_lock_session = session
        return True
    except Exception:  # noqa: BLE001
        session.close()
        return False


def _job() -> None:
    global last_result
    if not _run_lock.acquire(blocking=False):
        # Предыдущий прогон ещё выполняется — пропускаем.
        return
    if not _acquire_database_lock():
        _run_lock.release()
        return
    try:
        try:
            last_result = run_parse_once(settings)
        except Exception as exc:  # noqa: BLE001
            last_result = {"status": "error", "errors": [str(exc)]}
    finally:
        _run_lock.release()


def start_scheduler() -> None:
    """Запускает периодический планировщик без сетевого запроса при старте."""
    global _scheduler
    if not settings.scheduler_enabled:
        return
    try:
        worker_count = int(os.getenv("WEB_CONCURRENCY", "1"))
    except ValueError:
        worker_count = 1
    if worker_count > 1 and not settings.scheduler_allow_multi_worker:
        # A scheduler needs a single owner. Run it in a dedicated one-worker process.
        return
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

    if settings.scheduler_run_on_start:
        threading.Thread(target=_job, daemon=True).start()


def shutdown_scheduler() -> None:
    global _scheduler, _db_lock_session
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
    if _db_lock_session is not None:
        _db_lock_session.close()
        _db_lock_session = None


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
