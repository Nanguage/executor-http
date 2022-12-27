import typing as T
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from .user_db.database import SessionAsync
from .user_db import schemas, crud, models, utils
from . import config


token_getter: T.Callable
if config.user_mode != "free":
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")
    token_getter = oauth2_scheme
else:
    token_getter = lambda: "fake_token"


async def get_db():
    if config.user_mode != "free":
        db = SessionAsync()
        try:
            yield db
        finally:
            await db.close()
    else:
        yield None


async def get_current_user(
        token: str = Depends(token_getter),
        db: AsyncSession = Depends(get_db),
        ) -> T.Optional[schemas.User]:
    if config.user_mode != "free":
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, config.jwt_secret_key, [config.jwt_algorithm])
            username = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        user = await crud.get_user_by_username(db, username)
        if user is None:
            raise credentials_exception
        return schemas.User(
            username=user.username, role=user.role, id=user.id,
        )
    else:
        return None


async def auth_user(
        db: AsyncSession,
        username: str, password: str,
        ) -> T.Union[T.Literal[False], models.User]:
    user = await crud.get_user_by_username(db, username)
    if user is None:
        return False
    hashed = user.hashed_password
    if hashed is None:
        return False
    if not utils.verify_password(password, hashed):
        return False
    return user


def create_access_token(
        subject: T.Union[str, T.Any],
        ) -> str:
    expires_delta = datetime.utcnow() + timedelta(minutes=config.access_token_expire_minutes)
    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, config.jwt_secret_key, config.jwt_algorithm)
    return encoded_jwt
