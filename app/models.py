from datetime import datetime, timedelta, tzinfo
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional, Self

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DECIMAL, Column, DateTime, and_, desc, or_, select
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import Select, func
from sqlalchemy.sql.expression import true
from sqlmodel import Field, Relationship, SQLModel, col

from app.settings import app_settings


def _get_missing_data_keys(input_dict: dict[str, Any]) -> dict[str, bool]:
    """
    Get a dictionary indicating whether each key in the input dictionary has missing data (empty or None).

    :param input_dict: The input dictionary to check for missing data.
    :return: A dictionary with the same keys as the input dictionary, where the values are True if the corresponding
             value in the input dictionary is empty or None, and False otherwise.
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
    # https://github.com/tiangolo/sqlmodel/issues/348
    __config__ = None

    @classmethod
    def filter_by(cls, session: Session, field: str, value: Any) -> "Query[Self]":
        """
        Filter a model based on a field's value.

        :param session: The database session.
        :param value: The field.
        :param field: The field's value.
        :return: The query.
        """
        return session.query(cls).filter(getattr(cls, field) == value)

    @classmethod
    def first_by(cls, session: Session, field: str, value: Any) -> Self | None:
        """
        Get an existing instance based on a field's value.

        :param session: The database session.
        :param value: The field.
        :param field: The field's value.
        :return: The existing instance if found, otherwise None.
        """
        return cls.filter_by(session, field, value).first()

    @classmethod
    def create(cls, session: Session, **data: Any) -> Self:
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

    def update(self, session: Session, **data: Any) -> Self:
        """
        Update an existing instance in the database.

        :param session: The database session.
        :param data: The updated instance data.
        :return: The updated instance.
        """
        for key, value in data.items():
            setattr(self, key, value)
        if hasattr(self, "missing_data"):
            self.missing_data = _get_missing_data_keys(self.model_dump())

        session.add(self)
        session.flush()
        return self


class BorrowerDocumentType(StrEnum):
    INCORPORATION_DOCUMENT = "INCORPORATION_DOCUMENT"
    SUPPLIER_REGISTRATION_DOCUMENT = "SUPPLIER_REGISTRATION_DOCUMENT"
    BANK_NAME = "BANK_NAME"
    BANK_CERTIFICATION_DOCUMENT = "BANK_CERTIFICATION_DOCUMENT"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    SIGNED_CONTRACT = "SIGNED_CONTRACT"
    SHAREHOLDER_COMPOSITION = "SHAREHOLDER_COMPOSITION"
    CHAMBER_OF_COMMERCE = "CHAMBER_OF_COMMERCE"
    THREE_LAST_BANK_STATEMENT = "THREE_LAST_BANK_STATEMENT"


# https://github.com/open-contracting/credere-backend/issues/39
class ApplicationStatus(StrEnum):
    """
    The different workflows are:

    -  PENDING -> LAPSED
    -  PENDING -> DECLINED
    -  PENDING -> ACCEPTED -> LAPSED
    -  PENDING -> ACCEPTED -> SUBMITTED -> STARTED

    From STARTED:

    -  -> INFORMATION_REQUESTED -> LAPSED
    -  -> INFORMATION_REQUESTED -> STARTED
    -  -> REJECTED
    -  -> APPROVED -> CONTRACT_UPLOADED -> COMPLETED
    -  -> APPROVED -> CONTRACT_UPLOADED -> REJECTED
    """

    # Credere sends an invitation to the borrower.
    PENDING = "PENDING"
    # Borrower declines the invitation.
    DECLINED = "DECLINED"
    # Borrower accepts the invitation.
    ACCEPTED = "ACCEPTED"
    # Borrower submits its application.
    SUBMITTED = "SUBMITTED"
    # Lender start reviewing the application.
    STARTED = "STARTED"
    # Lender rejects the application, after the borrower either submits its application, updates a document, or uploads
    # its contract and final contract amount.
    REJECTED = "REJECTED"
    # Lender requests the borrower to update a document.
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"
    # Borrower doesn't accept, or doesn't submit the application or information requested.
    LAPSED = "LAPSED"
    # Lender pre-approves the application, and Credere asks the borrower to upload its contract.
    APPROVED = "APPROVED"
    # Borrower uploads its contract and final contract amount.
    CONTRACT_UPLOADED = "CONTRACT_UPLOADED"
    # Lender sets the final credit disbursed.
    COMPLETED = "COMPLETED"


class BorrowerStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DECLINE_OPPORTUNITIES = "DECLINE_OPPORTUNITIES"


class MessageType(StrEnum):
    BORROWER_INVITATION = "BORROWER_INVITATION"
    BORROWER_PENDING_APPLICATION_REMINDER = "BORROWER_PENDING_APPLICATION_REMINDER"
    BORROWER_PENDING_SUBMIT_REMINDER = "BORROWER_PENDING_SUBMIT_REMINDER"
    BORROWER_DOCUMENT_UPDATED = "BORROWER_DOCUMENT_UPDATED"
    SUBMISSION_COMPLETED = "SUBMISSION_COMPLETED"
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


class UserType(StrEnum):
    OCP = "OCP"
    FI = "FI"


class ApplicationActionType(StrEnum):
    AWARD_UPDATE = "AWARD_UPDATE"
    BORROWER_UPDATE = "BORROWER_UPDATE"
    APPLICATION_CALCULATOR_DATA_UPDATE = "APPLICATION_CALCULATOR_DATA_UPDATE"
    APPLICATION_CONFIRM_CREDIT_PRODUCT = "APPLICATION_CONFIRM_CREDIT_PRODUCT"
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
    BORROWER_DOCUMENT_VERIFIED = "BORROWER_DOCUMENT_VERIFIED"
    BORROWER_UPLOADED_CONTRACT = "BORROWER_UPLOADED_CONTRACT"
    APPLICATION_COPIED_FROM = "APPLICATION_COPIED_FROM"
    COPIED_APPLICATION = "COPIED_APPLICATION"


class BorrowerSize(StrEnum):
    NOT_INFORMED = "NOT_INFORMED"
    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"


class CreditType(StrEnum):
    LOAN = "LOAN"
    CREDIT_LINE = "CREDIT_LINE"


class BorrowerType(StrEnum):
    NATURAL_PERSON = "NATURAL_PERSON"
    LEGAL_PERSON = "LEGAL_PERSON"


class StatisticType(StrEnum):
    MSME_OPT_IN_STATISTICS = "MSME_OPT_IN_STATISTICS"
    APPLICATION_KPIS = "APPLICATION_KPIS"


class StatisticCustomRange(StrEnum):
    LAST_WEEK = "LAST_WEEK"
    LAST_MONTH = "LAST_MONTH"


class CreditProductBase(SQLModel):
    borrower_size: BorrowerSize = Field(nullable=False)
    lower_limit: Decimal = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False))
    upper_limit: Decimal = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False))
    interest_rate: str = Field(default="", nullable=False)
    additional_information: str = Field(default="", nullable=False)
    type: CreditType = Field(nullable=False)
    borrower_types: dict[str, bool] = Field(default={}, sa_column=Column(JSON, nullable=False))
    required_document_types: dict[str, bool] = Field(default={}, sa_column=Column(JSON))
    other_fees_total_amount: Decimal = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False))
    other_fees_description: str = Field(default="", nullable=False)
    more_info_url: str = Field(default="", nullable=False)
    lender_id: int = Field(foreign_key="lender.id", nullable=False, index=True)


class CreditProduct(CreditProductBase, ActiveRecordMixin, table=True):
    __tablename__ = "credit_product"
    id: int | None = Field(default=None, primary_key=True)
    lender: "Lender" = Relationship(back_populates="credit_products")
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), onupdate=func.now())
    )


class BorrowerDocumentBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id")

    type: BorrowerDocumentType = Field(nullable=True)
    verified: bool = Field(default=False)
    name: str = Field(default="")
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), onupdate=func.now())
    )
    submitted_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )


class BorrowerDocument(BorrowerDocumentBase, ActiveRecordMixin, table=True):
    __tablename__ = "borrower_document"
    application: Optional["Application"] = Relationship(back_populates="borrower_documents")
    file: bytes


class ApplicationBase(SQLModel):
    award_id: int | None = Field(foreign_key="award.id", nullable=True, index=True)
    uuid: str = Field(unique=True, nullable=False)
    primary_email: str = Field(default="", nullable=False)
    status: ApplicationStatus = Field(default=ApplicationStatus.PENDING, nullable=True)
    award_borrower_identifier: str = Field(default="", nullable=False)
    borrower_id: int | None = Field(foreign_key="borrower.id", index=True)
    lender_id: int | None = Field(foreign_key="lender.id", nullable=True)
    contract_amount_submitted: Decimal | None = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True))

    disbursed_final_amount: Decimal | None = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True))
    amount_requested: Decimal | None = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=True))
    currency: str = Field(default="COP", description="ISO 4217 currency code")
    repayment_years: int | None = Field(nullable=True)
    repayment_months: int | None = Field(nullable=True)
    payment_start_date: datetime | None = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    calculator_data: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    borrower_credit_product_selected_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    pending_documents: bool = Field(default=False)
    pending_email_confirmation: bool = Field(default=False)
    borrower_submitted_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_accepted_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_declined_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    overdued_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_declined_preferences_data: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    borrower_declined_data: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    lender_started_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    secop_data_verification: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    lender_approved_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    lender_approved_data: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    lender_rejected_data: dict[str, Any] | None = Field(default={}, sa_column=Column(JSON))
    lender_rejected_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    borrower_uploaded_contract_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    lender_completed_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    completed_in_days: int | None = Field(nullable=True)
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), onupdate=func.now())
    )
    expired_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    archived_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    information_requested_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    application_lapsed_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    credit_product_id: int | None = Field(foreign_key="credit_product.id", nullable=True)


class ApplicationPrivate(ApplicationBase):
    confirmation_email_token: str | None = Field(index=True, nullable=True, default="")


class ApplicationRead(ApplicationBase):
    id: int


class Application(ApplicationPrivate, ActiveRecordMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    borrower_documents: list["BorrowerDocument"] | None = Relationship(back_populates="application")
    award: "Award" = Relationship(back_populates="applications")
    borrower: "Borrower" = Relationship(back_populates="applications")
    lender: Optional["Lender"] = Relationship(back_populates="applications")
    messages: list["Message"] | None = Relationship(back_populates="application")
    actions: list["ApplicationAction"] | None = Relationship(back_populates="application")
    credit_product: "CreditProduct" = Relationship()

    @classmethod
    def unarchived(cls, session: Session) -> "Query[Self]":
        return session.query(cls).filter(col(cls.archived_at).is_(None))

    @classmethod
    def expiring_soon(cls, session: Session) -> "Query[Self]":
        return session.query(cls).filter(
            col(cls.expired_at) > datetime.now(),
            col(cls.expired_at) <= datetime.now() + timedelta(days=app_settings.reminder_days_before_expiration),
        )

    @classmethod
    def pending_introduction_reminder(cls, session: Session) -> "Query[Self]":
        return (
            cls.expiring_soon(session)
            .filter(
                cls.status == ApplicationStatus.PENDING,
                col(cls.id).notin_(Message.application_by_type(MessageType.BORROWER_PENDING_APPLICATION_REMINDER)),
                Borrower.status == BorrowerStatus.ACTIVE,
            )
            .join(Borrower, cls.borrower_id == Borrower.id)
            .join(Award, cls.award_id == Award.id)
        )

    @classmethod
    def pending_submission_reminder(cls, session: Session) -> "Query[Self]":
        return cls.expiring_soon(session).filter(
            cls.status == ApplicationStatus.ACCEPTED,
            col(cls.id).notin_(Message.application_by_type(MessageType.BORROWER_PENDING_SUBMIT_REMINDER)),
        )

    @classmethod
    def lapsed(cls, session: Session) -> "Query[Self]":
        delta = timedelta(days=app_settings.days_to_change_to_lapsed)

        return cls.unarchived(session).filter(
            or_(
                and_(
                    cls.status == ApplicationStatus.PENDING,
                    col(cls.created_at) + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.ACCEPTED,
                    col(cls.borrower_accepted_at) + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.INFORMATION_REQUESTED,
                    col(cls.information_requested_at) + delta < datetime.now(),
                ),
            ),
        )

    @classmethod
    def submitted(cls, session: Session) -> "Query[Self]":
        return cls.unarchived(session).filter(
            col(cls.status).notin_(
                [
                    ApplicationStatus.PENDING,
                    ApplicationStatus.ACCEPTED,
                    ApplicationStatus.DECLINED,
                    ApplicationStatus.LAPSED,
                ]
            )
        )

    @classmethod
    def submitted_to_lender(cls, session: Session, lender_id: int | None) -> "Query[Self]":
        return cls.submitted(session).filter(
            Application.lender_id == lender_id,
            col(Application.lender_id).isnot(None),
        )

    @classmethod
    def archivable(cls, session: Session) -> "Query[Self]":
        delta = timedelta(days=app_settings.days_to_erase_borrowers_data)

        return cls.unarchived(session).filter(
            or_(
                and_(
                    cls.status == ApplicationStatus.DECLINED,
                    col(cls.borrower_declined_at) + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.REJECTED,
                    col(cls.lender_rejected_at) + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.COMPLETED,
                    col(cls.lender_approved_at) + delta < datetime.now(),
                ),
                and_(
                    cls.status == ApplicationStatus.LAPSED,
                    col(cls.application_lapsed_at) + delta < datetime.now(),
                ),
            ),
        )

    @property
    def tz(self) -> tzinfo | None:
        return self.created_at.tzinfo

    def previous_awards(self, session: Session) -> list["Award"]:
        """
        :return: The previous awards for the application's borrower, in reverse time order by contract start date.
        """
        return (
            session.query(Award)
            .filter(
                Award.previous == true(),
                Award.borrower_id == self.borrower_id,
            )
            .order_by(col(Award.contractperiod_startdate).desc())
            .all()
        )

    def rejecter_lenders(self, session: Session) -> list[Self]:
        """
        :return: The IDs of lenders who rejected applications from the application's borrower for the same award.
        """
        return (
            session.query(Application.lender_id)
            .filter(
                self.__class__.award_borrower_identifier == self.award_borrower_identifier,
                self.__class__.status == ApplicationStatus.REJECTED,
                col(self.__class__.lender_id).isnot(None),
            )
            .distinct()
            .all()
        )

    def days_waiting_for_lender(self, session: Session) -> int:
        """
        :return: The number of days while waiting for the lender to perform an action.
        """
        days = 0

        # Sadly, `self.actions.order_by(ApplicationAction.created_at)` raises
        # "'InstrumentedList' object has no attribute 'order_by'".
        base_query = ApplicationAction.filter_by(session, "application_id", self.id).order_by(
            ApplicationAction.created_at
        )

        lender_requests = base_query.filter(
            ApplicationAction.type == ApplicationActionType.FI_REQUEST_INFORMATION
        ).all()

        if lender_requests:
            # Days between the lender starting and making a first request.
            end_time = lender_requests.pop(0).created_at
        else:
            # Days between the lender starting and now.
            end_time = datetime.now(self.tz)
        days += (end_time - self.lender_started_at).days

        # A lender can have only one unresponded request at a time.
        for borrower_response in base_query.filter(
            ApplicationAction.type == ApplicationActionType.MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED
        ):
            if lender_requests:
                # Days between the next request and the next response.
                end_time = lender_requests.pop(0).created_at
            else:
                # Days between the last request and now.
                end_time = datetime.now(self.tz)
            days += (end_time - borrower_response.created_at).days

            if not lender_requests:
                # There should be at most one unanswered request, but break just in case.
                break

        return round(days)

    def stage_as_rejected(self, lender_rejected_data: dict[str, Any]) -> None:
        self.status = ApplicationStatus.REJECTED
        self.lender_rejected_at = datetime.now(self.tz)
        self.lender_rejected_data = lender_rejected_data

    def stage_as_completed(self, disbursed_final_amount: Decimal | None) -> None:
        self.status = ApplicationStatus.COMPLETED
        self.lender_completed_at = datetime.now(self.tz)
        self.disbursed_final_amount = disbursed_final_amount
        self.overdued_at = None


class BorrowerBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    borrower_identifier: str = Field(default="", unique=True, nullable=False)
    legal_name: str = Field(default="")
    email: str = Field(default="")
    address: str = Field(default="")
    legal_identifier: str = Field(default="")
    type: str = Field(default="")
    sector: str = Field(default="")
    size: BorrowerSize = Field(default=BorrowerSize.NOT_INFORMED, nullable=True)
    missing_data: dict[str, bool] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), onupdate=func.now())
    )
    declined_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))


class Borrower(BorrowerBase, ActiveRecordMixin, table=True):
    source_data: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    status: BorrowerStatus = Field(default=BorrowerStatus.ACTIVE, nullable=True)
    applications: list["Application"] | None = Relationship(back_populates="borrower")
    awards: list["Award"] = Relationship(back_populates="borrower")


class LenderBase(SQLModel):
    name: str = Field(default="", nullable=False, unique=True)
    email_group: str = Field(default="")
    type: str = Field(default="")
    sla_days: int | None
    logo_filename: str = Field(default="", nullable=True)


class Lender(LenderBase, ActiveRecordMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    applications: list["Application"] | None = Relationship(back_populates="lender")
    users: list["User"] | None = Relationship(back_populates="lender")
    status: str = Field(default="")
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), onupdate=func.now())
    )
    deleted_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=True))
    credit_products: list["CreditProduct"] | None = Relationship(back_populates="lender")


class LenderCreate(LenderBase):
    credit_products: list["CreditProduct"] | None = None


class AwardBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    borrower_id: int | None = Field(foreign_key="borrower.id", nullable=True)
    source_contract_id: str = Field(default="", index=True)
    title: str = Field(default="")
    description: str = Field(default="")
    award_date: datetime | None = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    award_amount: Decimal | None = Field(sa_column=Column(DECIMAL(precision=16, scale=2), nullable=False))
    award_currency: str = Field(default="COP", description="ISO 4217 currency code")
    contractperiod_startdate: datetime | None = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    contractperiod_enddate: datetime | None = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    payment_method: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    buyer_name: str = Field(default="")
    source_url: str = Field(default="")
    entity_code: str = Field(default="")
    contract_status: str = Field(default="")
    source_last_updated_at: datetime | None = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    previous: bool = Field(default=False)
    procurement_method: str = Field(default="")
    contracting_process_id: str = Field(default="")
    procurement_category: str = Field(default="")
    missing_data: dict[str, bool] = Field(default={}, sa_column=Column(JSON))


class Award(AwardBase, ActiveRecordMixin, table=True):
    applications: list["Application"] | None = Relationship(back_populates="award")
    borrower: Borrower = Relationship(back_populates="awards")
    source_data_contracts: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    source_data_awards: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), onupdate=func.now())
    )

    @classmethod
    def last_updated(cls, session: Session) -> datetime | None:
        """
        Get the date of the last updated award.

        :return: The last updated award date.
        """
        obj = session.query(cls).order_by(desc(cls.source_last_updated_at)).first()
        if obj:
            return obj.source_last_updated_at
        return None


class Message(SQLModel, ActiveRecordMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: MessageType = Field(nullable=True)
    application_id: int = Field(foreign_key="application.id")
    application: Optional["Application"] = Relationship(back_populates="messages")
    external_message_id: str | None = Field(default="")
    body: str | None = Field(default="")
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), onupdate=func.now())
    )
    lender_id: int | None = Field(default=None, foreign_key="lender.id", nullable=True)

    @classmethod
    def application_by_type(cls, message_type: MessageType) -> Select:
        """
        :return: The IDs of applications that sent messages of the provided type.
        """
        return select(cls.application_id).filter(cls.type == message_type)


class UserBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    type: UserType = Field(default=UserType.FI, nullable=True)
    language: str = Field(default="es", description="ISO 639-1 language code")
    email: str = Field(unique=True, nullable=False)
    name: str = Field(default="")
    external_id: str = Field(default="", index=True)
    lender_id: int | None = Field(default=None, foreign_key="lender.id", nullable=True)
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )

    def is_OCP(self) -> bool:
        return self.type == UserType.OCP


class UserWithLender(UserBase):
    id: int
    lender: Optional["LenderBase"] = None


class User(UserBase, ActiveRecordMixin, table=True):
    __tablename__ = "credere_user"
    application_actions: list["ApplicationAction"] = Relationship(back_populates="user")
    lender: Optional["Lender"] = Relationship(back_populates="users")


class ApplicationAction(SQLModel, ActiveRecordMixin, table=True):
    __tablename__ = "application_action"
    id: int | None = Field(default=None, primary_key=True)
    type: ApplicationActionType = Field(nullable=True)
    data: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    application_id: int = Field(foreign_key="application.id")
    application: Optional["Application"] = Relationship(back_populates="actions")
    user_id: int | None = Field(default=None, foreign_key="credere_user.id")
    user: User | None = Relationship(back_populates="application_actions")
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow(), server_default=func.now())
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)


class BasicUser(BaseModel):
    username: str
    name: str | None = None
    password: str | None = None
    temp_password: str | None = None


class SetupMFA(BaseModel):
    temp_password: str
    session: str
    secret: str


class ApplicationWithRelations(ApplicationRead):
    borrower: Optional["BorrowerBase"] = None
    award: Optional["AwardBase"] = None
    lender: Optional["LenderBase"] = None
    credit_product: Optional["CreditProductBase"] = None
    borrower_documents: list[BorrowerDocumentBase] | None = None
    modified_data_fields: dict[str, Any] | None = {}


class LenderRead(LenderBase):
    id: int


class LenderWithRelations(LenderRead):
    credit_products: list["CreditProduct"] | None = None


class CreditProductWithLender(CreditProductBase):
    id: int
    lender: Optional["Lender"] = None


class StatisticData(BaseModel):
    name: str
    value: int

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value}


class Statistic(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: StatisticType = Field(nullable=True)
    data: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()))
    lender_id: int | None = Field(foreign_key="lender.id", nullable=True)
