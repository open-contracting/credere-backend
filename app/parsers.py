from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models import BorrowerSize


class AwardUpdate(BaseModel):
    source_contract_id: str | None
    title: str | None
    description: str | None
    contracting_process_id: str | None
    award_currency: str | None
    award_amount: Decimal | None
    award_date: datetime | None
    payment_method: dict | None
    buyer_name: str | None
    source_url: str | None
    entity_code: str | None
    contract_status: str | None
    contractperiod_startdate: datetime | None
    contractperiod_enddate: datetime | None
    procurement_method: str | None
    procurement_category: str | None


class LenderApprovedData(BaseModel):
    compliant_checks_completed: bool
    compliant_checks_passed: bool
    additional_comments: str | None


class LenderReviewContract(BaseModel):
    disbursed_final_amount: Decimal | None


class BorrowerUpdate(BaseModel):
    legal_name: str | None
    email: str | None
    address: str | None
    legal_identifier: str | None
    type: str | None
    sector: str | None
    size: BorrowerSize | None


class UpdateDataField(BaseModel):
    legal_name: bool | None
    email: bool | None
    address: bool | None
    legal_identifier: bool | None
    type: bool | None


class ApplicationUpdate(BaseModel):
    uuid: str | None
    contract_amount_submitted: Decimal | None
    amount_requested: Decimal | None
    currency: str | None
    repayment_months: int | None
    pending_documents: bool | None
    completed_in_days: int | None


class LenderRejectedApplication(BaseModel):
    compliance_checks_failed: bool
    poor_credit_history: bool
    risk_of_fraud: bool
    other: bool
    other_reason: str | None


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
    credit_product_id: int
    repayment_years: int | None
    repayment_months: int | None
    payment_start_date: datetime | None


class UploadContractConfirmation(ApplicationBase):
    contract_amount_submitted: Decimal | None


class ApplicationEmailSme(BaseModel):
    message: str


class ApplicationDeclinePayload(ApplicationBase):
    decline_this: bool
    decline_all: bool


class ApplicationDeclineFeedbackPayload(ApplicationBase):
    dont_need_access_credit: bool
    already_have_acredit: bool
    preffer_to_go_to_bank: bool
    dont_want_access_credit: bool
    other: bool
    other_comments: str
