from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(sa_column=Column(BigInteger(), primary_key=True, autoincrement=True))
    application_actions: List["ApplicationAction"] = Relationship(back_populates="user")
    type: str
    language: str = Field(default=None)
    email: str
    external_id: str
    fl_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))

    class Config:
        arbitrary_types_allowed = True


class ApplicationAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str
    data: dict = Field(default={}, sa_column=Column(JSON))
    application_id: str
    user_id: int = Field(sa_column=Column(BigInteger(), ForeignKey("user.id")))

    user: Optional[User] = Relationship(back_populates="application_actions")

    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))

    class Config:
        arbitrary_types_allowed = True
