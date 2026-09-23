

# utils
from datetime import datetime, timezone
from typing import Annotated
from pydantic import ValidationError
from helpers.config import get_settings


from fastapi import (
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)

from app_core.dependecies.clients import get_redis, get_db_client

# clients
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# models
from models.db_schemas.redis_data import SessionData
from models.system_schemas import AuthContext
from models.db_objects_models import UserModel

# security
from security.session_management import hash_session_token
from security.csrf import verify_csrf_token
from security.session_management import build_redis_session_key, build_redis_user_version_key






async def require_authentication(
    request  : Request,
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    redis    : Annotated[Redis, Depends(get_redis)]
) -> AuthContext:
    user_model = UserModel(db_client = db_client)

    # - get the session from the request cookie
    raw_token = request.cookies.get(get_settings().session_cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Authentication Required"
        )

    # - get the session from Redis
    token_hash = hash_session_token(raw_token)
    session_key = build_redis_session_key(token_hash)

    try:
        stored_session = await redis.get(session_key)
    except RedisError:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = "Authentication is Unavailable"
        )

    if stored_session is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid Credentials"
        )


    try:
        session_data = SessionData.model_validate_json(stored_session)
    except ValidationError:
        await redis.delete(session_key)
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid session",
        )

    # - check session expiration
    now = datetime.now(timezone.utc)
    if session_data.expires_at <= now:
        await redis.delete(session_key)

        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Session expired",
        )

    # - check user version key
    user_version_key = build_redis_user_version_key(user_id = session_data.user_uuid)
    user_version_val = int(await redis.get(user_version_key) or 0)

    if session_data.session_version != user_version_val:
        await redis.delete(session_key)
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Session revoked",
        )

    # - get user
    user = await user_model.get_user_by_uuid(user_uuid = session_data.user_uuid)

    if user is None:
        await redis.delete(session_key)

        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "User no longer exists",
        )

    # - update ttl
    remaining_absolute_seconds = int((session_data.expires_at - now).total_seconds())
    idle_seconds = (get_settings().session_idle_minutes * 60)
    new_ttl = min(idle_seconds, remaining_absolute_seconds)

    if new_ttl <= 0:
        await redis.delete(session_key)

        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Session expired",
        )

    # update session
    await redis.expire(
        session_key,
        new_ttl,
    )

    return AuthContext(
        user         = user,
        session_data = session_data,
        session_key  = session_key,
        session_hash = token_hash,
    )




async def require_csrf(
    auth      : Annotated[AuthContext, Depends(require_authentication)], 
    csrf_token: Annotated[str | None, Header(alias = "X-CSRF-Token")] = None
) -> AuthContext:
    
    if csrf_token is None:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Missing CSRF token",
        )

    valid = verify_csrf_token(
        csrf_token = csrf_token,
        session_hash = auth.session_hash,
    )

    if not valid:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Invalid CSRF token",
        )

    return auth
