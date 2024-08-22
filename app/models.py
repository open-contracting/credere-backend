from datetime import datetime, timedelta, tzinfo
from decimal import Decimal
from enum import StrEnum
from typing import Any, Self

from sqlalchemy import Boolean, Column, DateTime, and_, desc, or_, select
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import ColumnElement, Select, func
from sqlalchemy.sql.expression import nulls_last, true
from sqlmodel import Field, Relationship, SQLModel, col

from app.settings import app_settings


def _get_missing_data_keys(data: dict[str, Any]) -> dict[str, bool]:
    """
    Get a dictionary indicating whether each key in the input dictionary has missing data (empty or None).

    :param data: The input dictionary to check for missing data.
    :return: A dictionary with the same keys as the input dictionary, where the values are True if the corresponding
             value in the input dictionary is empty or None, and False otherwise.
    """
    return {key: value == "" or value is None for key, value in data.items()}


# https://github.com/tiangolo/sqlmodel/issues/254
#
# The session.flush() calls are not strictly necessary. However, they can avoid errors like:
#
#     instance.related_id = related.id  # related_id is set to None
class ActiveRecordMixin:
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
    def get(cls, session: Session, id: int) -> Self:
        """
        Get an existing instance by its ID. Raise an exception if not found.

        :param session: The database session.
        :param id: The ID.
        :return: The existing instance if found.
        """
        return cls.filter_by(session, "id", id).one()

    @classmethod
    def create(cls, session: Session, **data: Any) -> Self:
        """
        Insert a new instance into the database.

        :param session: The database session.
        :param data: The initial instance data.
        :return: The inserted instance.
        """
        obj = cls(**data)
        if hasattr(obj, "missing_data"):  # Award and Borrower
            obj.missing_data = _get_missing_data_keys(data)

        session.add(obj)
        session.flush()
        return obj

    @classmethod
    def create_from_object(cls, session: Session, obj: Any) -> Self:
        """
        Insert a new instance into the database.

        :param session: The database session.
        :param data: The initial instance data.
        :return: The inserted instance.
        """
        # https://sqlmodel.tiangolo.com/tutorial/fastapi/multiple-models/
        obj = cls.model_validate(obj)
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
        if hasattr(self, "missing_data"):  # Award and Borrower
            self.missing_data = _get_missing_data_keys(self.model_dump())

        session.add(self)  # not strictly necessary
        session.flush()
        return self

    @classmethod
    def create_or_update(cls, session: Session, filters: list[bool | ColumnElement[Boolean]], **data: Any) -> Self:
        if obj := session.query(cls).filter(*filters).first():
            return obj.update(session, **data)
        return cls.create(session, **data)


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

    -  PENDING → LAPSED
    -  PENDING → DECLINED
    -  PENDING → ACCEPTED → LAPSED
    -  PENDING → ACCEPTED → SUBMITTED → STARTED (→ …)

    And then, from STARTED:

    -  → INFORMATION_REQUESTED → LAPSED
    -  → INFORMATION_REQUESTED → STARTED (→ …)
    -  → REJECTED
    -  → APPROVED → CONTRACT_UPLOADED → COMPLETED
    -  → APPROVED → CONTRACT_UPLOADED → REJECTED
    """

    #: Credere sends an invitation to the borrower.
    #:
    #: (:doc:`fetch-awards</commands>`)
    PENDING = "PENDING"
    #: Borrower declines the invitation.
    #:
    #: (``/applications/decline``)
    DECLINED = "DECLINED"
    #: Borrower accepts the invitation.
    #:
    #: (``/applications/access-scheme``)
    ACCEPTED = "ACCEPTED"
    #: Borrower submits its application.
    #:
    #: (``/applications/submit``)
    SUBMITTED = "SUBMITTED"
    #: Lender start reviewing the application.
    #:
    #: (``/applications/{id}/start``)
    STARTED = "STARTED"
    #: Lender rejects the application, after the borrower either submits its application, updates a document,
    #: or uploads its contract and final contract amount.
    #:
    #: (``/applications/{id}/reject-application``)
    REJECTED = "REJECTED"
    #: Lender requests the borrower to update a document.
    #:
    #: (``/applications/email-sme/{id}``)
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"
    #: Borrower doesn't accept, or doesn't submit the application or information requested.
    #:
    #: (:doc:`update-applications-to-lapsed</commands>`)
    LAPSED = "LAPSED"
    #: Lender pre-approves the application, and Credere asks the borrower to upload its contract.
    #:
    #: (``/applications/{id}/approve-application``)
    APPROVED = "APPROVED"
    #: Borrower uploads its contract and final contract amount.
    #:
    #: (``/applications/confirm-upload-contract``)
    CONTRACT_UPLOADED = "CONTRACT_UPLOADED"
    #: Lender sets the final credit disbursed.
    #:
    #: (``/applications/{id}/complete-application``)
    COMPLETED = "COMPLETED"


class BorrowerStatus(StrEnum):
    #: The borrower may receive Credere invitations.
    ACTIVE = "ACTIVE"
    #: The borrower has opted out of Credere entirely.
    DECLINE_OPPORTUNITIES = "DECLINE_OPPORTUNITIES"


class MessageType(StrEnum):
    #: PENDING (:doc:`fetch-awards</commands>`)
    BORROWER_INVITATION = "BORROWER_INVITATION"
    #: PENDING (:doc:`send-reminders</commands>`)
    BORROWER_PENDING_APPLICATION_REMINDER = "BORROWER_PENDING_APPLICATION_REMINDER"
    #: ACCEPTED (:doc:`send-reminders</commands>`)
    BORROWER_PENDING_SUBMIT_REMINDER = "BORROWER_PENDING_SUBMIT_REMINDER"
    #: ACCEPTED → SUBMITTED (``/applications/submit``)
    SUBMISSION_COMPLETED = "SUBMISSION_COMPLETED"
    #: Unused, but the corresponding message is sent by ``/applications/submit`` :issue:`330`
    NEW_APPLICATION_OCP = "NEW_APPLICATION_OCP"
    #: Unused, but the corresponding message is sent by ``/applications/submit`` :issue:`330`
    NEW_APPLICATION_FI = "NEW_APPLICATION_FI"
    #: STARTED → INFORMATION_REQUESTED (``/applications/email-sme/{id}``)
    FI_MESSAGE = "FI_MESSAGE"
    #: INFORMATION_REQUESTED → STARTED (``/applications/complete-information-request``)
    BORROWER_DOCUMENT_UPDATED = "BORROWER_DOCUMENT_UPDATED"
    #: STARTED → REJECTED (``/applications/{id}/reject-application``)
    REJECTED_APPLICATION = "REJECTED_APPLICATION"
    #: STARTED → APPROVED (``/applications/{id}/approve-application``)
    APPROVED_APPLICATION = "APPROVED_APPLICATION"
    #: Unused
    CONTRACT_UPLOAD_REQUEST = "CONTRACT_UPLOAD_REQUEST"
    #: APPROVED → CONTRACT_UPLOADED (``/applications/confirm-upload-contract``)
    CONTRACT_UPLOAD_CONFIRMATION = "CONTRACT_UPLOAD_CONFIRMATION"
    #: APPROVED → CONTRACT_UPLOADED (``/applications/confirm-upload-contract``)
    CONTRACT_UPLOAD_CONFIRMATION_TO_FI = "CONTRACT_UPLOAD_CONFIRMATION_TO_FI"
    #: CONTRACT_UPLOADED → COMPLETED (``/applications/{id}/complete-application``)
    CREDIT_DISBURSED = "CREDIT_DISBURSED"
    #: STARTED | CONTRACT_UPLOADED (:doc:`sla-overdue-applications</commands>`)
    OVERDUE_APPLICATION = "OVERDUE_APPLICATION"
    #: ACCEPTED (``/applications/find-alternative-credit-option``)
    APPLICATION_COPIED = "APPLICATION_COPIED"
    #: Any (``/applications/change-email``)
    EMAIL_CHANGE_CONFIRMATION = "EMAIL_CHANGE_CONFIRMATION"


class UserType(StrEnum):
    #: Administrators have full access to all endpoints.
    OCP = "OCP"
    #: Lenders have access to applications they received.
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
    APPLICATION_ROLLBACK_SELECT_PRODUCT = "APPLICATION_ROLLBACK_SELECT_PRODUCT"
    APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT = "APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT"


class BorrowerSize(StrEnum):
    NOT_INFORMED = "NOT_INFORMED"
    MICRO = "MICRO"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    BIG = "BIG"


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


class LenderBase(SQLModel):
    name: str = Field(default="", unique=True)
    email_group: str = Field(default="")
    type: str = Field(default="")  # LENDER_TYPES
    logo_filename: str = Field(default="")

    #: The number of days within which the lender agrees to respond to application changes.
    #:
    #: .. seealso:: :attr:`~app.settings.Settings.progress_to_remind_started_applications`
    sla_days: int | None
    #: Additional HTML content to include in a :attr:`app.models.MessageType.APPROVED_APPLICATION` message, if the
    #: "additional_comments" key in the application's :attr:`app.models.APplication.lender_approved_data` isn't set.
    default_pre_approval_message: str = Field(default="")


class Lender(LenderBase, ActiveRecordMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: str = Field(default="")
    deleted_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    # Relationships
    applications: list["Application"] = Relationship(back_populates="lender")
    users: list["User"] = Relationship(back_populates="lender")
    credit_products: list["CreditProduct"] = Relationship(back_populates="lender")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )


class CreditProductBase(SQLModel):
    #: The size of the borrower to which this credit product is applicable.
    #: (The same credit product can be configured for each applicable borrower size.)
    borrower_size: BorrowerSize
    # The types of borrower to which this credit product is applicable.
    borrower_types: dict[str, bool] = Field(default_factory=dict, sa_type=JSON)
    #: The lower limit for the amount requested, below which this credit product is inapplicable.
    lower_limit: Decimal = Field(max_digits=16, decimal_places=2)
    #: The upper limit for the amount requested, above which this credit product is inapplicable.
    upper_limit: Decimal = Field(max_digits=16, decimal_places=2)
    #: A single procurement category, to which this credit product is inapplicable.
    procurement_category_to_exclude: str = Field(default="")
    #: The type of credit product, which mainly controls which descriptive fields are displayed.
    type: CreditType
    #: The document types that the borrower is prompted to upload.
    required_document_types: dict[str, bool] = Field(default_factory=dict, sa_type=JSON)

    # Descriptive
    interest_rate: str = Field(default="")
    additional_information: str = Field(default="")
    other_fees_total_amount: Decimal = Field(max_digits=16, decimal_places=2)
    other_fees_description: str = Field(default="")
    more_info_url: str = Field(default="")

    # Relationships
    lender_id: int = Field(foreign_key="lender.id", index=True)


class CreditProduct(CreditProductBase, ActiveRecordMixin, table=True):
    __tablename__ = "credit_product"

    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    lender: Lender = Relationship(back_populates="credit_products")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )


class BorrowerBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    borrower_identifier: str = Field(default="", unique=True)
    legal_name: str = Field(default="")
    email: str = Field(default="")
    address: str = Field(default="")
    legal_identifier: str = Field(default="")
    type: str = Field(default="")
    sector: str = Field(default="")  # SECTOR_TYPES
    annual_revenue: Decimal | None = Field(max_digits=16, decimal_places=2)
    currency: str = Field(default="COP", description="ISO 4217 currency code")
    # size is self-reported.
    size: BorrowerSize = Field(default=BorrowerSize.NOT_INFORMED)
    # is_msme is from source. This is always set when querying the sources.
    is_msme: bool = Field(default=True)
    missing_data: dict[str, bool] = Field(default_factory=dict, sa_type=JSON)
    declined_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )


class Borrower(BorrowerBase, ActiveRecordMixin, table=True):
    source_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    status: BorrowerStatus = Field(default=BorrowerStatus.ACTIVE)

    # Relationships
    applications: list["Application"] = Relationship(back_populates="borrower")
    awards: list["Award"] = Relationship(back_populates="borrower")


class AwardBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    source_contract_id: str = Field(default="", index=True)
    title: str = Field(default="")
    description: str = Field(default="")
    award_date: datetime | None
    award_amount: Decimal = Field(max_digits=16, decimal_places=2)
    award_currency: str = Field(default="COP", description="ISO 4217 currency code")
    contractperiod_startdate: datetime | None
    contractperiod_enddate: datetime | None
    payment_method: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    buyer_name: str = Field(default="")
    source_url: str = Field(default="")
    entity_code: str = Field(default="")
    contract_status: str = Field(default="")
    source_last_updated_at: datetime | None
    previous: bool = Field(default=False)
    procurement_method: str = Field(default="")
    contracting_process_id: str = Field(default="")
    procurement_category: str = Field(default="")
    missing_data: dict[str, bool] = Field(default_factory=dict, sa_type=JSON)

    # Relationships
    borrower_id: int | None = Field(foreign_key="borrower.id")


class Award(AwardBase, ActiveRecordMixin, table=True):
    source_data_contracts: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    source_data_awards: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Relationships
    applications: list["Application"] = Relationship(back_populates="award")
    borrower: Borrower = Relationship(back_populates="awards")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )

    @classmethod
    def last_updated(cls, session: Session) -> datetime | None:
        """
        :return: The most recent ``source_last_updated_at`` value.
        """
        if obj := session.query(cls).order_by(nulls_last(desc(cls.source_last_updated_at))).first():
            return obj.source_last_updated_at
        return None


class ApplicationBase(SQLModel):
    #: The secure identifier for the application, for passwordless login.
    uuid: str = Field(unique=True)
    #: The email address at which the borrower is contacted.
    primary_email: str = Field(default="")
    #: The hashed award and borrower identifiers, for privacy-preserving long-term identification.
    award_borrower_identifier: str = Field(default="")

    # Request

    amount_requested: Decimal | None = Field(max_digits=16, decimal_places=2)
    currency: str = Field(default="COP", description="ISO 4217 currency code")
    repayment_years: int | None
    repayment_months: int | None
    payment_start_date: datetime | None
    calculator_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Status

    #: The status of the application.
    status: ApplicationStatus = Field(default=ApplicationStatus.PENDING)
    #: Whether the borrower has confirmed the credit product but not yet submitted the application, or
    #: the lender has requested information and the borrower has not yet uploaded documents.
    pending_documents: bool = Field(default=False)
    #: Whether the borrower has changed the primary email for the application, but hasn't confirmed it.
    pending_email_confirmation: bool = Field(default=False)

    # Timeline

    #: The time at which the application expires.
    #:
    #: .. seealso:: :attr:`~app.settings.Settings.application_expiration_days`
    expired_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.DECLINED`.
    borrower_declined_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    #: The reason(s) for which the borrower declined the invitation.
    #:
    #: .. seealso:: :class:`app.parsers.ApplicationDeclineFeedbackPayload`
    borrower_declined_preferences_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    #: Whether the borrower declined only this invitation or all invitations.
    #:
    #: .. seealso:: :class:`app.parsers.ApplicationDeclinePayload`
    borrower_declined_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.ACCEPTED`.
    borrower_accepted_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    #: The time at which the borrower most recently selected a credit product.
    borrower_credit_product_selected_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    #: The time at which the application transitioned from :attr:`~app.models.ApplicationStatus.SUBMITTED`.
    borrower_submitted_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.STARTED`,
    #: from :attr:`~app.models.ApplicationStatus.SUBMITTED`.
    lender_started_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.INFORMATION_REQUESTED`.
    information_requested_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.REJECTED`.
    lender_rejected_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    #: The reason(s) for which the application was rejected.
    #:
    #: .. seealso:: :class:`app.parsers.LenderRejectedApplication`
    lender_rejected_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.APPROVED`.
    lender_approved_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    #: The reason(s) for which the application was approved.
    #:
    #: .. seealso:: :class:`app.parsers.LenderApprovedData`
    lender_approved_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    #: Whether the borrower fields (keys) have been verified (``bool`` values) by the lender.
    secop_data_verification: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.CONTRACT_UPLOADED`.
    borrower_uploaded_contract_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    #: The amount of the contract submitted by the borrower.
    contract_amount_submitted: Decimal | None = Field(max_digits=16, decimal_places=2)

    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.COMPLETED`.
    lender_completed_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    #: The amount of the loan disbursed by the lender.
    disbursed_final_amount: Decimal | None = Field(max_digits=16, decimal_places=2)
    #: The total number of days waiting for the lender.
    #:
    #: .. seealso:: :meth:`app.models.Application.days_waiting_for_lender`
    completed_in_days: int | None

    #: The time at which the application was most recently overdue (reset once completed).
    #:
    #: .. seealso:: :attr:`~app.settings.Settings.progress_to_remind_started_applications`
    overdued_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    #: The time at which the application transitioned to :attr:`~app.models.ApplicationStatus.LAPSED`.
    #:
    #: .. seealso:: :meth:`app.models.Application.lapseable`
    application_lapsed_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))
    #: The time at which the application was archived.
    #:
    #: .. seealso:: :meth:`app.models.Application.archivable`
    archived_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    # Relationships
    award_id: int | None = Field(foreign_key="award.id", index=True)
    borrower_id: int | None = Field(foreign_key="borrower.id", index=True)
    lender_id: int | None = Field(foreign_key="lender.id")
    credit_product_id: int | None = Field(foreign_key="credit_product.id")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )


class ApplicationPrivate(ApplicationBase):
    confirmation_email_token: str = Field(default="", index=True)


class Application(ApplicationPrivate, ActiveRecordMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    borrower_documents: list["BorrowerDocument"] = Relationship(back_populates="application")
    award: Award = Relationship(back_populates="applications")
    borrower: Borrower = Relationship(back_populates="applications")
    lender: Lender | None = Relationship(back_populates="applications")
    messages: list["Message"] = Relationship(back_populates="application")
    actions: list["ApplicationAction"] = Relationship(back_populates="application")
    credit_product: CreditProduct = Relationship()

    @classmethod
    def unarchived(cls, session: Session) -> "Query[Self]":
        """
        :return: A query for unarchived applications.
        """
        return session.query(cls).filter(col(cls.archived_at).is_(None))

    @classmethod
    def pending_introduction_reminder(cls, session: Session) -> "Query[Self]":
        """
        :return: A query for PENDING applications whose expiration date is within
            :attr:`~app.settings.Settings.reminder_days_before_expiration` days from now, and whose
            borrower hasn't already received a reminder to accept and may receive Credere invitations.

        .. seealso:: :doc:`send-reminders</commands>`
        """
        return (
            session.query(cls)
            .filter(
                cls.status == ApplicationStatus.PENDING,
                datetime.now() < col(cls.expired_at),
                col(cls.expired_at) <= datetime.now() + timedelta(days=app_settings.reminder_days_before_expiration),
                col(cls.id).notin_(Message.application_by_type(MessageType.BORROWER_PENDING_APPLICATION_REMINDER)),
                Borrower.status == BorrowerStatus.ACTIVE,
            )
            .join(Borrower, cls.borrower_id == Borrower.id)
        )

    @classmethod
    def pending_submission_reminder(cls, session: Session) -> "Query[Self]":
        """
        :return: A query for ACCEPTED applications whose lapsed date is within
            :attr:`~app.settings.Settings.reminder_days_before_lapsed` days from now, and whose
            borrower hasn't already received a reminder to submit.

        .. seealso:: :doc:`send-reminders</commands>`
        """
        lapsed_at = col(cls.borrower_accepted_at) + timedelta(days=app_settings.days_to_change_to_lapsed)

        return session.query(cls).filter(
            cls.status == ApplicationStatus.ACCEPTED,
            datetime.now() < lapsed_at,
            lapsed_at <= datetime.now() + timedelta(days=app_settings.reminder_days_before_lapsed),
            col(cls.id).notin_(Message.application_by_type(MessageType.BORROWER_PENDING_SUBMIT_REMINDER)),
        )

    @classmethod
    def lapseable(cls, session: Session) -> "Query[Self]":
        """
        :return: A query for :meth:`~app.models.Application.unarchived` applications that have been waiting for the
            borrower to respond (PENDING, ACCEPTED, INFORMATION_REQUESTED) for
            :attr:`~app.settings.Settings.days_to_change_to_lapsed` days.

        .. seealso:: :doc:`update-applications-to-lapsed</commands>`
        """
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
        """
        :return: A query for :meth:`~app.models.Application.unarchived` applications that have been submitted to any
            lender (not one of PENDING, DECLINED, ACCEPTED) and that aren't LAPSED.
        """
        return cls.unarchived(session).filter(
            col(cls.status).notin_(
                [
                    ApplicationStatus.PENDING,
                    ApplicationStatus.DECLINED,
                    ApplicationStatus.ACCEPTED,
                    ApplicationStatus.LAPSED,
                ]
            )
        )

    @classmethod
    def submitted_to_lender(cls, session: Session, lender_id: int | None) -> "Query[Self]":
        """
        :return: A query for applications :meth:`~app.models.Application.submitted` to a specific lender.
        """
        return cls.submitted(session).filter(
            Application.lender_id == lender_id,
            col(Application.lender_id).isnot(None),
        )

    @classmethod
    def archivable(cls, session: Session) -> "Query[Self]":
        """
        :return: A query for :meth:`~app.models.Application.unarchived` applications that have been in a final state
            (DECLINED, REJECTED, COMPLETED, LAPSED) for
            :attr:`~app.settings.Settings.days_to_erase_borrowers_data` days.

        .. seealso:: :doc:`remove-dated-application-data</commands>`
        """
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
        """
        :return: The application's time zone.
        """
        return self.created_at.tzinfo

    def previous_awards(self, session: Session) -> list["Award"]:
        """
        :return: The previous awards to the application's borrower, in reverse time order by contract start date.
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

    def rejected_lenders(self, session: Session) -> list[Self]:
        """
        :return: The IDs of lenders who rejected applications from the application's borrower, for the same award.
        """
        cls = type(self)
        return [
            lender_id
            for (lender_id,) in session.query(Application.lender_id)
            .distinct()
            .filter(
                cls.award_borrower_identifier == self.award_borrower_identifier,
                cls.status == ApplicationStatus.REJECTED,
                col(cls.lender_id).isnot(None),
            )
            .all()
        ]

    def days_waiting_for_lender(self, session: Session) -> int:
        """
        :return: The number of days that the application has been waiting for the lender to respond.
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
        """
        Assign fields related to marking the application as REJECTED.
        """
        self.status = ApplicationStatus.REJECTED
        self.lender_rejected_at = datetime.now(self.tz)
        self.lender_rejected_data = lender_rejected_data

    def stage_as_completed(self, disbursed_final_amount: Decimal | None) -> None:
        """
        Assign fields related to marking the application as COMPLETED.
        """
        self.status = ApplicationStatus.COMPLETED
        self.lender_completed_at = datetime.now(self.tz)
        self.disbursed_final_amount = disbursed_final_amount
        self.overdued_at = None


class BorrowerDocumentBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    type: BorrowerDocumentType
    verified: bool = Field(default=False)
    name: str = Field(default="")
    submitted_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )

    # Relationships
    application_id: int = Field(foreign_key="application.id")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )


class BorrowerDocument(BorrowerDocumentBase, ActiveRecordMixin, table=True):
    __tablename__ = "borrower_document"

    file: bytes

    # Relationships
    application: Application | None = Relationship(back_populates="borrower_documents")


class Message(SQLModel, ActiveRecordMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    #: The type of email message.
    type: MessageType
    #: The SES ``MessageId``.
    external_message_id: str = Field(default="")
    #: The body of the email message, if directly provided by a lender.
    body: str = Field(default="")

    # Relationships
    application_id: int = Field(foreign_key="application.id")
    application: Application | None = Relationship(back_populates="messages")
    lender_id: int | None = Field(default=None, foreign_key="lender.id")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )

    @classmethod
    def application_by_type(cls, message_type: MessageType) -> Select:
        """
        :return: The IDs of applications that sent messages of the provided type.
        """
        return select(cls.application_id).filter(cls.type == message_type)


class EventLog(SQLModel, ActiveRecordMixin, table=True):
    __tablename__ = "event_log"

    id: int | None = Field(default=None, primary_key=True)
    category: str
    message: str
    url: str = Field(default="")
    data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    traceback: str

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )


class UserBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    #: The authorization group of the user.
    type: UserType = Field(default=UserType.FI)
    language: str = Field(default="es", description="ISO 639-1 language code")
    #: The email address with which the user logs in and is contacted.
    email: str = Field(unique=True)
    #: The name by which the user is addressed in emails and identified in application action histories.
    name: str = Field(default="")
    #: The Cognito ``Username``.
    external_id: str = Field(default="", index=True)

    # Relationships
    lender_id: int | None = Field(default=None, foreign_key="lender.id")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )

    def is_ocp(self) -> bool:
        return self.type == UserType.OCP


class User(UserBase, ActiveRecordMixin, table=True):
    __tablename__ = "credere_user"

    # Relationships
    application_actions: list["ApplicationAction"] = Relationship(back_populates="user")
    lender: Lender | None = Relationship(back_populates="users")


class ApplicationAction(SQLModel, ActiveRecordMixin, table=True):
    __tablename__ = "application_action"

    id: int | None = Field(default=None, primary_key=True)
    type: ApplicationActionType
    data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Relationships
    application_id: int = Field(foreign_key="application.id")
    application: Application | None = Relationship(back_populates="actions")
    user_id: int | None = Field(default=None, foreign_key="credere_user.id")
    user: User | None = Relationship(back_populates="application_actions")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )


class Statistic(SQLModel, ActiveRecordMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: StatisticType
    data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    lender_id: int | None = Field(foreign_key="lender.id")


# Classes that inherit from SQLModel but that are used as serializers only.


class UserWithLender(UserBase):
    id: int
    lender: LenderBase | None = None


class LenderRead(LenderBase):
    id: int


class LenderCreate(LenderBase):
    credit_products: list[CreditProduct] | None = None


class LenderWithRelations(LenderRead):
    credit_products: list[CreditProduct] | None = None


class CreditProductWithLender(CreditProductBase):
    id: int
    lender: LenderRead | None = None


class ApplicationRead(ApplicationBase):
    id: int


class ApplicationWithRelations(ApplicationRead):
    borrower: BorrowerBase | None = None
    award: AwardBase | None = None
    lender: LenderBase | None = None
    credit_product: CreditProductBase | None = None
    borrower_documents: list[BorrowerDocumentBase] = Field(default_factory=list)
    modified_data_fields: dict[str, Any] = Field(default_factory=dict)
