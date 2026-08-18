from app.parser.telegram import normalize_channel
from app.telegram_auth import _code_method_name


def test_at_username():
    assert normalize_channel("@arendakhm") == "arendakhm"


def test_url():
    assert normalize_channel("https://t.me/arendakhm") == "arendakhm"


def test_url_trailing_slash():
    assert normalize_channel("https://t.me/arendakhm/") == "arendakhm"


def test_plain():
    assert normalize_channel("arendakhm") == "arendakhm"


def test_case():
    assert normalize_channel("@ArendaKhm") == "arendakhm"


class _MockCode:
    def __init__(self, type_name: str):
        self.type = type(type_name, (), {})()


def test_code_method_app():
    assert "приложение Telegram" in _code_method_name(_MockCode("SentCodeTypeApp"))


def test_code_method_sms():
    assert "SMS" in _code_method_name(_MockCode("SentCodeTypeSms"))


def test_code_method_call():
    assert "звонком" in _code_method_name(_MockCode("SentCodeTypeCall"))
