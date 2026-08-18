import pytest

from app.parser.city_map import normalize_city


def test_uk():
    assert normalize_city("Хмельницький") == "khmelnitskiy"


def test_ru():
    assert normalize_city("Хмельницкий") == "khmelnitskiy"


def test_case_and_spaces():
    assert normalize_city("  ХМЕЛЬНИЦЬКИЙ  ") == "khmelnitskiy"


def test_unknown_raises():
    with pytest.raises(ValueError):
        normalize_city("НетТакогоГорода")
