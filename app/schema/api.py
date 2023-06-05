from pydantic import BaseModel

from app.schema.core import Application, Award, Borrower


class ApplicationResponse(BaseModel):
    application: Application
    borrower: Borrower
    award: Award


class ApplicationDeclinePayload(BaseModel):
    uuid: str
    decline_this: bool
    decline_all: bool


class ApplicationDeclineFeedbackPayload(BaseModel):
    uuid: str
    dont_need_access_credit: bool
    already_have_acredit: bool
    preffer_to_go_to_bank: bool
    dont_want_access_credit: bool
    other: bool
    other_commnets: str
