import typing as T

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..user_db.schemas import Token
from ..utils.auth import (
    get_db, auth_user, create_access_token, get_current_user
)
from ..user_db import crud
from ..user_db.schemas import User
from ..utils import get_app, CustomFastAPI

router = APIRouter(prefix="/user")


@router.post("/token")
async def token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db),
        app: "CustomFastAPI" = Depends(get_app)
        ) -> Token:
    user = await auth_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.id is not None:
        await crud.create_user_login(db, user.id)
    access_token = create_access_token(
        user.username, app.config.access_token_expire_minutes,
        app.config.jwt_secret_key, app.config.jwt_algorithm)
    return Token(access_token=access_token)


@router.get("/info")
async def user_info(
        user: T.Optional[User] = Depends(get_current_user)):
    return user
