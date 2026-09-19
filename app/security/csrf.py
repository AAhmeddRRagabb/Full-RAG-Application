import hashlib
import secrets
import hmac
from helpers.config import get_settings
settings = get_settings()



def create_csrf_token(session_hash: str) -> str:
    nonce = secrets.token_urlsafe(32)
    message = f"{session_hash}.{nonce}".encode("utf-8")
    secret = settings.csrf_secret.get_secret_value().encode("utf-8")

    signature = hmac.new(
        secret,
        message,
        hashlib.sha256
    ).hexdigest()

    return f"{nonce}.{signature}"



def verify_csrf_token(session_hash: str, csrf_token: str) -> bool:
    try:
        nonce, supplied_signature = csrf_token.split(".", maxsplit = 1)
    except ValueError:
        return False

    message = f"{session_hash}.{nonce}".encode("utf-8")
    secret = settings.csrf_secret.get_secret_value().encode("utf-8")

    expected_signature = hmac.new(
        secret,
        message,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(
        supplied_signature,
        expected_signature
    )
