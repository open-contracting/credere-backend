from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from app.schema import core
from app.schema.core import User


class BasePagination(BaseModel):
    count: int
    page: int
    page_size: int


class ApplicationListResponse(BasePagination):
    items: List[core.ApplicationWithRelations]


class LenderListResponse(BasePagination):
    items: List[core.Lender]


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


class BorrowerUpdate(BaseModel):
    legal_name: Optional[str]
    email: Optional[str]
    address: Optional[str]
    legal_identifier: Optional[str]
    type: Optional[str]
    sector: Optional[str]
    size: Optional[core.BorrowerSize]


class ApplicationUpdate(BaseModel):
    uuid: Optional[str]
    contract_amount_submitted: Optional[Decimal]
    amount_requested: Optional[Decimal]
    currency: Optional[str]
    repayment_months: Optional[int]
    pending_documents: Optional[bool]
    completed_in_days: Optional[int]


class ApplicationResponse(BaseModel):
    application: core.Application
    borrower: core.Borrower
    award: core.Award


class ApplicationBase(BaseModel):
    uuid: str


class ConfirmNewEmail(ApplicationBase):
    confirmation_email_token: str
    email: str


class ChangeEmail(ApplicationBase):
    old_email: str
    new_email: str


class ApplicationSubmit(ApplicationBase):
    lender_id: int


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
