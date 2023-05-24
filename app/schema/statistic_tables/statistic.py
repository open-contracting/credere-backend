from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, SQLModel


class StatisticType(Enum):
    MSME_OPT_IN_STATISTICS = "MSME opt-in statistics"
    APPLICATION_KPIS = "Application KPIs"
    TBD = "TBD"


class Statistic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: StatisticType = Field(default=StatisticType.MSME_OPT_IN_STATISTICS)
    data: dict = Field(default={}, sa_column=Column(JSON))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
