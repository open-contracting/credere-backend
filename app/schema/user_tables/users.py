from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

from app.schema.core_tables.core import Lender


class UserType(Enum):
    OCP_admin = "OCP Admin"
    FI_user = "FI User"


class ApplicationActionType(Enum):
    MSME_ACCESS_FROM_LINK = "MSME access from link"
    MSME_DECLINE_INVITATION = "MSME decline invitation"
    MSME_ACCEPT_INVITATION = "MSME accept invitation"
    AWARD_UPDATE = "Award Update"
    BORROWER_UPDATE = "Borrower Update"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_actions: List["ApplicationAction"] = Relationship(back_populates="user")
    type: UserType = Field(default=UserType.FI_user)
    language: str = Field(default="es")  # "ISO 639-1 language code"
    email: str = Field(default="")
    external_id: str = Field(default="")
    lender_id: Optional[int] = Field(default=None)
    lender: "Lender" = Relationship(back_populates="user")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))


class ApplicationAction(SQLModel, table=True):
    __tablename__ = "application_action"
    id: Optional[int] = Field(default=None, primary_key=True)
    type: ApplicationActionType = Field(default=ApplicationActionType.AWARD_UPDATE)
    data: dict = Field(default={}, sa_column=Column(JSON))
    application_id: str = Field(default="")
    user_id: int = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="application_actions")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))

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
