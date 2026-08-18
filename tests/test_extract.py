from app.parser.extract import parse_district, parse_price_value, parse_rooms


def test_price_simple():
    assert parse_price_value("13 000 грн.") == 13000.0


def test_price_decimal():
    assert parse_price_value("35 843.63 грн.") == 35843.63


def test_price_negotiable():
    assert parse_price_value("Договірна") is None


def test_price_with_negotiable():
    assert parse_price_value("18 000 грн. Договірна") == 18000.0


def test_rooms_explicit():
    assert parse_rooms("Оренда 2к квартири") == 2


def test_rooms_kimnata():
    assert parse_rooms("2-кімнатна квартира") == 2


def test_rooms_word():
    assert parse_rooms("однокімнатна квартира") == 1


def test_rooms_three_word():
    assert parse_rooms("трикімнатна квартира") == 3


def test_rooms_studio():
    assert parse_rooms("Студія в центрі") == 1


def test_district_dubovo():
    assert parse_district("Оренда 1к квартири на Дубово") == "Дубово"


def test_district_center():
    assert parse_district("Здам 2к в Центрі на Проскурівській") == "Центр"


def test_district_none():
    assert parse_district("Оренда квартири") is None
