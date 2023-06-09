from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import DECIMAL, Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


class BorrowerDocumentType(Enum):
    INCORPORATION_DOCUMENT = "INCORPORATION_DOCUMENT"
    SUPPLIER_REGISTRATION_DOCUMENT = "SUPPLIER_REGISTRATION_DOCUMENT"
    BANK_NAME = "BANK_NAME"
    BANK_CERTIFICATION_DOCUMENT = "BANK_CERTIFICATION_DOCUMENT"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    SIGNED_CONTRACT = "SIGNED_CONTRACT"
    COMPLIANCE_REPORT = "COMPLIANCE_REPORT"


class ApplicationStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    LAPSED = "LAPSED"
    DECLINED = "DECLINED"
    SUBMITTED = "SUBMITTED"
    STARTED = "STARTED"
    APPROVED = "APPROVED"
    CONTRACT_UPLOADED = "CONTRACT_UPLOADED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"


class BorrowerStatus(Enum):
    ACTIVE = "ACTIVE"
    DECLINE_OPPORTUNITIES = "DECLINE_OPPORTUNITIES"


class MessageType(Enum):
    BORROWER_INVITACION = "BORROWER_INVITACION"
    BORROWER_PENDING_APPLICATION_REMINDER = "BORROWER_PENDING_APPLICATION_REMINDER"
    BORROWER_PENDING_SUBMIT_REMINDER = "BORROWER_PENDING_SUBMIT_REMINDER"
    SUBMITION_COMPLETE = "SUBMITION_COMPLETE"
    CONTRACT_UPLOAD_REQUEST = "CONTRACT_UPLOAD_REQUEST"
    CONTRACT_UPLOAD_CONFIRMATION = "CONTRACT_UPLOAD_CONFIRMATION"
    CONTRACT_UPLOAD_CONFIRMATION_TO_FI = "CONTRACT_UPLOAD_CONFIRMATION_TO_FI"
    NEW_APPLICATION_OCP = "NEW_APPLICATION_OCP"
    NEW_APPLICATION_FI = "NEW_APPLICATION_FI"
    FI_MESSAGE = "FI_MESSAGE"
    APPROVED_APPLICATION = "APPROVED_APPLICATION"
    REJECTED_APPLICATION = "REJECTED_APPLICATION"
    OVERDUE_APPLICATION = "OVERDUE_APPLICATION"
    EMAIL_CHANGE_CONFIRMATION = "EMAIL_CHANGE_CONFIRMATION"


class UserType(Enum):
    OCP = "OCP"
    FI = "FI"


class ApplicationActionType(Enum):
    AWARD_UPDATE = "AWARD_UPDATE"
    BORROWER_UPDATE = "BORROWER_UPDATE"
    APPLICATION_CALCULATOR_DATA_UPDATE = "APPLICATION_CALCULATOR_DATA_UPDATE"
    APPLICATION_CONFIRM_CREDIT_PRODUCT = "APPLICATION_CONFIRM_CREDIT_PRODUCT"
    FI_UPLOAD_COMPLIANCE = "FI_UPLOAD_COMPLIANCE"
    FI_COMPLETE_APPLICATION = "FI_COMPLETE_APPLICATION"
    FI_DOWNLOAD_DOCUMENT = "FI_DOWNLOAD_DOCUMENT"
    FI_DOWNLOAD_APPLICATION = "FI_DOWNLOAD_APPLICATION"
    FI_START_APPLICATION = "FI_START_APPLICATION"
    FI_REQUEST_INFORMATION = "FI_REQUEST_INFORMATION"
    OCP_DOWNLOAD_DOCUMENT = "OCP_DOWNLOAD_DOCUMENT"
    APPROVED_APPLICATION = "APPROVED_APPLICATION"
    REJECTED_APPLICATION = "REJECTED_APPLICATION"
    MSME_UPLOAD_DOCUMENT = "MSME_UPLOAD_DOCUMENT"
    MSME_UPLOAD_CONTRACT = "MSME_UPLOAD_CONTRACT"
    MSME_CHANGE_EMAIL = "MSME_CHANGE_EMAIL"
    MSME_CONFIRM_EMAIL = "MSME_CONFIRM_EMAIL"
    MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED = (
        "MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED"
    )
    MSME_RETRY_APPLICATION = "MSME_RETRY_APPLICATION"
    DATA_VALIDATION_UPDATE = "DATA_VALIDATION_UPDATE"
    BORROWER_DOCUMENT_UPDATE = "BORROWER_DOCUMENT_UPDATE"
    BORROWER_UPLOADED_CONTRACT = "BORROWER_UPLOADED_CONTRACT"


class BorrowerSize(Enum):
    NOT_INFORMED = "NOT_INFORMED"
    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"


class CreditType(Enum):
    LOAN = "LOAN"
    CREDIT_LINE = "CREDIT_LINE"


