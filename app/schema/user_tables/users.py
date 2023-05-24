from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_actions: List["ApplicationAction"] = Relationship(back_populates="user")
    type: str = Field(default="")
    language: str = Field(default="Spanish")
    email: str = Field(default="")
    external_id: str = Field(default="")
    fl_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class ApplicationAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(default="")
    data: dict = Field(default={}, sa_column=Column(JSON))
    application_id: str = Field(default="")
    user_id: int = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="application_actions")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
