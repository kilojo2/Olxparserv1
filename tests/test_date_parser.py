from datetime import datetime

from app.parser.date_parser import age_days, parse_olx_date

NOW = datetime(2026, 8, 18, 20, 0, 0)


def test_today_uk():
    assert parse_olx_date("Сьогодні о 12:04", NOW) == datetime(2026, 8, 18, 12, 4)


def test_today_ru():
    assert parse_olx_date("Сегодня в 09:15", NOW) == datetime(2026, 8, 18, 9, 15)


def test_yesterday_uk():
    assert parse_olx_date("Вчора о 18:00", NOW) == datetime(2026, 8, 17, 18, 0)


def test_yesterday_ru():
    assert parse_olx_date("Вчера в 23:59", NOW) == datetime(2026, 8, 17, 23, 59)


def test_absolute_uk():
    assert parse_olx_date("17 серпня 2026 р.", NOW) == datetime(2026, 8, 17)


def test_absolute_ru():
    assert parse_olx_date("16 августа 2026 г.", NOW) == datetime(2026, 8, 16)


def test_days_ago():
    assert parse_olx_date("2 дні тому", NOW) == datetime(2026, 8, 16)


def test_unknown_returns_none():
    assert parse_olx_date("щось незрозуміле", NOW) is None


def test_age_days_fresh():
    pub = datetime(2026, 8, 17, 12, 0)
    assert age_days(pub, NOW) < 2


def test_age_days_old():
    pub = datetime(2026, 8, 10, 12, 0)
    assert age_days(pub, NOW) > 2
