from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependecies.clients import get_db_client, get_redis
from core.system_settings import get_system_settings as get_settings
from models.db_models import UserModel
from models.db_schemas.redis_data import SessionData
from models.db_schemas.redis_data import AuthContext
from core.auth.csrf import verify_csrf_token
from core.auth.session_management import (
    build_redis_session_key,
    build_redis_user_version_key,
    hash_session_token,
)

from models.enums import ResponsesEnum


async def require_authentication(
    request  : Request,
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    redis    : Annotated[Redis, Depends(get_redis)]
) -> AuthContext:
    user_model = UserModel(db_client = db_client)

    # - get the session from the request cookie
    raw_token = request.cookies.get(get_settings().SESSION_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = ResponsesEnum.AUTH_REQUIRED.value
        )

    # - get the session from Redis
    token_hash = hash_session_token(raw_token)
    session_key = build_redis_session_key(token_hash)

    try:
        stored_session = await redis.get(session_key)
    except RedisError:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = ResponsesEnum.AUTH_NOT_AVAILABLE.value
        )

    if stored_session is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = ResponsesEnum.AUTH_INVALID_CRED.value
        )


    try:
        session_data = SessionData.model_validate_json(stored_session)
    except ValidationError:
        await redis.delete(session_key)
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = ResponsesEnum.AUTH_INVALID_SESSION.value
        )

    # - check session expiration
    now = datetime.now(timezone.utc)
    if session_data.expires_at <= now:
        await redis.delete(session_key)

        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = ResponsesEnum.AUTH_INVALID_SESSION.value
        )

    # - check user version key
    user_version_key = build_redis_user_version_key(user_uuid = session_data.user_uuid)
    user_version_val = int(await redis.get(user_version_key) or 0)

    if session_data.session_version != user_version_val:
        await redis.delete(session_key)
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = ResponsesEnum.AUTH_INVALID_CRED.value
        )

    # - get user
    user = await user_model.get_user_by_uuid(user_uuid = session_data.user_uuid)

    if user is None:
        await redis.delete(session_key)

        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = ResponsesEnum.AUTH_INVALID_CRED.value
        )

    # - update ttl
    remaining_absolute_seconds = int((session_data.expires_at - now).total_seconds())
    idle_seconds = (get_settings().SESSION_IDLE_MINUTES * 60)
    new_ttl = min(idle_seconds, remaining_absolute_seconds)

    if new_ttl <= 0:
        await redis.delete(session_key)

        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = ResponsesEnum.AUTH_INVALID_SESSION.value
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
            detail = ResponsesEnum.AUTH_INVALID_CRED.value
        )

    valid = verify_csrf_token(
        csrf_token = csrf_token,
        session_hash = auth.session_hash,
    )

    if not valid:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = ResponsesEnum.AUTH_INVALID_CRED.value
        )

    return auth
