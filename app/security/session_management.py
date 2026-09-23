
# utils
from helpers.config import get_settings
settings = get_settings()

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from security.csrf import create_csrf_token
from redis.asyncio import Redis, RedisError

# models
from models.db_schemas import User
from models.db_schemas.redis_data import SessionData

# fastapi
from fastapi import Response, HTTPException, status



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


async def create_user_session(
    response: Response,
    redis   : Redis,
    user    : User,
) -> str:
    now = datetime.now(timezone.utc)
    session_expires_at = now + timedelta(days=settings.session_absolute_days)
    user_version_key = build_redis_user_version_key(user.user_uuid)

    try:
        current_version = int(await redis.get(user_version_key) or 0)
        raw_session_token = generate_session_token()
        token_hash = hash_session_token(raw_session_token)
        session_key = build_redis_session_key(token_hash)

        session_data = SessionData(
            user_uuid=user.user_uuid,
            created_at=now,
            expires_at=session_expires_at,
            session_version=current_version,
        )

        initial_ttl = min(
            settings.session_idle_minutes * 60,
            settings.session_absolute_days * 24 * 60 * 60,
        )

        session_created = await redis.set(
            name=session_key,
            value=session_data.model_dump_json(),
            ex=initial_ttl,
            nx=True,
        )

    except RedisError:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = "Authentication service unavailable",
        )

    if not session_created:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create session",
        )

    response.set_cookie(
        key = settings.session_cookie_name,
        value = raw_session_token,
        max_age   = settings.session_absolute_days * 24 * 60 * 60,
        expires = session_expires_at,
        path = "/",
        httponly = True,
        samesite = "lax",
    )

    return create_csrf_token(token_hash)