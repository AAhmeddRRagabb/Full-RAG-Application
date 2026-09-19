
import hashlib
import secrets


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)

def hash_session_token(token: str) -> str:
    return hashlib.sha256(
        data = token.encode("utf-8")
    ).hexdigest()

def build_redis_session_key(token_hash: str) -> str:
    return f"session:{token_hash}"

def build_redis_user_version_key(user_id) -> str:
    return f"user-session-version:{user_id}"