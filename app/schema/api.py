from pydantic import BaseModel

from app.schema.core import Application, Award, Borrower, User


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
    other_comments: str
