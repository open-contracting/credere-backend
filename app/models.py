from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import DECIMAL, Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

from app.settings import app_settings


def _get_missing_data_keys(input_dict):
    """
    Get a dictionary indicating whether each key in the input dictionary has missing data (empty or None).

    :param input_dict: The input dictionary to check for missing data.
    :type input_dict: dict

    :return: A dictionary with the same keys as the input dictionary, where the values are True if the corresponding
             value in the input dictionary is empty or None, and False otherwise.
    :rtype: dict
    """

    result_dict = {}
    for key, value in input_dict.items():
        if value == "" or value is None:
            result_dict[key] = True
        else:
            result_dict[key] = False

    return result_dict


# https://github.com/tiangolo/sqlmodel/issues/254
class ActiveRecordMixin:
    __config__ = None

    @classmethod
    def first_by(cls, session, field: str, value: Any):
        """
        Get an existing instance based on a field's value.

        :param session: The database session.
        :param value: The field.
        :param field: The field's value.

        :return: The existing instance if found, otherwise None.
        """
        return session.query(cls).filter(getattr(cls, field) == value).first()

    @classmethod
    def create(cls, session, **data):
        """
        Insert a new instance into the database.

        :param session: The database session.
        :param data: The initial instance data.

        :return: The inserted instance.
        """
        obj = cls(**data)
        if hasattr(obj, "missing_data"):
            obj.missing_data = _get_missing_data_keys(data)

        session.add(obj)
        session.flush()
        return obj

    def update(self, session, **data):
        """
        Update an existing instance in the database.

        :param session: The database session.
        :param data: The updated instance data.

        :return: The updated instance.
        """
        for key, value in data.items():
            setattr(self, key, value)
        if hasattr(self, "missing_data"):
            self.missing_data = _get_missing_data_keys(self.dict())

        session.add(self)
        session.flush()
        return self


class BorrowerDocumentType(Enum):
    INCORPORATION_DOCUMENT = "INCORPORATION_DOCUMENT"
    SUPPLIER_REGISTRATION_DOCUMENT = "SUPPLIER_REGISTRATION_DOCUMENT"
    BANK_NAME = "BANK_NAME"
    BANK_CERTIFICATION_DOCUMENT = "BANK_CERTIFICATION_DOCUMENT"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    SIGNED_CONTRACT = "SIGNED_CONTRACT"
    COMPLIANCE_REPORT = "COMPLIANCE_REPORT"
    SHAREHOLDER_COMPOSITION = "SHAREHOLDER_COMPOSITION"
    CHAMBER_OF_COMMERCE = "CHAMBER_OF_COMMERCE"
    THREE_LAST_BANK_STATEMENT = "THREE_LAST_BANK_STATEMENT"


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
    APPLICATION_COPIED = "APPLICATION_COPIED"
    CREDIT_DISBURSED = "CREDIT_DISBURSED"


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
    OCP_DOWNLOAD_APPLICATION = "OCP_DOWNLOAD_APPLICATION"
    FI_START_APPLICATION = "FI_START_APPLICATION"
    FI_REQUEST_INFORMATION = "FI_REQUEST_INFORMATION"
    OCP_DOWNLOAD_DOCUMENT = "OCP_DOWNLOAD_DOCUMENT"
    APPROVED_APPLICATION = "APPROVED_APPLICATION"
    REJECTED_APPLICATION = "REJECTED_APPLICATION"
    MSME_UPLOAD_DOCUMENT = "MSME_UPLOAD_DOCUMENT"
    MSME_UPLOAD_CONTRACT = "MSME_UPLOAD_CONTRACT"
    MSME_CHANGE_EMAIL = "MSME_CHANGE_EMAIL"
    MSME_CONFIRM_EMAIL = "MSME_CONFIRM_EMAIL"
    MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED = "MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED"
    MSME_RETRY_APPLICATION = "MSME_RETRY_APPLICATION"
    DATA_VALIDATION_UPDATE = "DATA_VALIDATION_UPDATE"
    BORROWER_DOCUMENT_UPDATE = "BORROWER_DOCUMENT_UPDATE"
    BORROWER_UPLOADED_CONTRACT = "BORROWER_UPLOADED_CONTRACT"
    APPLICATION_COPIED_FROM = "APPLICATION_COPIED_FROM"
    COPIED_APPLICATION = "COPIED_APPLICATION"


