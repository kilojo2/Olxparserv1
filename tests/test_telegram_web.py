from app.parser.telegram_web import _build_card


def test_telegram_message_id_contains_channel():
    card = _build_card("first_channel", "42", "Здам квартиру 💰 315 $", None)
    assert card["olx_id"] == "tg-first_channel-42"
    assert card["price_value"] == 315.0
    assert card["currency"] == "USD"
