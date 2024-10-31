import sys
from datetime import datetime, timedelta, tzinfo
from decimal import Decimal
from enum import StrEnum
from typing import Any, Self

from sqlalchemy import Boolean, Column, DateTime, and_, desc, or_, select
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Query, Session, joinedload
from sqlalchemy.sql import ColumnElement, Select, func
from sqlalchemy.sql.expression import nulls_last, true
from sqlmodel import Field, Relationship, SQLModel, col

from app.i18n import i
from app.settings import app_settings


def get_missing_data_keys(data: dict[str, Any]) -> dict[str, bool]:
    """
    Get a dictionary indicating whether each key in the input dictionary has missing data (empty or None).

    :param data: The input dictionary to check for missing data.
    :return: A dictionary with the same keys as the input dictionary, where the values are True if the corresponding
             value in the input dictionary is empty or None, and False otherwise.
    """
    return {key: value == "" or value is None for key, value in data.items()}


def get_order_by(sort_field: str, sort_order: str, model: type[SQLModel] | None = None) -> Any:
    if "." in sort_field:
        model_name, field_name = sort_field.split(".", 1)
        # credere-frontend doesn't use any camelcase models, so capitalize() works.
        column = getattr(getattr(sys.modules[__name__], model_name.capitalize()), field_name)
    else:
        column = getattr(model, sort_field)
    return getattr(col(column), sort_order)()