class BorrowerSize(Enum):
    NOT_INFORMED = "NOT_INFORMED"
    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"


class CreditType(Enum):
    LOAN = "LOAN"
    CREDIT_LINE = "CREDIT_LINE"


class BorrowerType(Enum):
    NATURAL_PERSON = "NATURAL_PERSON"
    LEGAL_PERSON = "LEGAL_PERSON"


class StatisticType(Enum):
    MSME_OPT_IN_STATISTICS = "MSME_OPT_IN_STATISTICS"
    APPLICATION_KPIS = "APPLICATION_KPIS"


class StatisticCustomRange(Enum):
    LAST_WEEK = "LAST_WEEK"
    LAST_MONTH = "LAST_MONTH"


class CreditProductBase(SQLModel):
    borrower_size: BorrowerSize = Field(sa_column=Column(SAEnum(BorrowerSize, name="borrower_size")), nullable=False)
    lower_limit: Decimal = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False))
    upper_limit: Decimal = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False))
    interest_rate: str = Field(default="", nullable=False)
    additional_information: str = Field(default="", nullable=False)
    type: CreditType = Field(sa_column=Column(SAEnum(CreditType, name="credit_type")), nullable=False)
    borrower_types: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    required_document_types: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    other_fees_total_amount: Decimal = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False))
    other_fees_description: str = Field(default="", nullable=False)
    more_info_url: str = Field(default="", nullable=False)
    lender_id: int = Field(foreign_key="lender.id", nullable=False, index=True)


class CreditProduct(CreditProductBase, ActiveRecordMixin, table=True):
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

    type: BorrowerDocumentType = Field(sa_column=Column(SAEnum(BorrowerDocumentType, name="borrower_document_type")))
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


class BorrowerDocument(BorrowerDocumentBase, ActiveRecordMixin, table=True):
    __tablename__ = "borrower_document"
    application: Optional["Application"] = Relationship(back_populates="borrower_documents")
    file: bytes


class ApplicationBase(SQLModel):
    award_id: Optional[int] = Field(foreign_key="award.id", nullable=True, index=True)
    uuid: str = Field(unique=True, nullable=False)
    primary_email: str = Field(default="", nullable=False)
    status: ApplicationStatus = Field(
        sa_column=Column(SAEnum(ApplicationStatus, name="application_status")),
        default=ApplicationStatus.PENDING,
    )
    award_borrower_identifier: str = Field(default="", nullable=False)
    borrower_id: Optional[int] = Field(foreign_key="borrower.id", index=True)
    lender_id: Optional[int] = Field(foreign_key="lender.id", nullable=True)
    contract_amount_submitted: Optional[Decimal] = Field(
        sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True)
    )

    disbursed_final_amount: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True))
    amount_requested: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True))
    currency: str = Field(default="COP", description="ISO 4217 currency code")
    repayment_years: Optional[int] = Field(nullable=True)
    repayment_months: Optional[int] = Field(nullable=True)
    payment_start_date: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    calculator_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    borrower_credit_product_selected_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    pending_documents: bool = Field(default=False)
    pending_email_confirmation: bool = Field(default=False)
    borrower_submitted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_accepted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_declined_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    overdued_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_declined_preferences_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    borrower_declined_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    lender_started_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    secop_data_verification: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    lender_approved_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    lender_approved_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    lender_rejected_data: Optional[dict] = Field(default={}, sa_column=Column(JSON), nullable=False)
    lender_rejected_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_uploaded_contract_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    lender_completed_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
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
    expired_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    archived_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    information_requested_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    application_lapsed_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    credit_product_id: Optional[int] = Field(foreign_key="credit_product.id", nullable=True)


class ApplicationPrivate(ApplicationBase):
    confirmation_email_token: Optional[str] = Field(index=True, nullable=True, default="")


class ApplicationRead(ApplicationBase):
    id: int


