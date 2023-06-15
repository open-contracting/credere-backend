from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel
from sqlmodel import SQLModel
from app.schema import core


class ApplicationPagination(BaseModel):
    items: List[core.Application]
    count: int
    page: int
    page_size: int


class LenderPagination(BaseModel):
    items: List[core.Lender]
    count: int
    page: int
    page_size: int


class AwardUpdate(BaseModel):
    source_contract_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    award_currency: Optional[str]
    payment_method: Optional[dict]
    buyer_name: Optional[str]
    source_url: Optional[str]
    entity_code: Optional[str]
    contract_status: Optional[str]
    previous: Optional[bool]
    procurement_method: Optional[str]
    contracting_process_id: Optional[str]
    procurement_category: Optional[str]


class BorrowerUpdate(BaseModel):
    borrower_identifier: Optional[str]
    legal_name: Optional[str]
    email: Optional[str]
    address: Optional[str]
    legal_identifier: Optional[str]
    type: Optional[str]
    sector: Optional[str]
    size: Optional[core.BorrowerSize]
    status: Optional[core.BorrowerStatus]


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


class ApplicationDeclinePayload(ApplicationBase):
    decline_this: bool
    decline_all: bool


class ApplicationDeclineFeedbackPayload(ApplicationBase):
    dont_need_access_credit: bool
    already_have_acredit: bool
    preffer_to_go_to_bank: bool
    dont_want_access_credit: bool
    other: bool
    other_commnets: str
