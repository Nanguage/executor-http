import typing as T
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from executor.engine.job import Job

from .user_db.database import SessionAsync
from .user_db import schemas, crud, models, utils
from .user_db.schemas import User, role_priority_over
from . import config
from .utils.oauth2cookie import OAuth2PasswordBearerCookie


def fake_token():
    return "fake_token"


token_getter: T.Callable
if config.user_mode != "free":
    oauth2_scheme = OAuth2PasswordBearerCookie(tokenUrl="user/token")
    token_getter = oauth2_scheme
else:
    token_getter = fake_token


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
            payload = jwt.decode(
                token, config.jwt_secret_key, [config.jwt_algorithm])
            username = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:  # type: ignore
            raise credentials_exception
        user = await crud.get_user_by_username(db, username)
        if user is None:
            raise credentials_exception
        return schemas.User(
            username=user.username, role=user.role, id=user.id,  # type: ignore
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
    dt = timedelta(minutes=config.access_token_expire_minutes)
    expires_delta = datetime.utcnow() + dt
    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, config.jwt_secret_key, config.jwt_algorithm)
    return encoded_jwt


def user_can_access(user: User, job: Job) -> bool:
    job_user: T.Optional[User] = job.attrs.get("user")
    if job_user is not None:
        if user.username == job_user.username:
            return True
        if role_priority_over(user.role, job_user.role):
            return True
    return False


def check_user_job(user: T.Optional[User], job: Job) -> Job:
    if user is None:
        return job
    else:
        if user_can_access(user, job):
            return job
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Can't access to the job."
        )