# https://github.com/tiangolo/sqlmodel/issues/254
#
# The session.flush() calls are not strictly necessary. However, they can avoid errors like:
#
# >>> instance.related_id = related.id
# (related_id is set to None)
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

        If the model has a ``missing_data`` field, indicate which fields are missing in ``data``.

        :param session: The database session.
        :param data: The initial instance data.
        :return: The inserted instance.
        """
        obj = cls(**data)
        if hasattr(obj, "missing_data"):  # Award and Borrower
            obj.missing_data = get_missing_data_keys(data)

        session.add(obj)
        session.flush()
        return obj

    @classmethod
    def create_from_object(cls, session: Session, obj: Self) -> Self:
        """
        Insert a new instance into the database.

        If the model has a ``missing_data`` field, indicate which fields are missing in the instance.

        :param session: The database session.
        :param data: The initial instance data.
        :return: The inserted instance.
        """
        # https://github.com/fastapi/sqlmodel/issues/348
        obj = cls.model_validate(obj)  # type: ignore[attr-defined]
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
            # https://github.com/fastapi/sqlmodel/issues/348
            self.missing_data = get_missing_data_keys(self.model_dump())  # type: ignore[attr-defined]

        session.add(self)  # not strictly necessary
        session.flush()
        return self

    @classmethod
    def create_or_update(cls, session: Session, filters: list[bool | ColumnElement[Boolean]], **data: Any) -> Self:
        obj: Self | None = session.query(cls).filter(*filters).first()
        if obj:
            return obj.update(session, **data)
        return cls.create(session, **data)


class BorrowerDocumentType(StrEnum):
    INCORPORATION_DOCUMENT = i("INCORPORATION_DOCUMENT")
    SUPPLIER_REGISTRATION_DOCUMENT = i("SUPPLIER_REGISTRATION_DOCUMENT")
    BANK_NAME = i("BANK_NAME")
    BANK_CERTIFICATION_DOCUMENT = i("BANK_CERTIFICATION_DOCUMENT")
    FINANCIAL_STATEMENT = i("FINANCIAL_STATEMENT")
    SIGNED_CONTRACT = i("SIGNED_CONTRACT")
    SHAREHOLDER_COMPOSITION = i("SHAREHOLDER_COMPOSITION")
    CHAMBER_OF_COMMERCE = i("CHAMBER_OF_COMMERCE")
    THREE_LAST_BANK_STATEMENT = i("THREE_LAST_BANK_STATEMENT")
    INCOME_TAX_RETURN_STATEMENT = i("INCOME_TAX_RETURN_STATEMENT")
    CHAMBER_OF_COMMERCE_WITH_TEMPORARY_UNIONS = i("CHAMBER_OF_COMMERCE_WITH_TEMPORARY_UNIONS")


# https://github.com/open-contracting/credere-backend/issues/39
class ApplicationStatus(StrEnum):
    """
    An application status.

    The different workflows are:

    -  PENDING → LAPSED
    -  PENDING → DECLINED
    -  PENDING → ACCEPTED → LAPSED
    -  PENDING → ACCEPTED → SUBMITTED → STARTED (→ …)

    And then, from STARTED:

    -  → INFORMATION_REQUESTED → LAPSED
    -  → INFORMATION_REQUESTED → STARTED (→ …)
    -  → REJECTED
    -  → APPROVED
    """

    #: Credere sends an invitation to the borrower.
    #:
    #: (:typer:`python-m-app-fetch-awards`)
    PENDING = i("PENDING")
    #: Borrower declines the invitation.
    #:
    #: (``/applications/decline``)
    DECLINED = i("DECLINED")
    #: Borrower accepts the invitation.
    #:
    #: (``/applications/access-scheme``)
    ACCEPTED = i("ACCEPTED")
    #: Borrower submits its application.
    #:
    #: (``/applications/submit``)
    SUBMITTED = i("SUBMITTED")
    #: Lender start reviewing the application.
    #:
    #: (``/applications/{id}/start``)
    STARTED = i("STARTED")
    #: Lender rejects the application, after the borrower either submits its application or updates a document.
    #:
    #: (``/applications/{id}/reject-application``)
    REJECTED = i("REJECTED")
    #: Lender requests the borrower to update a document.
    #:
    #: (``/applications/email-sme/{id}``)
    INFORMATION_REQUESTED = i("INFORMATION_REQUESTED")
    #: Borrower doesn't accept or decline the invitation, or doesn't submit the application or information requested.
    #:
    #: (:typer:`python-m-app-update-applications-to-lapsed`)
    LAPSED = i("LAPSED")
    #: Lender approves the application, and sets the final credit disbursed.
    #:
    #: (``/applications/{id}/approve-application``)
    APPROVED = i("APPROVED")


class BorrowerStatus(StrEnum):
    #: The borrower may receive Credere invitations.
    ACTIVE = "ACTIVE"
    #: The borrower has opted out of Credere entirely.
    DECLINE_OPPORTUNITIES = "DECLINE_OPPORTUNITIES"


class MessageType(StrEnum):
    #: Message the borrower to accept or decline the invitation.
    #:
    #: PENDING (:typer:`python-m-app-fetch-awards`)
    BORROWER_INVITATION = "BORROWER_INVITATION"
    #: Remind the borrower to accept or decline the invitation.
    #:
    #: PENDING (:typer:`python-m-app-send-reminders`)
    BORROWER_PENDING_APPLICATION_REMINDER = "BORROWER_PENDING_APPLICATION_REMINDER"
    #: Remind the borrower to submit the application.
    #:
    #: ACCEPTED (:typer:`python-m-app-send-reminders`)
    BORROWER_PENDING_SUBMIT_REMINDER = "BORROWER_PENDING_SUBMIT_REMINDER"
    #: Remind the borrower to start external onboarding.
    #:
    #: SUBMITTED, STARTED (:typer:`python-m-app-send-reminders`)
    BORROWER_EXTERNAL_ONBOARDING_REMINDER = "BORROWER_EXTERNAL_ONBOARDING_REMINDER"
    #: Confirm receipt of the application.
    #:
    #: ACCEPTED → SUBMITTED (``/applications/submit``)
    SUBMISSION_COMPLETED = "SUBMISSION_COMPLETED"
    #: Notify the administrators about a new application.
    #:
    #: Unused, but the corresponding message is sent by ``/applications/submit`` :issue:`330`
    NEW_APPLICATION_OCP = "NEW_APPLICATION_OCP"
    #: Notify the lender about a new application.
    #:
    #: Unused, but the corresponding message is sent by ``/applications/submit`` :issue:`330`
    NEW_APPLICATION_FI = "NEW_APPLICATION_FI"
    #: Request documents from the borrower.
    #:
    #: STARTED → INFORMATION_REQUESTED (``/applications/email-sme/{id}``)
    FI_MESSAGE = "FI_MESSAGE"
    #: Notify the lender about the requested documents.
    #:
    #: INFORMATION_REQUESTED → STARTED (``/applications/complete-information-request``)
    BORROWER_DOCUMENT_UPDATED = "BORROWER_DOCUMENT_UPDATED"
    #: Notify the borrower that the application is rejected.
    #:
    #: STARTED → REJECTED (``/applications/{id}/reject-application``)
    REJECTED_APPLICATION = "REJECTED_APPLICATION"
    #: Notify the borrower that the application is pre-approved.
    #:
    #: STARTED → APPROVED (``/applications/{id}/approve-application``)
    APPROVED_APPLICATION = "APPROVED_APPLICATION"
    #: Remind the administrators about overdue applications.
    #:
    #: STARTED (:typer:`python-m-app-sla-overdue-applications`)
    OVERDUE_APPLICATION = "OVERDUE_APPLICATION"
    #: Send the borrower a URL to continue the copied application.
    #:
    #: ACCEPTED (``/applications/find-alternative-credit-option``)
    APPLICATION_COPIED = "APPLICATION_COPIED"
    #: Verify the borrower's new email address.
    #:
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
    FI_DOWNLOAD_DOCUMENT = "FI_DOWNLOAD_DOCUMENT"
    FI_DOWNLOAD_APPLICATION = "FI_DOWNLOAD_APPLICATION"
    OCP_DOWNLOAD_APPLICATION = "OCP_DOWNLOAD_APPLICATION"
    FI_START_APPLICATION = "FI_START_APPLICATION"
    FI_REQUEST_INFORMATION = "FI_REQUEST_INFORMATION"
    OCP_DOWNLOAD_DOCUMENT = "OCP_DOWNLOAD_DOCUMENT"
    APPROVED_APPLICATION = "APPROVED_APPLICATION"
    REJECTED_APPLICATION = "REJECTED_APPLICATION"
    MSME_UPLOAD_DOCUMENT = "MSME_UPLOAD_DOCUMENT"
    MSME_CHANGE_EMAIL = "MSME_CHANGE_EMAIL"
    MSME_CONFIRM_EMAIL = "MSME_CONFIRM_EMAIL"
    MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED = "MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED"
    MSME_RETRY_APPLICATION = "MSME_RETRY_APPLICATION"
    MSME_ACCESS_EXTERNAL_ONBOARDING = "MSME_ACCESS_EXTERNAL_ONBOARDING"
    DATA_VALIDATION_UPDATE = "DATA_VALIDATION_UPDATE"
    BORROWER_DOCUMENT_VERIFIED = "BORROWER_DOCUMENT_VERIFIED"
    APPLICATION_COPIED_FROM = "APPLICATION_COPIED_FROM"
    COPIED_APPLICATION = "COPIED_APPLICATION"
    APPLICATION_ROLLBACK_SELECT_PRODUCT = "APPLICATION_ROLLBACK_SELECT_PRODUCT"
    APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT = "APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT"


class BorrowerSize(StrEnum):
    NOT_INFORMED = i("NOT_INFORMED")
    MICRO = i("MICRO")
    SMALL = i("SMALL")
    MEDIUM = i("MEDIUM")
    BIG = i("BIG")


class BorrowerSector(StrEnum):
    AGRICULTURA = i("agricultura")
    MINAS = i("minas")
    MANUFACTURA = i("manufactura")
    ELECTRICIDAD = i("electricidad")
    AGUA = i("agua")
    CONSTRUCCION = i("construccion")
    TRANSPORTE = i("transporte")
    ALOJAMIENTO = i("alojamiento")
    COMUNICACIONES = i("comunicaciones")
    ACTIVIDADES_FINANCIERAS = i("actividades_financieras")
    ACTIVIDADES_INMOBILIARIAS = i("actividades_inmobiliarias")
    ACTIVIDADES_PROFESIONALES = i("actividades_profesionales")
    ACTIVIDADES_SERVICIOS_ADMINISTRATIVOS = i("actividades_servicios_administrativos")
    ADMINISTRACION_PUBLICA = i("administracion_publica")
    EDUCACION = i("educacion")
    ATENCION_SALUD = i("atencion_salud")
    ACTIVIDADES_ARTISTICAS = i("actividades_artisticas")
    OTRAS_ACTIVIDADES = i("otras_actividades")
    ACTIVIDADES_HOGARES = i("actividades_hogares")
    ACTIVIDADES_ORGANIZACIONES_EXTRATERRITORIALES = i("actividades_organizaciones_extraterritoriales")


class CreditType(StrEnum):
    LOAN = i("LOAN")
    CREDIT_LINE = i("CREDIT_LINE")


class BorrowerType(StrEnum):
    NATURAL_PERSON = i("NATURAL_PERSON")
    LEGAL_PERSON = i("LEGAL_PERSON")


class LenderBase(SQLModel):
    #: The name of the lender.
    name: str = Field(default="", unique=True)
    #: An email address of the lender, for sharing with borrowers.
    email_group: str = Field(default="")
    #: The type of the lender, from the ``LENDER_TYPES`` enum in credere-frontend. (Unused.)
    type: str = Field(default="")  # LENDER_TYPES
    #: The filename of the logo of the lender, in credere-frontend.
    logo_filename: str = Field(default="")

    #: The number of days within which the lender agrees to respond to application changes.
    #:
    #: .. seealso:: :attr:`~app.settings.Settings.progress_to_remind_started_applications`
    sla_days: int | None
    #: A URL pointing to the lender's own onboarding system. If set, a custom email is sent to the borrower after
    #: the application is submitted, indicating that the process should continue in the lender's system.
    external_onboarding_url: str = Field(default="")


class Lender(LenderBase, ActiveRecordMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    #: Unused.
    status: str = Field(default="")
    #: Unused.
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
    #: The types of borrower to which this credit product is applicable.
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
    #: The hashed borrower ID, for privacy-preserving long-term identification.
    borrower_identifier: str = Field(default="", unique=True)
    #: The time at which the borrower opted out of Credere entirely.
    #:
    #: .. seealso:: :attr:`app.models.Borrower.status`
    declined_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

    # From data source

    #: The name of the borrower in the data source.
    legal_name: str = Field(default="")
    #: The email address with which the application's :attr:`~app.models.Application.primary_email` is initialized.
    email: str = Field(default="")
    #: The registered address of the borrower in the data source.
    address: str = Field(default="")
    #: The ID of the borrower in the data source.
    legal_identifier: str = Field(default="")
    #: The type of the borrower in the data source.
    type: str = Field(default="")
    #: Whether the borrower is a MSME in the data source.
    is_msme: bool = Field(default=True)
    #: .. seealso:: :attr:`app.models.ActiveRecordMixin.create` and :attr:`~app.models.ActiveRecordMixin.update`.
    missing_data: dict[str, bool] = Field(default_factory=dict, sa_type=JSON)

    # From borrower input

    #: .. seealso:: :attr:`app.models.CreditProduct.borrower_size`
    size: BorrowerSize = Field(default=BorrowerSize.NOT_INFORMED)
    #: The industrial sector of the borrower.
    sector: str = Field(default="")  # SECTOR_TYPES
    #: The annual revenue of the borrower.
    annual_revenue: Decimal | None = Field(max_digits=16, decimal_places=2)
    #: The currency of the annual revenue of the borrower.
    currency: str = Field(default="COP", description="ISO 4217 currency code")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )


class Borrower(BorrowerBase, ActiveRecordMixin, table=True):
    """
    Most fields are derived from the data source. In terms of application logic, those fields are (or can be) used in
    emails to the borrower, like the ``legal_identifier`` and ``legal_name``.
    """

    # From data source
    source_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    #: The status of the borrower.
    status: BorrowerStatus = Field(default=BorrowerStatus.ACTIVE)

    # Relationships
    applications: list["Application"] = Relationship(back_populates="borrower")
    awards: list["Award"] = Relationship(back_populates="borrower")


class AwardBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)

    # From data source

    #: The ID of the award (contract) in the data source.
    source_contract_id: str = Field(default="", index=True)
    title: str = Field(default="")
    description: str = Field(default="")
    award_date: datetime | None
    award_amount: Decimal = Field(max_digits=16, decimal_places=2)
    award_currency: str = Field(default="COP", description="ISO 4217 currency code")
    #: .. seealso:: :meth:`app.models.Application.previous_awards`
    contractperiod_startdate: datetime | None
    contractperiod_enddate: datetime | None
    payment_method: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    buyer_name: str = Field(default="")
    #: The human-readable web page of the award.
    source_url: str = Field(default="")
    entity_code: str = Field(default="")
    contract_status: str = Field(default="")
    #: The time at which the award was last updated in the data source.
    #:
    #: .. seealso:: :meth:`app.models.Award.last_updated`
    source_last_updated_at: datetime | None
    #: Whether this award was retrieved when the invitation was :attr:`accepted<app.models.ApplicationStatus.ACCEPTED>`
    #: (to display to the lender, as context), or is related to an archived application (again, to display in future
    #: applications).
    #:
    #: .. seealso::
    #:
    #:    - :meth:`app.models.Application.previous_awards`
    #:    - :typer:`python-m-app-remove-dated-application-data`
    previous: bool = Field(default=False)
    procurement_method: str = Field(default="")
    contracting_process_id: str = Field(default="")
    #: .. seealso:: :attr:`app.models.CreditProduct.procurement_category_to_exclude`
    procurement_category: str = Field(default="")
    #: .. seealso:: :attr:`app.models.ActiveRecordMixin.create` and :attr:`~app.models.ActiveRecordMixin.update`.
    missing_data: dict[str, bool] = Field(default_factory=dict, sa_type=JSON)

    # Relationships
    borrower_id: int | None = Field(foreign_key="borrower.id")


class Award(AwardBase, ActiveRecordMixin, table=True):
    """
    All fields, other than relationships and timestamps, are derived from the data source. In terms of application
    logic, the fields are (or can be) used in emails to identify the award, like the ``buyer_name`` and ``title``.
    """

    # From data source
    source_data_contracts: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    source_data_awards: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Relationships
    applications: list["Application"] = Relationship(back_populates="award")
    borrower: Borrower | None = Relationship(back_populates="awards")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now())
    )

    @classmethod
    def last_updated(cls, session: Session) -> datetime | None:
        """Return the most recent ``source_last_updated_at`` value."""
        obj: Self | None = session.query(cls).order_by(nulls_last(desc(cls.source_last_updated_at))).first()
        if obj:
            return obj.source_last_updated_at
        return None


class ApplicationBase(SQLModel):
    #: The secure identifier for the application, for passwordless login.
    uuid: str = Field(unique=True)
    #: The email address at which the borrower is contacted.
    primary_email: str = Field(default="")
    #: The hashed borrower ID and award ID, for privacy-preserving long-term identification.
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

    #: The time at which the borrower clicked :attr:`~app.models.Lender.external_onboarding_url`.
    #:
    #: .. seealso:: :attr:`app.models.Lender.external_onboarding_url`
    borrower_accessed_external_onboarding_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)))

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

    #: The amount of the loan disbursed by the lender.
    disbursed_final_amount: Decimal | None = Field(max_digits=16, decimal_places=2)
    #: The total number of days waiting for the lender.
    #:
    #: .. seealso:: :meth:`app.models.Application.days_waiting_for_lender`
    completed_in_days: int | None

    #: The time at which the application was most recently overdue (reset once approved).
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
    award_id: int = Field(foreign_key="award.id", index=True)
    borrower_id: int = Field(foreign_key="borrower.id", index=True)
    lender_id: int | None = Field(foreign_key="lender.id")
    credit_product_id: int | None = Field(foreign_key="credit_product.id", index=True)

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
    lender: Lender = Relationship(back_populates="applications")
    messages: list["Message"] = Relationship(back_populates="application")
    actions: list["ApplicationAction"] = Relationship(back_populates="application")
    # no back_populates, because models.CreditProduct is used as a request and response format. :issue:`376`
    credit_product: CreditProduct = Relationship()

    @classmethod
    def unarchived(cls, session: Session) -> "Query[Self]":
        """Return a query for unarchived applications."""
        return session.query(cls).filter(col(cls.archived_at).is_(None))

    @classmethod
    def pending_introduction_reminder(cls, session: Session) -> "Query[Self]":
        """
        Return a query for PENDING applications whose expiration date is within
        :attr:`~app.settings.Settings.reminder_days_before_expiration` days from now, and whose borrower hasn't already
        received a reminder to accept and may receive Credere invitations.

        .. seealso:: :typer:`python-m-app-send-reminders`
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
        Return a query for ACCEPTED applications whose lapsed date is within
        :attr:`~app.settings.Settings.reminder_days_before_lapsed` days from now, and whose borrower hasn't already
        received a reminder to submit.

        .. seealso:: :typer:`python-m-app-send-reminders`
        """
        lapsed_at = col(cls.borrower_accepted_at) + timedelta(days=app_settings.days_to_change_to_lapsed)

        return session.query(cls).filter(
            cls.status == ApplicationStatus.ACCEPTED,
            datetime.now() < lapsed_at,
            lapsed_at <= datetime.now() + timedelta(days=app_settings.reminder_days_before_lapsed),
            col(cls.id).notin_(Message.application_by_type(MessageType.BORROWER_PENDING_SUBMIT_REMINDER)),
        )

    @classmethod
    def pending_external_onboarding_reminder(cls, session: Session) -> "Query[Self]":
        """
        Return a query for SUBMITTED applications in which the lender uses external onboarding, whose lapsed date is
        within :attr:`~app.settings.Settings.reminder_days_before_lapsed_for_external_onboarding` days from now, and
        whose borrower hasn't already received a reminder to start external onboarding.

        .. seealso:: :typer:`python-m-app-send-reminders`
        """
        lapsed_at = col(cls.borrower_submitted_at) + timedelta(days=app_settings.days_to_change_to_lapsed)
        days = app_settings.reminder_days_before_lapsed_for_external_onboarding

        return cls.pending_external_onboarding(
            session, (ApplicationStatus.SUBMITTED, ApplicationStatus.STARTED)
        ).filter(
            datetime.now() < lapsed_at,
            lapsed_at <= datetime.now() + timedelta(days=days),
            col(cls.id).notin_(Message.application_by_type(MessageType.BORROWER_EXTERNAL_ONBOARDING_REMINDER)),
        )

    @classmethod
    def pending_external_onboarding(cls, session: Session, statuses: tuple[ApplicationStatus, ...]) -> "Query[Self]":
        """
        Return a query for applications with the provided status, in which the lender uses external onboarding, and
        whose borrower hasn't already started external onboarding.
        """
        return (
            session.query(cls)
            .filter(
                col(cls.status).in_(statuses),
                col(Lender.external_onboarding_url) != "",
                col(cls.borrower_accessed_external_onboarding_at).is_(None),
            )
            .join(Lender, cls.lender_id == Lender.id)
        )

    @classmethod
    def lapseable(cls, session: Session) -> "Query[Self]":
        """
        Return a query for :meth:`~app.models.Application.unarchived` applications that have been waiting for the
        borrower to respond for :attr:`~app.settings.Settings.days_to_change_to_lapsed` days.

        .. seealso:: :typer:`python-m-app-update-applications-to-lapsed`
        """
        delta = timedelta(days=app_settings.days_to_change_to_lapsed)

        return (
            cls.unarchived(session)
            .filter(
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
                        cls.status == ApplicationStatus.SUBMITTED,
                        # col(cls.borrower_submitted_at) + delta < datetime.now(),  # noqa: ERA001 # also remove join
                        col(Message.created_at) + delta < datetime.now(),
                        col(Lender.external_onboarding_url) != "",
                        col(cls.borrower_accessed_external_onboarding_at).is_(None),
                    ),
                    and_(
                        cls.status == ApplicationStatus.INFORMATION_REQUESTED,
                        col(cls.information_requested_at) + delta < datetime.now(),
                    ),
                ),
            )
            .join(
                Message,
                and_(
                    cls.id == Message.application_id,
                    Message.type == MessageType.BORROWER_EXTERNAL_ONBOARDING_REMINDER,
                ),
                isouter=True,
            )
            .join(Lender, cls.lender_id == Lender.id, isouter=True)
        )

    @classmethod
    def submitted(cls, session: Session) -> "Query[Self]":
        """
        Return query for :meth:`~app.models.Application.unarchived` applications that have been submitted to any
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
    def submitted_search(
        cls,
        session: Session,
        sort_field: str,
        sort_order: str,
        lender_id: int | None = None,
        search_value: str | None = None,
    ) -> "Query[Self]":
        query = (
            cls.submitted(session)
            .join(Award)
            .join(Borrower, cls.borrower_id == Borrower.id)
            .join(CreditProduct)
            .join(Lender)
            .options(
                joinedload(cls.award),
                joinedload(cls.borrower),
                joinedload(cls.borrower_documents),
                joinedload(cls.credit_product),
                joinedload(cls.lender),
            )
            .order_by(get_order_by(sort_field, sort_order, model=cls))
        )

        if search_value:
            like = f"%{search_value}%"
            query = query.filter(
                or_(
                    cls.primary_email == search_value,
                    col(Borrower.legal_name).ilike(like),
                    col(Borrower.legal_identifier).ilike(like),
                    col(Award.buyer_name).ilike(like),
                )
            )

        if lender_id:
            query = query.filter(
                cls.lender_id == lender_id,
                col(cls.lender_id).isnot(None),
            )

        return query

    @classmethod
    def archivable(cls, session: Session) -> "Query[Self]":
        """
        Return query for :meth:`~app.models.Application.unarchived` applications that have been in a final state
        (DECLINED, REJECTED, APPROVED, LAPSED) for :attr:`~app.settings.Settings.days_to_erase_borrowers_data` days.

        .. seealso:: :typer:`python-m-app-remove-dated-application-data`
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
                    cls.status == ApplicationStatus.APPROVED,
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
        """Return the application's time zone."""
        return self.created_at.tzinfo

    def previous_awards(self, session: Session) -> list["Award"]:
        """Return the previous awards to the application's borrower, in reverse time order by contract start date."""
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
        """Return the IDs of lenders who rejected applications from the application's borrower, for the same award."""
        cls = type(self)
        return [
            lender_id
            for (lender_id,) in session.query(cls.lender_id)
            .distinct()
            .filter(
                cls.award_borrower_identifier == self.award_borrower_identifier,
                cls.status == ApplicationStatus.REJECTED,
                col(cls.lender_id).isnot(None),
            )
            .all()
        ]

    def days_waiting_for_lender(self, session: Session) -> int:
        """Return the number of days that the application has been waiting for the lender to respond."""
        days = 0

        # Sadly, `self.actions.order_by(ApplicationAction.created_at)` raises
        # "'InstrumentedList' object has no attribute 'order_by'".
        base_query = ApplicationAction.filter_by(session, "application_id", self.id).order_by(
            ApplicationAction.created_at
        )

        lender_requests = base_query.filter(
            ApplicationAction.type == ApplicationActionType.FI_REQUEST_INFORMATION
        ).all()

        # Days between the lender starting and making a first request. / Days between the lender starting and now.
        end_time = lender_requests.pop(0).created_at if lender_requests else datetime.now(self.tz)
        days += (end_time - self.lender_started_at).days  # type: ignore[operator]

        # A lender can have only one unresponded request at a time.
        for borrower_response in base_query.filter(
            ApplicationAction.type == ApplicationActionType.MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED
        ):
            # Days between the next request and the next response. / Days between the last request and now.
            end_time = lender_requests.pop(0).created_at if lender_requests else datetime.now(self.tz)
            days += (end_time - borrower_response.created_at).days

            if not lender_requests:
                # There should be at most one unanswered request, but break just in case.
                break

        return round(days)

    def stage_as_rejected(self, lender_rejected_data: dict[str, Any]) -> None:
        """Assign fields related to marking the application as REJECTED."""
        self.status = ApplicationStatus.REJECTED
        self.lender_rejected_at = datetime.now(self.tz)
        self.lender_rejected_data = lender_rejected_data

    def stage_as_approved(self, disbursed_final_amount: Decimal | None, lender_approved_data: dict[str, Any]) -> None:
        """Assign fields related to marking the application as COMPLETED."""
        self.status = ApplicationStatus.APPROVED
        self.lender_approved_at = datetime.now(self.tz)
        self.disbursed_final_amount = disbursed_final_amount
        self.overdued_at = None
        self.lender_approved_data = lender_approved_data


