from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, autoincrement=True)
    type: str
    data: dict = Field(default={}, sa_column=Column(JSON))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