class CreditProductBase(SQLModel):
    borrower_size: BorrowerSize = Field(
        sa_column=Column(SAEnum(BorrowerSize, name="borrower_size")), nullable=False
    )
    lower_limit: Decimal = Field(
        sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False)
    )
    upper_limit: Decimal = Field(
        sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False)
    )
    interest_rate: Decimal = Field(
        sa_column=Column(DECIMAL(precision=5, scale=2), nullable=False)
    )
    type: CreditType = Field(
        sa_column=Column(SAEnum(CreditType, name="credit_type")), nullable=False
    )
    required_document_types: dict = Field(
        default={}, sa_column=Column(JSON), nullable=False
    )
    other_fees_total_amount: Decimal = Field(
        sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False)
    )
    other_fees_description: str = Field(default="", nullable=False)
    more_info_url: str = Field(default="", nullable=False)
    lender_id: int = Field(foreign_key="lender.id", nullable=False)


class CreditProduct(CreditProductBase, table=True):
    __tablename__ = "credit_product"
    id: Optional[int] = Field(default=None, primary_key=True)
    lender: "Lender" = Relationship(back_populates="credit_products")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            onupdate=func.now(),
        )
    )


class BorrowerDocumentBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id")

    type: BorrowerDocumentType = Field(
        sa_column=Column(SAEnum(BorrowerDocumentType, name="borrower_document_type"))
    )
    verified: bool = Field(default=False)
    name: str = Field(default="")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            onupdate=func.now(),
            server_default=func.now(),
        )
    )
    submitted_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )


class BorrowerDocument(BorrowerDocumentBase, table=True):
    __tablename__ = "borrower_document"
    application: Optional["Application"] = Relationship(
        back_populates="borrower_documents"
    )
    file: bytes


class ApplicationBase(SQLModel):
    award_id: Optional[int] = Field(foreign_key="award.id", nullable=True)
    uuid: str = Field(unique=True, index=True, nullable=False)
    primary_email: str = Field(default="", nullable=False)
    status: ApplicationStatus = Field(
        sa_column=Column(SAEnum(ApplicationStatus, name="application_status")),
        default=ApplicationStatus.PENDING,
    )
    award_borrower_identifier: str = Field(default="", unique=True, nullable=False)
    borrower_id: Optional[int] = Field(foreign_key="borrower.id")
    lender_id: Optional[int] = Field(foreign_key="lender.id", nullable=True)
    contract_amount_submitted: Optional[Decimal] = Field(
        sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True)
    )
    disbursed_final_amount: Optional[Decimal] = Field(
        sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True)
    )
    amount_requested: Optional[Decimal] = Field(
        sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True)
    )
    currency: str = Field(default="COP", description="ISO 4217 currency code")
    repayment_years: Optional[int] = Field(nullable=True)
    repayment_months: Optional[int] = Field(nullable=True)
    payment_start_date: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    calculator_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    borrower_credit_product_selected_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    pending_documents: bool = Field(default=False)
    pending_email_confirmation: bool = Field(default=False)
    borrower_submitted_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    borrower_accepted_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    borrower_declined_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    borrower_declined_preferences_data: dict = Field(
        default={}, sa_column=Column(JSON), nullable=False
    )
    borrower_declined_data: dict = Field(
        default={}, sa_column=Column(JSON), nullable=False
    )
    lender_started_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    secop_data_verification: dict = Field(
        default={}, sa_column=Column(JSON), nullable=False
    )
    lender_approved_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    lender_approved_data: dict = Field(
        default={}, sa_column=Column(JSON), nullable=False
    )
    lender_rejected_data: Optional[dict] = Field(
        default={}, sa_column=Column(JSON), nullable=False
    )
    lender_rejected_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    borrower_uploaded_contract_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    lender_completed_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    completed_in_days: Optional[int] = Field(nullable=True)
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            onupdate=func.now(),
        )
    )
    expired_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    archived_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    information_requested_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    application_lapsed_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    credit_product_id: Optional[int] = Field(
        foreign_key="credit_product.id", nullable=True
    )


class ApplicationPrivate(ApplicationBase):
    confirmation_email_token: Optional[str] = Field(
        index=True, nullable=True, default=""
    )


class ApplicationRead(ApplicationBase):
    id: int


class Application(ApplicationPrivate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    borrower_documents: Optional[List["BorrowerDocument"]] = Relationship(
        back_populates="application"
    )
    award: "Award" = Relationship(back_populates="applications")
    borrower: "Borrower" = Relationship(back_populates="applications")
    lender: Optional["Lender"] = Relationship(back_populates="applications")
    messages: Optional[List["Message"]] = Relationship(back_populates="application")
    actions: Optional[List["ApplicationAction"]] = Relationship(
        back_populates="application"
    )
    credit_product: "CreditProduct" = Relationship()


class BorrowerBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    borrower_identifier: str = Field(default="", unique=True, nullable=False)
    legal_name: str = Field(default="")
    email: str = Field(default="")
    address: str = Field(default="")
    legal_identifier: str = Field(default="")
    type: str = Field(default="")
    sector: str = Field(default="")
    size: BorrowerSize = Field(
        sa_column=Column(
            SAEnum(BorrowerSize, name="borrower_size"),
        ),
        default=BorrowerSize.NOT_INFORMED,
    )
    missing_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            onupdate=func.now(),
        )
    )
    declined_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class Borrower(BorrowerBase, table=True):
    source_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    status: BorrowerStatus = Field(
        sa_column=Column(SAEnum(BorrowerStatus, name="borrower_status")),
        default=BorrowerStatus.ACTIVE,
    )
    applications: Optional[List["Application"]] = Relationship(
        back_populates="borrower"
    )
    awards: List["Award"] = Relationship(back_populates="borrower")


