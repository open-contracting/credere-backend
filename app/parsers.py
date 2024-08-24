from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.models import BorrowerSize


class BasicUser(BaseModel):
    username: str
    name: str | None = None
    password: str
    temp_password: str


class ResetPassword(BaseModel):
    username: str


class SetupMFA(BaseModel):
    temp_password: str
    session: str
    secret: str


class AwardUpdate(BaseModel):
    source_contract_id: str | None = None
    title: str | None = None
    description: str | None = None
    contracting_process_id: str | None = None
    award_currency: str | None = None
    award_amount: Decimal | None = None
    award_date: datetime | None = None
    payment_method: dict[str, Any] | None = None
    buyer_name: str | None = None
    source_url: str | None = None
    entity_code: str | None = None
    contract_status: str | None = None
    contractperiod_startdate: datetime | None = None
    contractperiod_enddate: datetime | None = None
    procurement_method: str | None = None
    procurement_category: str | None = None


class LenderApprovedData(BaseModel):
    compliant_checks_completed: bool
    compliant_checks_passed: bool
    additional_comments: str | None = None


class LenderReviewContract(BaseModel):
    disbursed_final_amount: Decimal | None = None


class BorrowerUpdate(BaseModel):
    legal_name: str | None = None
    email: str | None = None
    address: str | None = None
    legal_identifier: str | None = None
    type: str | None = None
    sector: str | None = None
    size: BorrowerSize | None = None


class UpdateDataField(BaseModel):
    legal_name: bool | None = None
    email: bool | None = None
    address: bool | None = None
    legal_identifier: bool | None = None
    type: bool | None = None


class LenderRejectedApplication(BaseModel):
    compliance_checks_failed: bool
    poor_credit_history: bool
    risk_of_fraud: bool
    other: bool
    other_reason: str | None = None


class ApplicationBase(BaseModel):
    uuid: str


class ConfirmNewEmail(ApplicationBase):
    confirmation_email_token: str


class ChangeEmail(ApplicationBase):
    new_email: str


class VerifyBorrowerDocument(BaseModel):
    verified: bool


class ApplicationCreditOptions(ApplicationBase):
    borrower_size: BorrowerSize
    amount_requested: Decimal


class ApplicationSelectCreditProduct(ApplicationCreditOptions):
    sector: str
    annual_revenue: Decimal | None = None
    credit_product_id: int
    repayment_years: int | None = None
    repayment_months: int | None = None
    payment_start_date: datetime | None = None


class UploadContractConfirmation(ApplicationBase):
    contract_amount_submitted: Decimal | None = None


class ApplicationEmailBorrower(BaseModel):
    message: str


class ApplicationDeclinePayload(ApplicationBase):
    decline_this: bool
    decline_all: bool


class ApplicationDeclineFeedbackPayload(ApplicationBase):
    dont_need_access_credit: bool
    already_have_acredit: bool
    preffer_to_go_to_bank: bool
    dont_want_access_credit: bool
    suspicious_email: bool
    other: bool
    other_comments: str
