import typing as T

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)
    logins: T.List["Login"] = relationship("Login", back_populates="user")


class Login(Base):
    __tablename__ = "logins"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user: "User" = relationship("User", back_populates="logins")
    time = Column(DateTime)

