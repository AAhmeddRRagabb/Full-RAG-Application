# ------------------------------------------------------
# User authentication routes
# ------------------------------------------------------

from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis, RedisError

import helpers.config as CFG
from fastapi_core.dependecies.auth import require_authentication, require_csrf
from fastapi_core.dependecies.redis import get_redis
from helpers.config import get_settings
from helpers.functional import raise_internal_server_error
from models.db_objects_models import UserModel
from models.db_schemas import User
from models.db_schemas.redis_data import SessionData
from models.enums import ResponsesEnum
from models.request_schemas.auth import (
    CsrfResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserPublic,
)
from models.system_schemas import AuthContext
from security.csrf import create_csrf_token
from security.passwords import hash_password, verify_password
from security.session_management import (
    build_redis_session_key,
    build_redis_user_version_key,
    generate_session_token,
    hash_session_token,
)

settings = get_settings()

auth_router = APIRouter(
    prefix=CFG.AUTH_ROUTES_PATH,
    tags=["account"],
)




def build_public_user(user: User) -> UserPublic:
    return UserPublic(
        user_name = user.user_name,
        user_email = user.user_email,
    )




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




@auth_router.post("/register")
async def register_user(
    request: Request,
    response: Response,
    register_request: RegisterRequest,
    redis: Annotated[Redis, Depends(get_redis)],
) -> RegisterResponse:
    user_model = UserModel(db_client=request.app.db_client)

    if await user_model.get_user_by_email(register_request.email):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = ResponsesEnum.USER_FOUND_ALREADY.value,
        )

    try:
        user = User(
            user_name = register_request.user_name,
            user_email = register_request.email,
            user_password_hash = hash_password(register_request.password),
        )
    except Exception:
        raise_internal_server_error()

    if not await user_model.insert_user(user):
        raise_internal_server_error()

    csrf_token = await create_user_session(response = response, redis = redis, user = user)

    return RegisterResponse(
        message = ResponsesEnum.USER_REGISTERED_SUCCESSFULLY.value,
        user = build_public_user(user),
        csrf_token = csrf_token,
    )




@auth_router.post("/login")
async def login_user(
    request      : Request,
    response     : Response,
    login_request: LoginRequest,
    redis        : Annotated[Redis, Depends(get_redis)],
) -> LoginResponse:
    
    user_model = UserModel(db_client = request.app.db_client)
    user = await user_model.get_user_by_email(login_request.email)

    if not user or not verify_password(
        password = login_request.password,
        expected_password_hash = user.user_password_hash,
    ):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = ResponsesEnum.USER_LOGIN_ERROR.value,
        )

    csrf_token = await create_user_session(response=response, redis=redis, user=user)

    return LoginResponse(
        message = "Login successful",
        user = build_public_user(user),
        csrf_token = csrf_token,
    )




@auth_router.get("/me")
async def get_current_user(
    auth: Annotated[AuthContext, Depends(require_authentication)],
) -> UserPublic:
    return build_public_user(auth.user)




@auth_router.get("/csrf", response_model = CsrfResponse)
async def get_csrf_token(
    auth: Annotated[AuthContext, Depends(require_authentication)],
) -> CsrfResponse:
    return CsrfResponse(
        csrf_token = create_csrf_token(auth.session_hash),
    )




@auth_router.post("/logout")
async def logout_user(
    response: Response,
    auth    : Annotated[AuthContext, Depends(require_csrf)],
    redis   : Annotated[Redis, Depends(get_redis)],
) -> dict[str, str]:
    
    try:
        await redis.delete(auth.session_key)
    except RedisError:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = "Authentication service unavailable",
        )

    response.delete_cookie(
        key = settings.session_cookie_name,
        path = "/",
    )

    return {
        "message": "Logged out successfully",
    }
