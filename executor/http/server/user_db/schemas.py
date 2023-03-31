import typing as T
from datetime import datetime

from pydantic import BaseModel


class Login(BaseModel):
    id: int
    user_id: int
    time: datetime

    class Config:
        orm_mode = True


Role = T.Literal["root", "admin", "user"]
_role_order = ['root', 'admin', 'user']


def role_priority_over(role1: Role, role2: Role) -> bool:
    """role1 is greater or equal than(>=) role2"""
    idx1 = _role_order.index(role1)
    idx2 = _role_order.index(role2)
    if idx1 <= idx2:
        return True
    else:
        return False


class UserBase(BaseModel):
    username: str
    role: Role


class User(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
