# ------------------------------------------------------
# User authentication routes
# ------------------------------------------------------

# utils
from typing import Annotated

import helpers.config as CFG
from helpers.functional import raise_internal_server_error
from helpers.config import get_settings
settings = get_settings()


# fastapi
from fastapi import APIRouter, Depends, HTTPException, Response, status
from app_core.dependecies.auth import require_authentication, require_csrf
from app_core.dependecies.clients import get_redis, get_db_client


# databases
from redis.asyncio import Redis, RedisError
from sqlalchemy.ext.asyncio import AsyncSession

# models
from models.db_schemas import User
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

from models.db_objects_models import UserModel

# security
from security.csrf import create_csrf_token
from security.passwords import hash_password, verify_password
from security.session_management import create_user_session



auth_router = APIRouter(
    prefix = CFG.AUTH_ROUTES_PATH,
    tags = ["account"],
)




def build_public_user(user: User) -> UserPublic:
    return UserPublic(
        user_name = user.user_name,
        user_email = user.user_email,
    )






# controllers
from controllers import UserController

@auth_router.post("/register")
async def register_user(
    register_request: RegisterRequest,
    db_client       : Annotated[AsyncSession, Depends(get_db_client)],
    redis           : Annotated[Redis, Depends(get_redis)],
    response        : Response,
) -> RegisterResponse:
    
    user_model = UserModel(db_client = db_client)

    # - if already exists
    if await user_model.get_user_by_email(register_request.email):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = ResponsesEnum.USER_FOUND_ALREADY.value,
        )

    # - insert user
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

    # - create session
    csrf_token = await create_user_session(response = response, redis = redis, user = user)

    return RegisterResponse(
        message = ResponsesEnum.USER_REGISTERED_SUCCESSFULLY.value,
        user = build_public_user(user),
        csrf_token = csrf_token,
    )




@auth_router.post("/login")
async def login_user(
    login_request: LoginRequest,
    db_client    : Annotated[AsyncSession, Depends(get_db_client)],
    redis        : Annotated[Redis, Depends(get_redis)],
    response     : Response,
) -> LoginResponse:
    
    user_model = UserModel(db_client = db_client)
    user = await user_model.get_user_by_email(login_request.email)

    if not user or not verify_password(
        password = login_request.password,
        expected_password_hash = user.user_password_hash,
    ):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = ResponsesEnum.USER_LOGIN_ERROR.value,
        )

    csrf_token = await create_user_session(response = response, redis = redis, user = user)

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
