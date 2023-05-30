from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, Relationship, SQLModel


class UserType(Enum):
    OCP_admin = "OCP Admin"
    FI_user = "FI User"


class ApplicationActionType(Enum):
    MSME_ACCESS_FROM_LINK = "MSME access from link"
    MSME_DECLINE_INVITATION = "MSME decline invitation"
    MSME_ACCEPT_INVITATION = "MSME accept invitation"
    AWARD_UPDATE = "Award Update"
    BORROWER_UPDATE = "Borrower Update"
    TBD = "TBD"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_actions: List["ApplicationAction"] = Relationship(back_populates="user")
    type: UserType = Field(default=UserType.FI_user)
    language: str = Field(default="Spanish")
    email: str = Field(default="")
    external_id: str = Field(default="")
    fl_id: Optional[int] = Field(default=None)
    created_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))


class ApplicationAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: ApplicationActionType = Field(default=ApplicationActionType.AWARD_UPDATE)
    data: dict = Field(default={}, sa_column=Column(JSON))
    application_id: str = Field(default="")
    user_id: int = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="application_actions")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
