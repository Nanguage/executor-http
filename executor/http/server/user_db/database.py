from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from ..config import user_database_url


engine = create_engine(
    user_database_url, connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
