from app.parser.telegram import normalize_channel


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