class BorrowerDocumentBase(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    #: The type of document.
    type: BorrowerDocumentType
    #: Whether the document has been verified by the lender.
    verified: bool = Field(default=False)
    #: The filename of the document.
    name: str = Field(default="")
    #: The time at which the document was most recently uploaded by the borrower.
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

    #: The content of the document.
    file: bytes

    # Relationships
    application: Application = Relationship(back_populates="borrower_documents")


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
    application: Application = Relationship(back_populates="messages")
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
        """Return the IDs of applications that sent messages of the provided type."""
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
    #: Unused.
    language: str = Field(default="es", description="ISO 639-1 language code")
    #: The email address with which the user logs in and is contacted.
    email: str = Field(unique=True)
    #: The :class:`~app.models.MessageType` the user wants to receive notifications about. The supported types are:
    #:
    #: - :attr:`~app.models.MessageType.NEW_APPLICATION_FI`
    #: - :attr:`~app.models.MessageType.BORROWER_DOCUMENT_UPDATED`
    #: - :attr:`~app.models.MessageType.OVERDUE_APPLICATION`
    notification_preferences: dict[str, bool] = Field(default_factory=dict, sa_type=JSON)
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

    def is_admin(self) -> bool:
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
    application: Application = Relationship(back_populates="actions")
    user_id: int | None = Field(default=None, foreign_key="credere_user.id")
    user: User | None = Relationship(back_populates="application_actions")

    # Timestamps
    created_at: datetime = Field(
        default=datetime.utcnow(), sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    )


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
