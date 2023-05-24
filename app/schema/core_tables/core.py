from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import DECIMAL, Column, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, Relationship, SQLModel


class BorrowerDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id")
    application: Optional["Application"] = Relationship(back_populates="borrower_document")
    type: str = Field(default="")
    verified: bool
    file: bytes
    name: str = Field(default="")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    submitted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    borrower_documents: List["BorrowerDocument"] = Relationship(back_populates="application")
    award_id: int = Field(foreign_key="award.id")
    uuid: str = Field(unique=True, default="")
    primary_email: str = Field(default="")
    status: str = Field(default="")
    stage: str = Field(default="")
    award_borrowed_identifier: str = Field(default="")
    borrower_id: Optional[int] = Field(foreign_key="borrower.id")
    lender_id: Optional[int] = Field(foreign_key="lender.id")
    contract_amount_submitted: Optional[Decimal] = Field(
        sa_column=Column(DECIMAL(precision=12, scale=2), nullable=False)
    )
    amount_requested: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=12, scale=2), nullable=False))
    currency: str = Field(default="")
    repayment_months: int
    calculator_data: dict = Field(default={}, sa_column=Column(JSON))
    borrower_submitted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    borrower_accepted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    borrower_declined_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    borrower_declined_preferences_data: dict = Field(default={}, sa_column=Column(JSON))
    borrower_declined_data: dict = Field(default={}, sa_column=Column(JSON))
    lender_started_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    secop_data_verification: dict = Field(default={}, sa_column=Column(JSON))
    lender_approved_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    lender_approved_data: dict = Field(default={}, sa_column=Column(JSON))
    lender_rejected_data: Optional[dict] = Field(default={}, sa_column=Column(JSON))
    borrewed_uploaded_contracted_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    completed_in_days: Optional[int]
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    expired_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    archived_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Borrower(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: List["Application"] = Relationship(back_populates="borrower")
    borrower_identifier: str = Field(default="")
    legal_name: str = Field(default="")
    email: str = Field(default="")
    address: str = Field(default="")
    legal_identifier: str = Field(default="")
    type: str = Field(default="")
    sector: str = Field(default="")
    size: str = Field(default="")
    status: str = Field(default="")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    declined_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Lender(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: List["Application"] = Relationship(back_populates="lender")
    name: str = Field(default="")
    status: str = Field(default="")
    type: str = Field(default="")
    borrowed_type_preferences: dict = Field(default={}, sa_column=Column(JSON))
    limits_preferences: dict = Field(default={}, sa_column=Column(JSON))
    sla_days: Optional[int]
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    deleted_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Award(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: List["Application"] = Relationship(back_populates="award.id")
    borrowers: List["Borrower"] = Relationship(back_populates="award.id")
    borrower_id: int = Field(foreign_key="borrower.id")
    source_contract_id: str = Field(default="")
    title: str = Field(default="")
    description: str = Field(default="")
    award_date: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    award_amount: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=10, scale=2), nullable=False))
    award_currency: str = Field(default="")
    contractperiod_startdate: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    contractperiod_enddate: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    payment_method: str = Field(default="")
    buyer_name: str = Field(default="")
    source_url: str = Field(default="")
    entity_code: str = Field(default="")
    contract_status: str = Field(default="")
    source_last_updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    previous: bool
    procurement_method: str = Field(default="")
    contracting_process_id: str = Field(default="")
    procurement_category: str = Field(default="")
    source_data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(default="")
    application_id: int = Field(foreign_key="application.id")
    body: Optional[str] = Field(default="")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    sent_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
