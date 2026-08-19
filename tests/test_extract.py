from app.parser.extract import (
    parse_district,
    parse_price_currency,
    parse_price_info,
    parse_price_value,
    parse_rooms,
    parse_tg_price,
)
from app.parser.date_parser import parse_olx_date


def test_price_simple():
    assert parse_price_value("13 000 грн.") == 13000.0


def test_price_decimal():
    assert parse_price_value("35 843.63 грн.") == 35843.63


def test_price_negotiable():
    assert parse_price_value("Договірна") is None


def test_price_with_negotiable():
    assert parse_price_value("18 000 грн. Договірна") == 18000.0


def test_price_currency_is_preserved():
    assert parse_price_info("$315") == (315.0, "USD")
    assert parse_price_currency("20 000 грн") == "UAH"


def test_telegram_phone_is_not_a_price():
    assert parse_tg_price("Телефон 067 123 45 67") is None


def test_relative_week_date():
    assert parse_olx_date("1 тиж. тому") is not None


def test_rooms_explicit():
    assert parse_rooms("Оренда 2к квартири") == 2


def test_rooms_kimnata():
    assert parse_rooms("2-кімнатна квартира") == 2


def test_rooms_ukrainian_and_keycap_forms():
    assert parse_rooms("Двохкімнатна квартира") == 2
    assert parse_rooms("2️⃣ - КІМНАТНА квартира") == 2
    assert parse_rooms("1- кімнатна квартира") == 1


def test_rooms_word():
    assert parse_rooms("однокімнатна квартира") == 1


def test_rooms_three_word():
    assert parse_rooms("трикімнатна квартира") == 3


def test_rooms_abbreviation():
    assert parse_rooms("Оренда 2 кімн. новобудови") == 2


def test_tg_price_marker():
    assert parse_tg_price("1️⃣ КІМНАТНА КВАРТИРА 💰 20000 грн") == 20000.0


def test_tg_price_kp():
    assert parse_tg_price("3-кімнатна. Центр. Новобудова. 20000+кп Юлія") == 20000.0


def test_tg_price_grn():
    assert parse_tg_price("Здам 1 кімнату в центрі 12000 грн") == 12000.0


def test_rooms_studio():
    assert parse_rooms("Студія в центрі") == 1


def test_district_dubovo():
    assert parse_district("Оренда 1к квартири на Дубово") == "Дубово"


def test_district_center():
    assert parse_district("Здам 2к в Центрі на Проскурівській") == "Центр"


def test_district_none():
    assert parse_district("Оренда квартири") is None


def test_district_street_vs_area():
    assert parse_district("2-кімнатна. Виставка. Вул.Зарічанська, 9") == "Виставка"
