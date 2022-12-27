from datetime import datetime
import typing as T

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from . import models, schemas, utils, database
from .. import config


def init_db():
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    init_users(db)


def init_users(db: Session) -> T.Optional[models.User]:
    root_password = config.root_password
    if root_password is None:
        return None
    root = _get_user_by_username_sync(db, "root")
    if root is None:
        create = schemas.UserCreate(
            username="root", role="root", password=root_password)
        create_user(db, create)
    else:
        root.hashed_password = utils.get_hashed_password(root_password)
        db.commit()
        db.refresh(root)
    return root


def _get_user_by_username_sync(db: Session, username: str) -> T.Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


async def get_user_by_username(db: AsyncSession, username: str) -> T.Optional[models.User]:
    stmt = select(models.User).filter(models.User.username == username)
    async with db.begin():
        res = await db.execute(stmt)
    user = res.scalars().first()
    return user


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


async def create_user_login(db: AsyncSession, user_id: int) -> models.Login:
    login = models.Login(user_id=user_id, time=datetime.utcnow())
    async with db.begin():
        db.add(login)
    await db.commit()
    return login