class LenderBase(SQLModel):
    name: str = Field(default="", nullable=False, unique=True)
    email_group: str = Field(default="")
    type: str = Field(default="")
    sla_days: Optional[int]


class Lender(LenderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    applications: Optional[List["Application"]] = Relationship(back_populates="lender")
    users: Optional[List["User"]] = Relationship(back_populates="lender")
    status: str = Field(default="")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            onupdate=func.now(),
        )
    )
    deleted_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    credit_products: Optional[List["CreditProduct"]] = Relationship(
        back_populates="lender"
    )


class LenderCreate(LenderBase):
    credit_products: Optional[List["CreditProduct"]] = None


class AwardBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    borrower_id: Optional[int] = Field(foreign_key="borrower.id", nullable=True)
    source_contract_id: str = Field(default="")
    title: str = Field(default="")
    description: str = Field(default="")
    award_date: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    award_amount: Optional[Decimal] = Field(
        sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False)
    )
    award_currency: str = Field(default="COP", description="ISO 4217 currency code")
    contractperiod_startdate: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    contractperiod_enddate: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    payment_method: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    buyer_name: str = Field(default="")
    source_url: str = Field(default="")
    entity_code: str = Field(default="")
    contract_status: str = Field(default="")
    source_last_updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    previous: bool = Field(default=False)
    procurement_method: str = Field(default="")
    contracting_process_id: str = Field(default="")
    procurement_category: str = Field(default="")
    missing_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)


class Award(AwardBase, table=True):
    applications: Optional[List["Application"]] = Relationship(back_populates="award")
    borrower: Borrower = Relationship(back_populates="awards")
    source_data_contracts: dict = Field(
        default={}, sa_column=Column(JSON), nullable=False
    )
    source_data_awards: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            onupdate=func.now(),
        )
    )


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: MessageType = Field(
        sa_column=Column(SAEnum(MessageType, name="message_type"))
    )
    application_id: int = Field(foreign_key="application.id")
    application: Optional["Application"] = Relationship(back_populates="messages")
    external_message_id: Optional[str] = Field(default="")
    body: Optional[str] = Field(default="")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            onupdate=func.now(),
        )
    )
    lender_id: Optional[int] = Field(
        default=None, foreign_key="lender.id", nullable=True
    )


class UserBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: UserType = Field(
        sa_column=Column(SAEnum(UserType, name="user_type")), default=UserType.FI
    )
    language: str = Field(default="es", description="ISO 639-1 language code")
    email: str = Field(unique=True, nullable=False)
    name: str = Field(default="")
    external_id: str = Field(default="")
    lender_id: Optional[int] = Field(
        default=None, foreign_key="lender.id", nullable=True
    )
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )

    def is_OCP(self) -> bool:
        return self.type == UserType.OCP


class UserWithLender(UserBase):
    id: int
    lender: Optional["LenderBase"] = None


class User(UserBase, table=True):
    application_actions: List["ApplicationAction"] = Relationship(back_populates="user")
    lender: Optional["Lender"] = Relationship(back_populates="users")


class ApplicationAction(SQLModel, table=True):
    __tablename__ = "application_action"
    id: Optional[int] = Field(default=None, primary_key=True)
    type: ApplicationActionType = Field(
        sa_column=Column(SAEnum(ApplicationActionType, name="application_action_type"))
    )
    data: dict = Field(default={}, sa_column=Column(JSON))
    application_id: int = Field(foreign_key="application.id")
    application: Optional["Application"] = Relationship(back_populates="actions")
    user_id: int = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="application_actions")
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow(),
            server_default=func.now(),
        )
    )

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


class ApplicationWithRelations(ApplicationRead):
    borrower: Optional["BorrowerBase"] = None
    award: Optional["AwardBase"] = None
    lender: Optional["LenderBase"] = None
    credit_product: Optional["CreditProductBase"] = None
    borrower_documents: Optional[List[BorrowerDocumentBase]] = None


class LenderRead(LenderBase):
    id: int


class LenderWithRelations(LenderRead):
    credit_products: Optional[List["CreditProduct"]] = None


class CreditProductWithLender(CreditProductBase):
    id: int
    lender: Optional["Lender"] = None
