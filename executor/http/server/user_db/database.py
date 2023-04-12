from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, AsyncEngine
)


def get_engine(user_database_url: str) -> Engine:
    engine = create_engine(
        user_database_url, connect_args={"check_same_thread": False},
    )
    return engine


def get_async_engine(user_database_url: str) -> AsyncEngine:
    engine = create_async_engine(
        get_async_url(user_database_url), echo=False
    )
    return engine


def get_local_session(engine: Engine) -> Session:
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_async_session(engine: AsyncEngine) -> AsyncSession:
    SessionAsync = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,)  # type: ignore
    return SessionAsync()


def get_async_url(url: str) -> str:
    parts = url.split(":///")
    if "+" not in parts[0]:
        if parts[0] == "sqlite":
            parts[0] = parts[0] + "+aiosqlite"
    res = parts[0] + ":///" + parts[1]
    return res
