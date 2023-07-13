from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from app.schema import core
from app.schema.core import User


class ERROR_CODES(Enum):
    BORROWER_FIELD_VERIFICATION_MISSING = "BORROWER_FIELD_VERIFICATION_MISSING"
    DOCUMENT_VERIFICATION_MISSING = "DOCUMENT_VERIFICATION_MISSING"


class BasePagination(BaseModel):
    count: int
    page: int
    page_size: int


class PreviousAwards(BasePagination):
    items: List[core.Award]


class ApplicationListResponse(BasePagination):
    items: List[core.ApplicationWithRelations]


class LenderListResponse(BasePagination):
    items: List[core.Lender]


class UserListResponse(BasePagination):
    items: List[core.UserWithLender]


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
    size: Optional[core.BorrowerSize]


class UpdateDataField(BaseModel):
    legal_name: Optional[bool]
    email: Optional[bool]
    address: Optional[bool]
    legal_identifier: Optional[bool]
    type: Optional[bool]
    sector: Optional[bool]
    size: Optional[bool]


class ApplicationUpdate(BaseModel):
    uuid: Optional[str]
    contract_amount_submitted: Optional[Decimal]
    amount_requested: Optional[Decimal]
    currency: Optional[str]
    repayment_months: Optional[int]
    pending_documents: Optional[bool]
    completed_in_days: Optional[int]


class ApplicationResponse(BaseModel):
    application: core.ApplicationRead
    borrower: core.Borrower
    award: core.Award
    lender: Optional[core.Lender] = None
    documents: List[core.BorrowerDocumentBase] = []
    creditProduct: Optional[core.CreditProduct] = None


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
    borrower_size: core.BorrowerSize
    amount_requested: Decimal


class ApplicationSelectCreditProduct(ApplicationCreditOptions):
    sector: str
    credit_product_id: int
    repayment_years: Optional[int]
    repayment_months: Optional[int]
    payment_start_date: Optional[datetime]


class CreditProductListResponse(BaseModel):
    loans: List[core.CreditProductWithLender]
    credit_lines: List[core.CreditProductWithLender]


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


class ResponseBase(BaseModel):
    detail: str


class ChangePasswordResponse(ResponseBase):
    secret_code: str
    session: str
    username: str


class UserResponse(BaseModel):
    user: User


class LoginResponse(UserResponse):
    access_token: str
    refresh_token: str
