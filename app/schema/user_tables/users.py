from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import BigInteger, Column, DateTime
from datetime import datetime


class User(SQLModel, table=True):
    id: Optional[int] = Field(sa_column=Column(BigInteger(), primary_key=True, autoincrement=True))
    type: str
    email: str
    external_id: str
    fl_id: Optional[int] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True
