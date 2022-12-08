from datetime import datetime
import typing as T

from sqlalchemy.orm import Session

from . import models, schemas, utils


def get_user_by_username(db: Session, username: str) -> T.Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = utils.get_hashed_password(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user_login(db: Session, user_id: int) -> models.Login:
    login = models.Login(user_id=user_id, time=datetime.utcnow())
    db.add(login)
    return login

