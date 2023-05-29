from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import DECIMAL, Column, DateTime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


class BorrowerDocumentType(Enum):
    INCORPORATION_DOCUMENT = "Incorporation Document"
    SUPPLIER_REGISTRATION_DOCUMENT = "Supplier Registration Document"
    BANK_NAME = "Bank Name"
    BANK_CERTIFICATION_DOCUMENT = "Bank Certification Document"
    FINANCIAL_STATEMENT = "Financial Statement"
    SIGNED_CONTRACT = "Signed Contract"
    COMPLIANCE_REPORT = "Compliance Report"


class ApplicationStatus(Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    LAPSED = "Lapsed"
    DECLINED = "Declined"
    SUBMITTED = "Submitted"
    STARTED = "Started"
    APPROVED = "Approved"
    CONTRACT_UPLOADED = "Contract Uploaded"
    COMPLETED = "Completed"
    REJECTED = "Rejected"
    INFORMATION_REQUESTED = "Information Requested"


class BorrowerStatus(Enum):
    ACTIVE = "Active"
    DECLINE_OPPORTUNITIEs = "Decline Opportunities"


class MessageType(Enum):
    NEW_APPLICATION = "New application"
    FI_MESSAGE = "FI message"
    OVERDUE_APPLICATION = "Overdue application"


class BorrowerDocument(SQLModel, table=True):
    __tablename__ = "borrower_document"
    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id")
    application: Optional["Application"] = Relationship(back_populates="borrower_document")
    type: BorrowerDocumentType = Field(default=BorrowerDocumentType.INCORPORATION_DOCUMENT)
    verified: bool = Field(default=False)
    file: bytes
    name: str = Field(default="")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()))
    submitted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    borrower_documents: Optional[List["BorrowerDocument"]] = Relationship(back_populates="application")
    award_id: int = Field(foreign_key="award.id")
    award: "Award" = Relationship(back_populates="application")
    uuid: str = Field(unique=True, default="", nullable=False)
    primary_email: str = Field(default="")
    status: ApplicationStatus = Field(default=ApplicationStatus.PENDING, nullable=False)
    award_borrowed_identifier: str = Field(default="")
    borrower_id: Optional[int] = Field(foreign_key="borrower.id")
    borrower: "Borrower" = Relationship(back_populates="application")
    lender_id: int = Field(foreign_key="lender.id")
    lender: "Lender" = Relationship(back_populates="application")
    messages: Optional[List["Message"]] = Relationship(back_populates="application")
    contract_amount_submitted: Optional[Decimal] = Field(
        sa_column=Column(DECIMAL(precision=12, scale=2), nullable=False)
    )
    amount_requested: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=12, scale=2), nullable=False))
    currency: str = Field(default="COP")  # ISO 4217 currency code
    repayment_months: Optional[int]
    calculator_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    pending_documents: bool = Field(default=False)
    pending_email_confirmation: bool = Field(default=False)
    borrower_submitted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_accepted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_declined_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_declined_preferences_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    borrower_declined_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    lender_started_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    secop_data_verification: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    lender_approved_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    lender_approved_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    lender_rejected_data: Optional[dict] = Field(default={}, sa_column=Column(JSON), nullable=False)
    borrewed_uploaded_contracted_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    completed_in_days: Optional[int]
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False), onupdate=func.now())
    expired_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    archived_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))


class Borrower(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: Optional[List["Application"]] = Relationship(back_populates="borrower")
    awards: List["Award"] = Relationship(back_populates="borrower")
    borrower_identifier: str = Field(default="")
    legal_name: str = Field(default="")
    email: str = Field(default="")
    address: str = Field(default="")
    legal_identifier: str = Field(default="")
    type: str = Field(default="")
    sector: str = Field(default="")
    size: str = Field(default="")
    status: BorrowerStatus = Field(default=BorrowerStatus.ACTIVE, nullable=False)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()))
    declined_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))


class Lender(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: Optional[List["Application"]] = Relationship(back_populates="lender")
    name: str = Field(default="", nullable=False, unique=True)
    status: str = Field(default="")
    type: str = Field(default="")
    borrowed_type_preferences: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    limits_preferences: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    sla_days: Optional[int]
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()))
    deleted_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class Award(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: Optional[List["Application"]] = Relationship(back_populates="award")
    borrower_id: int = Field(foreign_key="borrower.id")
    borrower: Borrower = Relationship(back_populates="awards")
    source_contract_id: str = Field(default="")
    title: str = Field(default="")
    description: str = Field(default="")
    award_date: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    award_amount: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=10, scale=2), nullable=False))
    award_currency: str = Field(default="")
    contractperiod_startdate: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    contractperiod_enddate: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    payment_method: str = Field(default="")
    buyer_name: str = Field(default="")
    source_url: str = Field(default="")
    entity_code: str = Field(default="")
    contract_status: str = Field(default="")
    source_last_updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    previous: bool = Field(default=False)
    procurement_method: str = Field(default="")
    contracting_process_id: str = Field(default="")
    procurement_category: str = Field(default="")
    source_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()))


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: BorrowerStatus = Field(nullable=False)
    application_id: int = Field(foreign_key="application.id")
    application: Optional["Application"] = Relationship(back_populates="message")
    body: Optional[str] = Field(default="")
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))
    sent_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
