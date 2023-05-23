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
    type: str
    verified: bool
    file: bytes
    name: str
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    submitted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    borrower_documents: List["BorrowerDocument"] = Relationship(back_populates="application")
    award_id: int = Field(foreign_key="award.id")
    uuid: str
    primary_email: str
    status: str
    stage: str
    award_borrowed_identifier: str
    borrower_id: Optional[int] = Field(foreign_key="borrower.id")
    lender_id: Optional[int] = Field(foreign_key="lender.id")
    contract_amount_submitted: Optional[Decimal] = Field(
        sa_column=Column(DECIMAL(precision=12, scale=2), nullable=False)
    )
    amount_requested: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=12, scale=2), nullable=False))
    currency: str
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
    expired_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    archived_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Borrower(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: List["Application"] = Relationship(back_populates="borrower")
    borrower_identifier: str
    legal_name: str
    email: str
    address: str
    legal_identifier: str
    type: str
    sector: str
    size: str
    status: str
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    declined_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Lender(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: List["Application"] = Relationship(back_populates="lender")
    name: str
    status: str
    type: str
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
    source_contract_id: str
    title: str
    description: str
    award_date: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    award_amount: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=10, scale=2), nullable=False))
    award_currency: str
    contractperiod_startdate: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    contractperiod_enddate: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    payment_method: str
    buyer_name: str
    source_url: str
    entity_code: str
    contract_status: str
    source_last_updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    previous: bool
    procurement_method: str
    contracting_process_id: str
    procurement_category: str
    source_data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str
    application_id: int = Field(foreign_key="application.id")
    body: Optional[str] = Field(default=None)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    sent_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