class Application(ApplicationPrivate, ActiveRecordMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    borrower_documents: Optional[List["BorrowerDocument"]] = Relationship(back_populates="application")
    award: "Award" = Relationship(back_populates="applications")
    borrower: "Borrower" = Relationship(back_populates="applications")
    lender: Optional["Lender"] = Relationship(back_populates="applications")
    messages: Optional[List["Message"]] = Relationship(back_populates="application")
    actions: Optional[List["ApplicationAction"]] = Relationship(back_populates="application")
    credit_product: "CreditProduct" = Relationship()

    @classmethod
    def unarchived(cls, session):
        return session.query(cls).filter(cls.archived_at.is_(None))

    @classmethod
    def expiring_soon(cls, session):
        return session.query(cls).filter(
            cls.expired_at > datetime.now(),
            cls.expired_at <= datetime.now() + timedelta(days=app_settings.reminder_days_before_expiration),
        )

    @classmethod
    def pending_introduction_reminder(cls, session):
        return (
            cls.expiring_soon(session)
            .filter(
                cls.status == ApplicationStatus.PENDING,
                cls.id.notin_(Message.application_by_type(MessageType.BORROWER_PENDING_APPLICATION_REMINDER)),
                Borrower.status == BorrowerStatus.ACTIVE,
            )
            .join(Borrower, cls.borrower_id == Borrower.id)
            .join(Award, cls.award_id == Award.id)
        )

    @classmethod
    def pending_submission_reminder(cls, session):
        return cls.expiring_soon(session).filter(
            cls.status == ApplicationStatus.ACCEPTED,
            cls.id.notin_(Message.application_by_type(MessageType.BORROWER_PENDING_SUBMIT_REMINDER)),
        )

    @classmethod
    def lapsed(cls, session):
        delta = timedelta(days=app_settings.days_to_change_to_lapsed)

        return cls.unarchived(session).filter(
            or_(
                and_(
                    cls.status == ApplicationStatus.PENDING,
                    cls.created_at + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.ACCEPTED,
                    cls.borrower_accepted_at + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.INFORMATION_REQUESTED,
                    cls.information_requested_at + delta < datetime.now(),
                ),
            ),
        )

    @classmethod
    def archivable(cls, session):
        delta = timedelta(days=app_settings.days_to_erase_borrower_data)

        return cls.unarchived(session).filter(
            or_(
                and_(
                    cls.status == ApplicationStatus.DECLINED,
                    cls.borrower_declined_at + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.REJECTED,
                    cls.lender_rejected_at + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.COMPLETED,
                    cls.lender_approved_at + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.LAPSED,
                    cls.application_lapsed_at + delta < datetime.now(),
                ),
            ),
        )

    def days_waiting_for_lender(self, session) -> int:
        """
        :return: The number of days while waiting for the lender to perform an action.
        """
        days = 0

        # Sadly, `self.actions.order_by(ApplicationAction.created_at)` raises
        # "'InstrumentedList' object has no attribute 'order_by'".
        base_query = (
            session.query(ApplicationAction)
            .filter(ApplicationAction.application_id == self.id)
            .order_by(ApplicationAction.created_at)
        )
        tz = self.created_at.tzinfo

        lender_requests = base_query.filter(
            ApplicationAction.type == ApplicationActionType.FI_REQUEST_INFORMATION
        ).all()

        if lender_requests:
            # Days between the lender starting and making a first request.
            end_time = lender_requests.pop(0).created_at
        else:
            # Days between the lender starting and now.
            end_time = datetime.now(tz)
        days += (end_time - self.lender_started_at).days

        for borrower_response in base_query.filter(
            ApplicationAction.type == ApplicationActionType.MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED
        ):
            if lender_requests:
                # Days between the next request and the next response.
                end_time = lender_requests.pop(0).created_at
            else:
                # Days between the last request and now.
                end_time = datetime.now(tz)
            days += (end_time - borrower_response.created_at).days

            if not lender_requests:
                # There should be at most one unanswered request, but break just in case.
                break

        return round(days)


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
    declined_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))


class Borrower(BorrowerBase, ActiveRecordMixin, table=True):
    source_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    status: BorrowerStatus = Field(
        sa_column=Column(SAEnum(BorrowerStatus, name="borrower_status")),
        default=BorrowerStatus.ACTIVE,
    )
    applications: Optional[List["Application"]] = Relationship(back_populates="borrower")
    awards: List["Award"] = Relationship(back_populates="borrower")


