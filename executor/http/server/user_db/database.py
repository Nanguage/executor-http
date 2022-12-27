from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from ..config import user_database_url


engine = create_engine(
    user_database_url, connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_async_url(url: str) -> str:
    parts = url.split(":///")
    if "+" not in parts[0]:
        if parts[0] == "sqlite":
            parts[0] = parts[0] + "+aiosqlite"
    res = parts[0] + ":///" + parts[1]
    return res

engine_async = create_async_engine(get_async_url(user_database_url), echo=False)
SessionAsync = sessionmaker(
    bind=engine_async, 
    class_=AsyncSession,
    expire_on_commit=False,)  # type: ignore

Base = declarative_base()
