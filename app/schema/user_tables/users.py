from typing import Optional

from pydantic import BaseModel
from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(sa_column=Column(BigInteger(), primary_key=True, autoincrement=True))
    type: str
    email: str
    external_id: str
    fl_id: Optional[int] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True


class Login(BaseModel):
    username: str
    password: str


class OnlyUsername(BaseModel):
    username: str


class ChangePassword(BaseModel):
    username: str
    new_password: str
    temp_password: str
