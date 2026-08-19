from cryptography.fernet import InvalidToken

from app import settings_store
from app.config import settings


def test_telegram_secret_ciphertext_is_not_plaintext(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "a-long-test-secret-key-for-fernet")
    fernet = settings_store._fernet()
    ciphertext = fernet.encrypt(b"telegram-session-value").decode()
    assert "telegram-session-value" not in ciphertext
    assert fernet.decrypt(ciphertext.encode()) == b"telegram-session-value"


def test_wrong_secret_key_cannot_decrypt(monkeypatch):
    monkeypatch.setattr(settings, "secret_key", "first-secret-key-for-fernet")
    ciphertext = settings_store._fernet().encrypt(b"secret").decode()
    monkeypatch.setattr(settings, "secret_key", "second-secret-key-for-fernet")
    try:
        settings_store._fernet().decrypt(ciphertext.encode())
    except InvalidToken:
        return
    raise AssertionError("ciphertext decrypted with a different SECRET_KEY")
