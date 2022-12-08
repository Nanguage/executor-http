import typing as T
from datetime import datetime

from pydantic import BaseModel


class Login(BaseModel):
    id: int
    user_id: int
    time: datetime

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    username: str
    role: str


class User(UserBase):
    id: int
    hashed_password: str
    logins: T.List[Login] = []

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str
