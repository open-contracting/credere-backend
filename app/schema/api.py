from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.schema.core import Application, Award, Borrower


class AwardUpdate(BaseModel):
    source_contract_id: str
    title: str
    description: str
    award_currency: str
    payment_method: dict
    buyer_name: str
    source_url: str
    entity_code: str
    contract_status: str
    previous: bool
    procurement_method: str
    contracting_process_id: str
    procurement_category: str


class ApplicationUpdate(BaseModel):
    uuid: Optional[str]
    contract_amount_submitted: Optional[Decimal]
    amount_requested: Optional[Decimal]
    currency: Optional[str]
    repayment_months: Optional[int]
    pending_documents: Optional[bool]
    completed_in_days: Optional[int]


class ApplicationResponse(BaseModel):
    application: Application
    borrower: Borrower
    award: Award


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
