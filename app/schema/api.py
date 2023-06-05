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
    decline_this: bool


#         dontNeedAccessCredit: boolean(),
# alreadyHaveAcredit: boolean(),
# prefferToGoToBank: boolean(),
# dontWantAccessCredit: boolean(),
# other: boolean(),
# otherCommnets: string(),
