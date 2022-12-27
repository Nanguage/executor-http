import typing as T
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from .user_db.database import SessionLocal
from .user_db import schemas, crud, models, utils
from . import config


token_getter: T.Callable
if config.user_mode != "free":
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")
    token_getter = oauth2_scheme
else:
    token_getter = lambda: "fake_token"


def get_db():
    if config.user_mode != "free":
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    else:
        yield None


def get_current_user(
        token: str = Depends(token_getter),
        db: Session = Depends(get_db),
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
        user = crud.get_user_by_username(db, username)
        if user is None:
            raise credentials_exception
        return schemas.User(
            username=user.username, role=user.role, id=user.id,
        )
    else:
        return None


def auth_user(
        db: Session,
        username: str, password: str,
        ) -> T.Union[T.Literal[False], models.User]:
    user = crud.get_user_by_username(db, username)
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


def reload():
    """Reload for switch user-mode."""
    import importlib
    from . import auth
    from .routers import file, job, monitor, proxy, task
    modules = [auth, file, job, monitor, proxy, task]
    for mod in modules:
        importlib.reload(mod)
