import typing as T
from datetime import datetime

from pydantic import BaseModel


class Login(BaseModel):
    id: int
    user_id: int
    time: datetime

    class Config:
        orm_mode = True


Roles = T.Literal["root", "admin", "user"]


class UserBase(BaseModel):
    username: str
    role: Roles


class User(UserBase):
    id: int
    hashed_password: str
    logins: T.List[Login] = []

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
