from typing import Optional

from pydantic import BaseModel
from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(
        sa_column=Column(BigInteger(), primary_key=True, autoincrement=True)
    )
    type: str
    email: str
    external_id: str
    fl_id: Optional[int] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True


class BasicUser(BaseModel):
    username: str
    name: Optional[str]
    password: Optional[str]
    temp_password: Optional[str]


class SetupMFA(BaseModel):
    temp_password: str
    session: str
    secret: str
