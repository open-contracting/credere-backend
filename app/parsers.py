from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models import BorrowerSize


class AwardUpdate(BaseModel):
    source_contract_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    contracting_process_id: Optional[str]
    award_currency: Optional[str]
    award_amount: Optional[Decimal]
    award_date: Optional[datetime]
    payment_method: Optional[dict]
    buyer_name: Optional[str]
    source_url: Optional[str]
    entity_code: Optional[str]
    contract_status: Optional[str]
    contractperiod_startdate: Optional[datetime]
    contractperiod_enddate: Optional[datetime]
    procurement_method: Optional[str]
    procurement_category: Optional[str]


class LenderApprovedData(BaseModel):
    compliant_checks_completed: bool
    compliant_checks_passed: bool
    additional_comments: Optional[str]


class LenderReviewContract(BaseModel):
    disbursed_final_amount: Optional[Decimal]


class BorrowerUpdate(BaseModel):
    legal_name: Optional[str]
    email: Optional[str]
    address: Optional[str]
    legal_identifier: Optional[str]
    type: Optional[str]
    sector: Optional[str]
    size: Optional[BorrowerSize]


class UpdateDataField(BaseModel):
    legal_name: Optional[bool]
    email: Optional[bool]
    address: Optional[bool]
    legal_identifier: Optional[bool]
    type: Optional[bool]


class ApplicationUpdate(BaseModel):
    uuid: Optional[str]
    contract_amount_submitted: Optional[Decimal]
    amount_requested: Optional[Decimal]
    currency: Optional[str]
    repayment_months: Optional[int]
    pending_documents: Optional[bool]
    completed_in_days: Optional[int]


class LenderRejectedApplication(BaseModel):
    compliance_checks_failed: bool
    poor_credit_history: bool
    risk_of_fraud: bool
    other: bool
    other_reason: Optional[str]


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
    repayment_years: Optional[int]
    repayment_months: Optional[int]
    payment_start_date: Optional[datetime]


class UploadContractConfirmation(ApplicationBase):
    contract_amount_submitted: Optional[Decimal]


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
