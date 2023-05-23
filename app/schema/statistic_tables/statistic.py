from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, SQLModel


class Statistic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str
    data: dict = Field(default={}, sa_column=Column(JSON))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