class LenderBase(SQLModel):
    name: str = Field(default="", nullable=False, unique=True)
    email_group: str = Field(default="")
    type: str = Field(default="")
    sla_days: Optional[int]
    logo_filename: str = Field(default="")


class Lender(LenderBase, ActiveRecordMixin, table=True):
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
    deleted_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    credit_products: Optional[List["CreditProduct"]] = Relationship(back_populates="lender")


class LenderCreate(LenderBase):
    credit_products: Optional[List["CreditProduct"]] = None


class AwardBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    borrower_id: Optional[int] = Field(foreign_key="borrower.id", nullable=True)
    source_contract_id: str = Field(default="", index=True)
    title: str = Field(default="")
    description: str = Field(default="")
    award_date: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    award_amount: Optional[Decimal] = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False))
    award_currency: str = Field(default="COP", description="ISO 4217 currency code")
    contractperiod_startdate: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    contractperiod_enddate: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    payment_method: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
    buyer_name: str = Field(default="")
    source_url: str = Field(default="")
    entity_code: str = Field(default="")
    contract_status: str = Field(default="")
    source_last_updated_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    previous: bool = Field(default=False)
    procurement_method: str = Field(default="")
    contracting_process_id: str = Field(default="")
    procurement_category: str = Field(default="")
    missing_data: dict = Field(default={}, sa_column=Column(JSON), nullable=False)


class Award(AwardBase, ActiveRecordMixin, table=True):
    applications: Optional[List["Application"]] = Relationship(back_populates="award")
    borrower: Borrower = Relationship(back_populates="awards")
    source_data_contracts: dict = Field(default={}, sa_column=Column(JSON), nullable=False)
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

    @classmethod
    def last_updated(cls, session) -> Optional[datetime]:
        """
        Get the date of the last updated award.

        :return: The last updated award date.
        """
        obj = session.query(cls).order_by(desc(cls.source_last_updated_at)).first()
        if obj:
            return obj.source_last_updated_at


class Message(SQLModel, ActiveRecordMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: MessageType = Field(sa_column=Column(SAEnum(MessageType, name="message_type")))
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
    lender_id: Optional[int] = Field(default=None, foreign_key="lender.id", nullable=True)

    @classmethod
    def application_by_type(cls, message_type):
        return select(cls.application_id).filter(cls.type == message_type)


class UserBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: UserType = Field(sa_column=Column(SAEnum(UserType, name="user_type")), default=UserType.FI)
    language: str = Field(default="es", description="ISO 639-1 language code")
    email: str = Field(unique=True, nullable=False)
    name: str = Field(default="")
    external_id: str = Field(default="", index=True)
    lender_id: Optional[int] = Field(default=None, foreign_key="lender.id", nullable=True)
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


class User(UserBase, ActiveRecordMixin, table=True):
    __tablename__ = "credere_user"
    application_actions: List["ApplicationAction"] = Relationship(back_populates="user")
    lender: Optional["Lender"] = Relationship(back_populates="users")


class ApplicationAction(SQLModel, ActiveRecordMixin, table=True):
    __tablename__ = "application_action"
    id: Optional[int] = Field(default=None, primary_key=True)
    type: ApplicationActionType = Field(
        sa_column=Column(SAEnum(ApplicationActionType, name="application_action_type"))
    )
    data: dict = Field(default={}, sa_column=Column(JSON))
    application_id: int = Field(foreign_key="application.id")
    application: Optional["Application"] = Relationship(back_populates="actions")
    user_id: int = Field(default=None, foreign_key="credere_user.id")
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
    modified_data_fields: Optional[Dict[str, Any]] = {}


class LenderRead(LenderBase):
    id: int


class LenderWithRelations(LenderRead):
    credit_products: Optional[List["CreditProduct"]] = None


class CreditProductWithLender(CreditProductBase):
    id: int
    lender: Optional["Lender"] = None


class StatisticData(BaseModel):
    name: str
    value: int

    def to_dict(self):
        return {"name": self.name, "value": self.value}


class Statistic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: StatisticType = Field(sa_column=Column(SAEnum(StatisticType, name="statistic_type")))
    data: dict = Field(default={}, sa_column=Column(JSON))
    created_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=func.now(),
        )
    )
    lender_id: Optional[int] = Field(foreign_key="lender.id", nullable=True)
